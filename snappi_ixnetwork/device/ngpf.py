import re
import json

from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.device.base import *
from snappi_ixnetwork.device.bgp import Bgp
from snappi_ixnetwork.device.ethernet import Ethernet
from snappi_ixnetwork.device.compactor import Compactor
from snappi_ixnetwork.device.createixnconfig import CreateIxnConfig


class Ngpf(Base):
    _DEVICE_ENCAP_MAP = {
        "DeviceEthernet": "ethernetVlan",
        "DeviceIpv4": "ipv4",
        "DeviceIpv6": "ipv6",
        "BgpV4Peer": "ipv4",
        "BgpV6Peer": "ipv6",
        "BgpV4RouteRange": "ipv4",
        "BgpV6RouteRange": "ipv4"
    }

    _ROUTE_OBJECTS = [
        "BgpV4RouteRange", "BgpV6RouteRange"
    ]

    _ROUTE_STATE = {
        "advertise": True,
        "withdraw": False
    }

    def __init__(self, ixnetworkapi):
        super(Ngpf, self).__init__()
        self._api = ixnetworkapi
        self._ixn_config = {}
        self._ixn_topo_objects = {}
        self._ethernet = Ethernet(self)
        self._bgp = Bgp(self)
        self.compactor = Compactor(self._api)
        self._createixnconfig = CreateIxnConfig(self)

    def config(self):
        self._ixn_topo_objects = {}
        self.working_dg = None
        self._ixn_config = dict()
        self._ixn_config["xpath"] = "/"
        self._resource_manager = self._api._ixnetwork.ResourceManager
        with Timer(self._api, "Convert device config :"):
            self._configure_topology()
        with Timer(self._api, "Create IxNetwork config :"):
            self._createixnconfig.create(
                self._ixn_config["topology"], "topology"
            )
        with Timer(self._api, "Push IxNetwork config :"):
            self._pushixnconfig()

    def set_device_info(self, snappi_obj, ixn_obj):
        name = snappi_obj.get("name")
        class_name = snappi_obj.__class__.__name__
        try:
            encap = Ngpf._DEVICE_ENCAP_MAP[class_name]
        except KeyError:
            raise NameError(
                "Mapping is missing for {0}".format(class_name)
            )
        self._api.set_device_encap(name, encap)
        self._api.set_device_encap(
            self.get_name(self.working_dg), encap
        )
        self._api.ixn_objects.set(name, ixn_obj)
        if class_name in Ngpf._ROUTE_OBJECTS:
            self._api.ixn_routes.append(name)

    def _get_topology_name(self, port_name):
        return "Topology %s" % port_name

    def _set_dev_compacted(self, dgs):
        if dgs is None:
            return
        for dg in dgs:
            names = dg.get("name")
            if isinstance(names, list) and len(names) > 1:
                self._api.set_dev_compacted(names[0], names)

    def _configure_topology(self):
        self.stop_topology()
        self._api._remove(self._api._topology, [])
        ixn_topos = self.create_node(self._ixn_config, "topology")
        for device in self._api.snappi_config.devices:
            self._configure_device_group(device, ixn_topos)

        for ixn_topo in self._ixn_topo_objects.values():
            self.compactor.compact(ixn_topo.get(
                "deviceGroup"
            ))
            self._set_dev_compacted(ixn_topo.get(
                "deviceGroup"
            ))


    def _configure_device_group(self, device, ixn_topos):
        """map ethernet with a ixn deviceGroup with multiplier = 1"""
        for ethernet in device.get("ethernets"):
            port_name = ethernet.get("port_name")
            if port_name in self._ixn_topo_objects:
                ixn_topo = self._ixn_topo_objects[port_name]
            else:
                ixn_topo = self.add_element(ixn_topos)
                ixn_topo["name"] = self._get_topology_name(port_name)
                ixn_topo["ports"] = [self._api.ixn_objects.get_xpath(port_name)]
                self._ixn_topo_objects[port_name] = ixn_topo
            ixn_dg = self.create_node_elemet(
                ixn_topo, "deviceGroup", device.get("name")
            )
            ixn_dg["multiplier"] = 1
            self.working_dg = ixn_dg
            self._ethernet.config(ethernet, ixn_dg)
        self._bgp.config(device)


    def _pushixnconfig(self):
        ixn_cnf = json.dumps(self._ixn_config, indent=2)
        print(ixn_cnf)
        errata = self._resource_manager.ImportConfig(
            ixn_cnf, False
        )
        for item in errata:
            self._api.warning(item)

    def stop_topology(self):
        glob_topo = self._api._globals.Topology.refresh()
        if glob_topo.Status == "started":
            self._api._ixnetwork.StopAllProtocols("sync")

    def set_route_state(self, payload):
        if payload.state is None:
            return
        names = payload.names
        if len(names) == 0:
            names = self._api.ixn_routes
        ixn_obj_idx_list = {}
        names = list(set(names))
        for name in names:
            route_info = self._api.get_route_object(name)
            ixn_obj = None
            for obj in ixn_obj_idx_list.keys():
                if obj.xpath == route_info.xpath:
                    ixn_obj = obj
                    break
            if ixn_obj is None:
                ixn_obj_idx_list[route_info] = list(range(
                    route_info.index, route_info.index + route_info.multiplier
                ))
            else:
                ixn_obj_idx_list[route_info].extend(list(range(
                    route_info.index, route_info.index + route_info.multiplier
                )))
        imports = []
        for obj, index_list in ixn_obj_idx_list.items():
            xpath = obj.xpath
            if re.search("ipv4PrefixPools", xpath):
                xpath += "/bgpIPRouteProperty[1]"
            else:
                xpath += "/bgpV6IPRouteProperty[1]"
            active = "active"
            index_list = list(set(index_list))
            object_info = self.select_properties(
                xpath , properties=[active]
            )
            values = object_info[active]["values"]
            for idx in index_list:
                values[idx] = Ngpf._ROUTE_STATE[payload.state]
            imports.append(self.configure_value(
                xpath, active, values
            ))
        self.imports(imports)
        self._api._ixnetwork.Globals.Topology.ApplyOnTheFly()
        return names

    def _get_href(self, xpath):
        return xpath.replace('[', '/').\
            replace(']', '')

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
                            "properties": ["format", "pattern", "values"]
                        }
                    ]
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        try:
            return results[0]
        except Exception:
            raise Exception("Problem to select %s" % href)

    def imports(self, imports):
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False
            )
            for item in errata:
                self._api.warning(item)
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