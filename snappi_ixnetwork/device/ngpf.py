import json, re

from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.device.bgp import Bgp
from snappi_ixnetwork.device.macsec import Macsec
from snappi_ixnetwork.logger import get_ixnet_logger
from snappi_ixnetwork.device.vxlan import VXLAN
from snappi_ixnetwork.device.interface import Ethernet
from snappi_ixnetwork.device.loopbackint import LoopbackInt
from snappi_ixnetwork.device.compactor import Compactor
from snappi_ixnetwork.device.createixnconfig import CreateIxnConfig
from snappi_ixnetwork.device.rocev2 import RoCEv2
from snappi_ixnetwork.device.isis import Isis


class Ngpf(Base):
    _DEVICE_ENCAP_MAP = {
        "Device": "",
        "DeviceEthernet": "ethernetVlan",
        "DeviceIpv4": "ipv4",
        "DeviceIpv6": "ipv6",
        "BgpV4Peer": "ipv4",
        "BgpV6Peer": "ipv6",
        "BgpV4RouteRange": "ipv4",
        "BgpV6RouteRange": "ipv6",
        "DeviceIpv4Loopback": "ipv4",
        "DeviceIpv6Loopback": "ipv6",
        "VxlanV4Tunnel": "ipv4",
        "VxlanV6Tunnel": "ipv6",
        "BgpCMacIpRange": "ethernetVlan",
        "Mka": "ethernetVlan",
        "SecureEntity": "ethernetVlan",
        "Rocev2V4Peer": "ipv4",
        "Rocev2V6Peer": "ipv6",
        "Isis": "ethernetVlan",
        "IsisInterface": "ethernetVlan",
        "IsisV4RouteRange": "ipv4",
        "IsisV6RouteRange": "ipv6",
    }

    _ROUTE_STATE = {"advertise": True, "withdraw": False}

    def __init__(self, ixnetworkapi):
        super(Ngpf, self).__init__()
        self.api = ixnetworkapi
        self._ixn_config = {}
        self.working_dg = None
        self._ixn_topo_objects = {}
        self.ether_v4gateway_map = {}
        self.ether_v6gateway_map = {}
        self.logger = get_ixnet_logger(__name__)
        self._ethernet = Ethernet(self)
        self._bgp = Bgp(self)
        self._macsec = Macsec(self)
        self._vxlan = VXLAN(self)
        self._rocev2 = RoCEv2(self)
        self._isis = Isis(self)
        self._loop_back = LoopbackInt(self)
        self.compactor = Compactor(self.api)
        self._createixnconfig = CreateIxnConfig(self)
        self.is_ip_allowed = True

    def config(self):
        self._ixn_topo_objects = {}
        self.working_dg = None
        self._ixn_config = dict()
        self.ether_v4gateway_map = {}
        self.ether_v6gateway_map = {}
        self._chain_parent_dgs = []
        self.loopback_parent_dgs = []
        self._ixn_config["xpath"] = "/"
        self._resource_manager = self.api._ixnetwork.ResourceManager
        with Timer(self.api, "Convert device config :"):
            self._configure_topology()
        with Timer(self.api, "Create IxNetwork device config :"):
            self._createixnconfig.create(
                self._ixn_config["topology"], "topology"
            )
            self._createixnconfig.post_calculate()
        with Timer(self.api, "Push IxNetwork device config :"):
            self._pushixnconfig()

    def set_device_info(self, snappi_obj, ixn_obj):
        name = snappi_obj.get("name")
        class_name = snappi_obj.__class__.__name__
        self.logger.debug(
            "set_device_info name %s and class_name %s" % (name, class_name)
        )
        try:
            encap = Ngpf._DEVICE_ENCAP_MAP[class_name]
        except KeyError:
            raise NameError("Mapping is missing for {0}".format(class_name))
        self.api.set_device_encap(name, encap)
        self.api.set_device_encap(self.get_name(self.working_dg), encap)
        self.api.ixn_objects.set(name, ixn_obj)

    def set_ixn_routes(self, snappi_obj, ixn_obj):
        name = snappi_obj.get("name")
        self.logger.debug("set_ixn_routes for %s " % name)
        self.api.ixn_routes.set(name, ixn_obj)

    def _get_topology_name(self, port_name):
        return "Topology %s" % port_name

    def _set_dev_compacted(self, dgs):
        if dgs is None:
            return
        for dg in dgs:
            names = dg.get("name")
            if isinstance(names, list) and len(names) > 1:
                self.api.set_dev_compacted(names[0], names)

    def _configure_topology(self):
        self.stop_topology()
        self.api._remove(self.api._topology, [])
        ixn_topos = self.create_node(self._ixn_config, "topology")
        # Configured all interfaces
        self._configure_device_group(ixn_topos)

        # Configure all MACsec interface before configure protocols
        for device in self.api.snappi_config.devices:
            self._macsec.config(device)

        # We need to configure all interface before configure protocols
        for device in self.api.snappi_config.devices:
            self._bgp.config(device)

        # Configure all RoCEv2 interface before configure protocols
        for device in self.api.snappi_config.devices:
            self._rocev2.config(device)

        # Configure all Isis interface before configure protocols
        for device in self.api.snappi_config.devices:
            self._isis.config(device)

        # Compaction will take place in this order
        # Step-1: Compact chain DGs
        for chain_parent_dg in self._chain_parent_dgs:
            self.compactor.compact(chain_parent_dg.get("deviceGroup"))
            self._set_dev_compacted(chain_parent_dg.get("deviceGroup"))

        # Step-2: Compact VXLAN
        source_interfaces = self._vxlan.source_interfaces
        for v4_int in source_interfaces.ipv4:
            self.compactor.compact(v4_int.get("vxlan"))
        for v6_int in source_interfaces.ipv6:
            self.compactor.compact(v6_int.get("vxlanv6"))

        # Step-3: First compact all loopback interfaces
        for ix_parent_dg in self.loopback_parent_dgs:
            self.compactor.compact(ix_parent_dg.get("deviceGroup"))

        # Step-4: Compact root Topology
        for ixn_topo in self._ixn_topo_objects.values():
            self.compactor.compact(ixn_topo.get("deviceGroup"))
            self._set_dev_compacted(ixn_topo.get("deviceGroup"))

    def _is_ip_allowed(self):
        is_allowed = True
        self.logger.debug(
            "Checking if IPv4/ v6 is allowed when MACsec is present"
        )
        for device in self.api.snappi_config.devices:
            is_allowed = self._macsec._is_ip_allowed(device)
            if is_allowed == False:
                break
        return is_allowed

    def _configure_device_group(self, ixn_topos):
        """map ethernet with a ixn deviceGroup with multiplier = 1"""
        port_name = None
        device_chain_dgs = {}
        self.is_ip_allowed = self._is_ip_allowed()
        for device in self.api.snappi_config.devices:
            chin_dgs = {}
            ethernets = device.get("ethernets")
            if ethernets is None:
                continue
            for ethernet in ethernets:
                if ethernet.get("connection") and ethernet.get("port_name"):
                    raise Exception(
                        "port_name and connection for ethernet configuration cannot be passed together, use either connection or port_name property. \
                            port_name is deprecated and will be removed in future releases."
                    )
                if ethernet.get("connection"):
                    connection_choice = ethernet.get("connection").choice
                    if connection_choice == "port_name":
                        port_name = ethernet.get("connection").port_name
                    elif connection_choice == "lag_name":
                        port_name = ethernet.get("connection").lag_name
                    elif connection_choice == "vxlan_name":
                        port_name = ethernet.get("connection").vxlan_name
                        if port_name in chin_dgs:
                            chin_dgs[port_name].append(ethernet)
                        else:
                            chin_dgs[port_name] = [ethernet]
                        continue
                else:
                    port_name = ethernet.get("port_name")
                if port_name is None:
                    raise Exception(
                        "port_name is not passed for the device {}".format(
                            device.get("name")
                        )
                    )
                if port_name in self._ixn_topo_objects:
                    ixn_topo = self._ixn_topo_objects[port_name]
                else:
                    ixn_topo = self.add_element(ixn_topos)
                    ixn_topo["name"] = self._get_topology_name(port_name)
                    ixn_topo["ports"] = [
                        self.api.ixn_objects.get_xpath(port_name)
                    ]
                    self._ixn_topo_objects[port_name] = ixn_topo
                ixn_dg = self.create_node_elemet(
                    ixn_topo, "deviceGroup", device.get("name")
                )
                ixn_dg["multiplier"] = 1
                self.working_dg = ixn_dg
                self.set_device_info(device, ixn_dg)
                self._ethernet.config(ethernet, ixn_dg)
            device_chain_dgs[device.name] = chin_dgs

        # Create all ethernet before start loopback
        self.loopback_parent_dgs = self._loop_back.config()

        for device in self.api.snappi_config.devices:
            vxlan = device.get("vxlan")
            if vxlan is None:
                continue
            self.working_dg = self.api.ixn_objects.get_working_dg(device.name)
            self._vxlan.config(vxlan)

        # Wait till all primary DG will configure
        for device in self.api.snappi_config.devices:
            chin_dgs = device_chain_dgs.get(device.name)
            if chin_dgs is None:
                continue
            for connected_to, ethernet_list in chin_dgs.items():
                ixn_working_dg = self.api.ixn_objects.get_working_dg(
                    connected_to
                )
                self._chain_parent_dgs.append(ixn_working_dg)
                for ethernet in ethernet_list:
                    ixn_dg = self.create_node_elemet(
                        ixn_working_dg, "deviceGroup", device.get("name")
                    )
                    ixn_dg["multiplier"] = 1
                    self.working_dg = ixn_dg
                    self.set_device_info(device, ixn_dg)
                    self._ethernet.config(ethernet, ixn_dg)

    def _pushixnconfig(self):
        self.logger.debug("pushing ixnet config")
        erros = self.api.get_errors()
        if len(erros) > 0:
            return
        ixn_cnf = json.dumps(self._ixn_config, indent=2)
        errata = self._resource_manager.ImportConfig(ixn_cnf, False)
        for item in errata:
            self.api.warning(item)

    def stop_topology(self):
        glob_topo = self.api._globals.Topology.refresh()
        if glob_topo.Status == "started":
            self.logger.debug("Stopping topology")
            self.api._ixnetwork.StopAllProtocols("sync")

    def set_protocol_state(self, request):
        if request.state is None:
            raise Exception("state is None within set_protocol_state")
        self.logger.debug("Setting protocol with %s" % request.state)
        if request.state == "start":
            if len(self.api._topology.find()) > 0:
                self.api._ixnetwork.StartAllProtocols("sync")
                self.api.check_protocol_statistics()
        else:
            if len(self.api._topology.find()) > 0:
                self.api._ixnetwork.StopAllProtocols("sync")

    def set_route_state(self, payload):
        if payload.state is None:
            return
        names = payload.names
        if len(names) == 0:
            names = self.api.ixn_routes.names
        ixn_obj_idx_list = {}
        names = list(set(names))
        self.logger.debug("set route state for %s" % names)
        for name in names:
            route_info = self.api.ixn_routes.get(name)
            ixn_obj = None
            for obj in ixn_obj_idx_list.keys():
                if obj.xpath == route_info.xpath:
                    ixn_obj = obj
                    break
            if ixn_obj is None:
                ixn_obj_idx_list[route_info] = list(
                    range(
                        route_info.index,
                        route_info.index + route_info.multiplier,
                    )
                )
            else:
                ixn_obj_idx_list[route_info].extend(
                    list(
                        range(
                            route_info.index,
                            route_info.index + route_info.multiplier,
                        )
                    )
                )
        imports = []
        for obj, index_list in ixn_obj_idx_list.items():
            xpath = obj.xpath
            active = "active"
            index_list = list(set(index_list))
            object_info = self.select_properties(xpath, properties=[active])
            values = object_info[active]["values"]
            for idx in index_list:
                values[idx] = Ngpf._ROUTE_STATE[payload.state]
            imports.append(self.configure_value(xpath, active, values))
        self.imports(imports)
        self.api._ixnetwork.Globals.Topology.ApplyOnTheFly()
        return names

    def set_device_state(self, payload):
        lmp_names = payload.member_ports.lag_member_names
        state = payload.member_ports.state
        if lmp_names is None:
            self._lacp_start_stop_pdu(state, 1)
        else:
            for lag, ports in self.api.lag._lag_ports.items():
                for index, port in enumerate(ports):
                    for lmp_n in lmp_names:
                        if port.port_name == lmp_n:
                            self._lacp_start_stop_pdu(state, index + 1, lag)

    def _lacp_start_stop_pdu(self, state, index=1, lag_name=None):
        if lag_name is None:
            lag_port_lacp = (
                self.api._ixnetwork.Lag.find()
                .ProtocolStack.find()
                .Ethernet.find()
                .Lagportlacp.find()
            )
            if state == "up":
                lag_port_lacp.LacpStartPDU()
            elif state == "down":
                lag_port_lacp.LacpStopPDU()
        else:
            lag_port_lacp = (
                self.api._ixnetwork.Lag.find(Name=lag_name)
                .ProtocolStack.find()
                .Ethernet.find()
                .Lagportlacp.find()
            )
            if state == "up":
                lag_port_lacp.LacpStartPDU(SessionIndices=index)
            elif state == "down":
                lag_port_lacp.LacpStopPDU(SessionIndices=index)

    def get_states(self, request):
        self.logger.debug("get_states for %s" % request.choice)
        if request.choice == "ipv4_neighbors":
            ip_objs = (
                self.api._ixnetwork.Topology.find()
                .DeviceGroup.find()
                .Ethernet.find()
                .Ipv4.find()
            )
            resolved_mac_list = self._get_ether_resolved_mac(
                ip_objs,
                self.ether_v4gateway_map,
                request.ipv4_neighbors,
                "ipv4",
            )
        elif request.choice == "ipv6_neighbors":
            ip_objs = (
                self.api._ixnetwork.Topology.find()
                .DeviceGroup.find()
                .Ethernet.find()
                .Ipv6.find()
            )
            resolved_mac_list = self._get_ether_resolved_mac(
                ip_objs,
                self.ether_v6gateway_map,
                request.ipv6_neighbors,
                "ipv6",
            )
        else:
            raise TypeError(
                "get_states only accept ipv4_neighbors or ipv6_neighbors"
            )

        return {"choice": request.choice, request.choice: resolved_mac_list}

    def _get_ether_resolved_mac(
        self, ip_objs, ether_gateway_map, ip_neighbors, choice
    ):
        arp_entries = {}
        for ip_obj in ip_objs:
            resolved_mac_list = ip_obj.ResolvedGatewayMac
            for index, gateway in enumerate(ip_obj.GatewayIp.Values):
                resolved_mac = resolved_mac_list[index]
                if re.search("unresolved", resolved_mac.lower()) is not None:
                    resolved_mac = None
                arp_entries[gateway] = resolved_mac

        ethernet_names = ip_neighbors.ethernet_names
        if ethernet_names is None:
            ethernet_names = ether_gateway_map.keys()
        resolved_mac_list = []
        for ethernet_name in ethernet_names:
            gateway_ips = ether_gateway_map[ethernet_name]
            for gateway_ip in gateway_ips:
                if gateway_ip not in arp_entries:
                    raise Exception(
                        "{} not found within current configured gateway ips".format(
                            gateway_ip
                        )
                    )
                if choice == "ipv4":
                    resolved_mac_list.append(
                        {
                            "ethernet_name": ethernet_name,
                            "ipv4_address": gateway_ip,
                            "link_layer_address": arp_entries[gateway_ip],
                        }
                    )
                elif choice == "ipv6":
                    resolved_mac_list.append(
                        {
                            "ethernet_name": ethernet_name,
                            "ipv6_address": gateway_ip,
                            "link_layer_address": arp_entries[gateway_ip],
                        }
                    )
        self.logger.debug(
            "These are resolved_mac_list: %s" % resolved_mac_list
        )
        return resolved_mac_list

    def _get_href(self, xpath):
        return xpath.replace("[", "/").replace("]", "")

    def select_properties(self, xpath, properties=[]):
        href = self._get_href(xpath)
        payload = {
            "selects": [
                {
                    "from": href,
                    "properties": properties,
                    "children": [],
                    "inlines": [
                        {
                            "child": "multivalue",
                            "properties": ["format", "pattern", "values"],
                        }
                    ],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self.api._ixnetwork.href
        results = self.api._ixnetwork._connection._execute(url, payload)
        try:
            return results[0]
        except Exception:
            raise Exception("Problem to select %s" % href)

    def imports(self, imports):
        self.logger.debug("imports of portion of config")
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False
            )
            for item in errata:
                self.api.warning(item)
            return len(errata) == 0
        return True

    def configure_value(self, source, attribute, value, enum_map=None):
        if value is None:
            return
        xpath = "/multivalue[@source = '{0} {1}']".format(source, attribute)
        if isinstance(value, list) and len(set(value)) == 1:
            value = value[0]
        if enum_map is not None:
            if isinstance(value, list):
                value = [enum_map[val] for val in value]
            else:
                value = enum_map[value]
        if isinstance(value, list):
            ixn_value = {
                "xpath": "{0}/valueList".format(xpath),
                "values": value,
            }
        else:
            ixn_value = {
                "xpath": "{0}/singleValue".format(xpath),
                "value": value,
            }
        return ixn_value
