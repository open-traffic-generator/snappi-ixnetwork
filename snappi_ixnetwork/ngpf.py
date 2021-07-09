import json
from snappi_ixnetwork.configurebgp import ConfigureBgp


class Ngpf(object):
    """Ngpf configuration

    Args
    ----
    - ixnetworkapi (Api): instance of the ixnetworkapi class
    """

    _TPID_MAP = {
        "8100": "ethertype8100",
        "88a8": "ethertype88a8",
        "9100": "ethertype9100",
        "9200": "ethertype9200",
        "9300": "ethertype9300",
    }

    # Select type of Traffic
    _DEVICE_ENCAP_MAP = {
        "ethernet": "ethernetVlan",
        "ipv4": "ipv4",
        "ipv6": "ipv6",
        "bgpv4": "ipv4",
        "bgpv6": "ipv6",
    }

    _ROUTE_STATE = {"advertise": True, "withdraw": False}

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._conf_bgp = ConfigureBgp(self)

    def config(self):
        """Transform /components/schemas/Device into /topology"""
        self.imports = []
        self._resource_manager = self._api._ixnetwork.ResourceManager
        self._configure_topology(
            self._api._topology, self._api.snappi_config.devices
        )
        self._import(self.imports)

    def update(self, ixn_object, **kwargs):
        update = False
        for name, value in kwargs.items():
            if getattr(ixn_object, name) != value:
                update = True
        if update is True:
            ixn_object.update(**kwargs)

    def _import(self, imports):
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False
            )
            for item in errata:
                self._api.warning(item)
            return len(errata) == 0
        return True

    def _configure_topology(self, ixn_topology, devices):
        """One /topology for every unique device.container_name
        Topology name is device.container_name
        """
        topologies = {}
        devices_in_topos = {}
        devices = devices._items
        for device in devices:
            topology = lambda: None
            if device.container_name is None:
                raise NameError("container_name should not None")
            topology.name = self._api._get_topology_name(device.container_name)
            topologies[topology.name] = topology
            if topology.name in devices_in_topos:
                devices_in_topos[topology.name].append(device)
            else:
                devices_in_topos[topology.name] = [device]
        self._api._remove(ixn_topology, topologies.values())
        for topo_name, devices_in_topo in devices_in_topos.items():
            ixn_topology.find(Name="^%s$" % self._api.special_char(topo_name))
            if len(ixn_topology) > 0:
                self._api._remove(ixn_topology.DeviceGroup, devices_in_topo)
        for device in devices:
            args = {
                "Name": self._api._get_topology_name(device.container_name),
                "Ports": [self._api.ixn_objects[device.container_name]],
            }
            ixn_topology.find(
                Name="^%s$" % self._api.special_char(args["Name"])
            )
            if len(ixn_topology) == 0:
                ixn_topology.add(**args)
            else:
                self.update(ixn_topology, **args)
            self._api.ixn_objects[ixn_topology.Name] = ixn_topology.href
            self._configure_device_group(ixn_topology.DeviceGroup, device)

    def _configure_device_group(self, ixn_device_group, device):
        """Transform /components/schemas/Device into /topology/deviceGroup
        One /topology/deviceGroup for every device in port.devices
        """
        args = {"Name": device.name, "Multiplier": 1}
        ixn_device_group.find(
            Name="^%s$" % self._api.special_char(device.name)
        )
        if len(ixn_device_group) == 0:
            ixn_device_group.add(**args)[-1]
        else:
            ixn_ng = ixn_device_group.NetworkGroup
            self._api._remove(ixn_ng, [])
            self.update(ixn_device_group, **args)
        self._config_proto_stack(ixn_device_group, device, ixn_device_group)

    def _config_proto_stack(self, ixn_obj, snappi_obj, ixn_dg):
        self._api.ixn_objects[snappi_obj.name] = ixn_obj.href
        properties = snappi_obj._properties
        for prop_name in properties:
            stack_class = getattr(
                self, "_configure_{0}".format(prop_name), None
            )
            if stack_class is not None:
                child = properties[prop_name]
                if prop_name not in Ngpf._DEVICE_ENCAP_MAP:
                    raise Exception(
                        "Mapping is missing for {0}".format(prop_name)
                    )
                self._api._device_encap[ixn_dg.Name] = Ngpf._DEVICE_ENCAP_MAP[
                    prop_name
                ]
                if child.name is not None:
                    self._api._device_encap[
                        child.name
                    ] = Ngpf._DEVICE_ENCAP_MAP[prop_name]
                new_ixn_obj = stack_class(ixn_obj, child, ixn_dg)
                self._config_proto_stack(new_ixn_obj, child, ixn_dg)

    def _configure_pattern(self, ixn_obj, pattern, enum_map=None):
        if pattern is None:
            return
        # Asymmetric support- without pattern
        if pattern.get("choice") is None:
            if enum_map is not None:
                ixn_obj.Single(enum_map[pattern])
            elif isinstance(pattern, list):
                ixn_obj.ValueList(pattern)
            else:
                ixn_obj.Single(pattern)
        # Symmetric support with pattern
        else:
            if pattern.get("choice") is None:
                return
            elif enum_map is not None and pattern.get("choice") == "value":
                ixn_obj.Single(enum_map[pattern.value])
            elif pattern.get("choice") == "value":
                ixn_obj.Single(pattern.value)
            elif pattern.get("choice") == "values":
                ixn_obj.ValueList(pattern.values)
            elif pattern.get("choice") == "increment":
                ixn_obj.Increment(
                    pattern.increment.start, pattern.increment.step
                )
            elif pattern.get("choice") == "decrement":
                ixn_obj.Decrement(
                    pattern.decrement.start, pattern.decrement.step
                )
            elif pattern.get("choice") == "random":
                pass

    def configure_value(self, source, attribute, value, enum_map=None):
        if value is None:
            return
        xpath = "/multivalue[@source = '{0} {1}']".format(source, attribute)
        if enum_map is not None:
            value = enum_map[value]
        if isinstance(value, list):
            if len(set(value)) == 1:
                ixn_value = {
                    "xpath": "{0}/singleValue".format(xpath),
                    "value": value[0],
                }
            else:
                ixn_value = {
                    "xpath": "{0}/valueList".format(xpath),
                    "values": value,
                }
        else:
            ixn_value = {
                "xpath": "{0}/singleValue".format(xpath),
                "value": value,
            }
        self.imports.append(ixn_value)

    def get_xpath(self, href):
        payload = {
            "selects": [
                {"from": href, "properties": [], "children": [], "inlines": []}
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        try:
            return results[0]["xpath"]
        except Exception:
            raise Exception("Problem to select %s" % href)

    def select_node(self, href, children=[]):
        payload = {
            "selects": [
                {
                    "from": href,
                    "properties": [],
                    "children": [
                        {
                            "child": "^({0})$".format("|".join(children)),
                            "properties": [],
                            "filters": [],
                        }
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        try:
            return results[0]
        except Exception:
            raise Exception("Problem to select %s" % href)

    def select_child_node(self, href, child):
        payload = {
            "selects": [
                {
                    "from": href,
                    "properties": [],
                    "children": [
                        {"child": child, "properties": [], "filters": []}
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        try:
            return results[0][child]
        except Exception:
            raise Exception("Problem to select %s" % href)

    def _configure_ethernet(self, ixn_parent, ethernet, ixn_dg):
        """Transform Device.Ethernet to /topology/.../ethernet"""
        ixn_ethernet = ixn_parent.Ethernet
        self._api._remove(ixn_ethernet, [ethernet])
        args = {}
        ixn_ethernet.find(Name="^%s$" % self._api.special_char(ethernet.name))
        if len(ixn_ethernet) == 0:
            ixn_ethernet.add(**args)
        else:
            self.update(ixn_ethernet, **args)
        if ethernet.name is not None:
            self._api.ixn_objects[ethernet.name] = ixn_ethernet.href
            ixn_ethernet.Name = ethernet.name
        eth_info = self.select_node(
            ixn_ethernet.href, children=["ipv4", "ipv6"]
        )
        eth_xpath = eth_info["xpath"]
        self.configure_value(eth_xpath, "mac", ethernet.mac)
        self.configure_value(eth_xpath, "mtu", ethernet.mtu)
        if len(ethernet.vlans) > 0:
            ixn_ethernet.VlanCount = len(ethernet.vlans)
            ixn_ethernet.EnableVlans.Single(ixn_ethernet.VlanCount > 0)
            self._configure_vlan(ixn_ethernet.Vlan, ethernet.vlans)
        if (
            ethernet.get("ipv4") is not None
            and ethernet.get("ipv6") is not None
        ):
            return ixn_ethernet
        elif (
            ethernet.get("ipv4") is not None
            and eth_info.get("ipv6") is not None
        ):
            ixn_ethernet.Ipv6.find().remove()
        elif (
            ethernet.get("ipv6") is not None
            and eth_info.get("ipv4") is not None
        ):
            ixn_ethernet.Ipv4.find().remove()
        return ixn_ethernet

    def _configure_vlan(self, ixn_vlans, vlans):
        """Transform Device.Vlan to /topology/.../vlan"""
        for i in range(0, len(ixn_vlans.find())):
            ixn_vlan = ixn_vlans[i]
            if vlans[i].name is not None:
                args = {"Name": vlans[i].name}
                self.update(ixn_vlan, **args)
                self._api.ixn_objects[vlans[i].name] = ixn_vlan.href
            vlan_xpath = self.get_xpath(ixn_vlan.href)
            self.configure_value(vlan_xpath, "vlanId", vlans[i].id)
            self.configure_value(vlan_xpath, "priority", vlans[i].priority)
            self.configure_value(
                vlan_xpath, "tpid", vlans[i].tpid, enum_map=Ngpf._TPID_MAP
            )

    def _configure_ipv4(self, ixn_parent, ipv4, ixn_dg):
        """Transform Device.Ipv4 to /topology/.../ipv4"""
        ixn_ipv4 = ixn_parent.Ipv4
        self._api._remove(ixn_ipv4, [ipv4])
        args = {}
        ixn_ipv4.find(Name="^%s$" % self._api.special_char(ipv4.name))
        if len(ixn_ipv4) == 0:
            ixn_ipv4.add(**args)[-1]
        else:
            self.update(ixn_ipv4, **args)
        if ipv4.name is not None:
            ixn_ipv4.Name = ipv4.name
            self._api.ixn_objects[ipv4.name] = ixn_ipv4.href
        ip_xpath = self.get_xpath(ixn_ipv4.href)
        self.configure_value(ip_xpath, "address", ipv4.address)
        self.configure_value(ip_xpath, "gatewayIp", ipv4.gateway)
        self.configure_value(ip_xpath, "prefix", ipv4.prefix)
        return ixn_ipv4

    def _configure_bgpv4(self, ixn_parent, bgpv4, ixn_dg):
        return self._conf_bgp.configure_bgpv4(ixn_parent, bgpv4, ixn_dg)

    def _configure_ipv6(self, ixn_parent, ipv6, ixn_dg):
        ixn_ipv6 = ixn_parent.Ipv6
        self._api._remove(ixn_ipv6, [ipv6])
        args = {}
        ixn_ipv6.find(Name="^%s$" % self._api.special_char(ipv6.name))
        if len(ixn_ipv6) == 0:
            ixn_ipv6.add(**args)[-1]
        else:
            self.update(ixn_ipv6, **args)
        if ipv6.name is not None:
            ixn_ipv6.Name = ipv6.name
            self._api.ixn_objects[ipv6.name] = ixn_ipv6.href
        ip_xpath = self.get_xpath(ixn_ipv6.href)
        self.configure_value(ip_xpath, "address", ipv6.address)
        self.configure_value(ip_xpath, "gatewayIp", ipv6.gateway)
        self.configure_value(ip_xpath, "prefix", ipv6.prefix)
        return ixn_ipv6

    def _configure_bgpv6(self, ixn_parent, bgpv6, ixn_dg):
        return self._conf_bgp.configure_bgpv6(ixn_parent, bgpv6, ixn_dg)

    def set_route_state(self, payload):
        if payload.state is None:
            return
        names = payload.names
        if len(names) == 0:
            names = self._api.ixn_route_objects.keys()
        for name in names:
            ixn_route = self._api.get_route_object(name)
            ixn_route.Active.Single(Ngpf._ROUTE_STATE[payload.state])
        self._api._ixnetwork.Globals.Topology.ApplyOnTheFly()
        return names
