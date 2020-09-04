import json


class Ngpf(object):
    """Ngpf configuration

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    """
    _TPID_MAP = {
        '8100': 'ethertype8100',
        '88a8': 'ethertype88a8',
        '9100': 'ethertype9100',
        '9200': 'ethertype9200',
        '9300': 'ethertype9300',
    }

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        
    def config(self):
        """Configure config.devices onto Ixnetwork.Topology
        
        CRUD
        ----
        - DELETE any ngpf object that does not exist in config.devices
        - CREATE ngpf object for any config.devices...name that does not exist
        - UPDATE ngpf object for any config...name that exists
        """
        self._configure_topology(self._api._topology, self._api.config.device_groups)

    def _configure_topology(self, ixn_topology, device_groups):
        """Resolve abstract device_groups with ixnetwork topologies
        """
        self._api._remove(ixn_topology, device_groups)
        for device_group in device_groups:
            port_regex = '^(%s)$' % '|'.join(device_group.port_names)
            args = {
                'Name': device_group.name,
                'Ports': self._api._vport.find(Name=port_regex)
            }
            ixn_topology.find(Name=device_group.name)
            if len(ixn_topology) == 0:
                ixn_topology.add(**args)[-1]
            else:
                ixn_topology.update(**args)
            self._api.ixn_objects[device_group.name] = ixn_topology.href
            self._configure_device_group(ixn_topology.DeviceGroup, device_group.devices)

    def _configure_device_group(self, ixn_device_group, devices):
        """Resolve abstract devices with ixnetwork device_groups 
        """
        self._api._remove(ixn_device_group, devices)
        if (devices) :
            for device in devices:
                args = {
                    'Name': device.name,
                    'Multiplier': device.devices_per_port
                }
                ixn_device_group.find(Name=device.name)
                if len(ixn_device_group) == 0:
                    ixn_device_group.add(**args)[-1]
                else:
                    ixn_device_group.update(**args)
                self._api.ixn_objects[device.name] = ixn_device_group.href
                self._configure_ethernet(ixn_device_group.Ethernet, device.ethernets)
                self._configure_device_group(ixn_device_group.DeviceGroup, device.devices)

    def _configure_pattern(self, ixn_obj, pattern, enum_map=None):
        if pattern is None:
            return
        elif enum_map is not None and pattern.fixed is not None:
            ixn_obj.Single(enum_map[pattern.fixed])
        elif pattern.choice == 'fixed':
            ixn_obj.Single(pattern.fixed)
        elif pattern.choice == 'list':
            ixn_obj.ValueList(pattern.list)
        elif pattern.choice == 'counter':
            pass
        elif pattern.choice == 'random':
            pass

    def _configure_ethernet(self, ixn_ethernet, ethernets):
        """Transform Device.Ethernet to /topology/.../ethernet
        """
        self._api._remove(ixn_ethernet, ethernets)
        for ethernet in ethernets:
            args = {
                'Name': ethernet.name,
            }
            ixn_ethernet.find(Name=ethernet.name)
            if len(ixn_ethernet) == 0:
                ixn_ethernet.add(**args)
            else:
                ixn_ethernet.update(**args)
            self._api.ixn_objects[ethernet.name] = ixn_ethernet.href
            self._configure_pattern(ixn_ethernet.Mac, ethernet.mac)
            self._configure_pattern(ixn_ethernet.Mtu, ethernet.mtu)
            if (ethernet.vlans) :
                ixn_ethernet.VlanCount = len(ethernet.vlans)
                ixn_ethernet.EnableVlans.Single(ixn_ethernet.VlanCount > 0)
                self._configure_vlan(ixn_ethernet.Vlan, ethernet.vlans)
            self._configure_ipv4(ixn_ethernet.Ipv4, ethernet.ipv4)
            self._configure_ipv6(ixn_ethernet.Ipv6, ethernet.ipv6)

    def _configure_vlan(self, ixn_vlans, vlans):
        """Transform Device.Vlan to /topology/.../vlan
        """
        for i in range(0, len(ixn_vlans.find())):
            args = {
                'Name': vlans[i].name
            }
            ixn_vlan = ixn_vlans[i]
            ixn_vlan.update(**args)
            self._api.ixn_objects[vlans[i].name] = ixn_vlan.href
            self._configure_pattern(ixn_vlan.VlanId, vlans[i].id)
            self._configure_pattern(ixn_vlan.Priority, vlans[i].priority)
            self._configure_pattern(ixn_vlan.Tpid, vlans[i].tpid, enum_map=Ngpf._TPID_MAP)

    def _configure_ipv4(self, ixn_ipv4, ipv4):
        """Transform Device.Ipv4 to /topology/.../ipv4
        """
        if ipv4 is None:
            return
        ixn_ipv4.find('^((?!%s).)*$' % ipv4.name).remove()
        args = {
            'Name': ipv4.name,
        }
        ixn_ipv4.find(Name=ipv4.name)
        if len(ixn_ipv4) == 0:
            ixn_ipv4.add(**args)[-1]
        else:
            ixn_ipv4.update(**args)
        self._api.ixn_objects[ipv4.name] = ixn_ipv4.href
        self._configure_pattern(ixn_ipv4.Address, ipv4.address)
        self._configure_pattern(ixn_ipv4.GatewayIp, ipv4.gateway)
        self._configure_pattern(ixn_ipv4.Prefix, ipv4.prefix)
        self._configure_bgpv4(ixn_ipv4.BgpIpv4Peer, ipv4.bgpv4)

    def _configure_ipv6(self, ixn_ipv6, ipv6):
        if ipv6 is None:
            return
        ixn_ipv6.find('^((?!%s).)*$' % ipv6.name).remove()
        args = {
            'Name': ipv6.name,
        }
        ixn_ipv6.find(Name=ipv6.name)
        if len(ixn_ipv6) == 0:
            ixn_ipv6.add(**args)[-1]
        else:
            ixn_ipv6.update(**args)
        self._api.ixn_objects[ipv6.name] = ixn_ipv6.href

    def _configure_bgpv4(self, ixn_bgpv4, bgpv4):
        if bgpv4 is None:
            return
        ixn_bgpv4.find('^((?!%s).)*$' % bgpv4.name).remove()
        args = {
            'Name': bgpv4.name,
        }
        ixn_bgpv4.find(Name=bgpv4.name)
        if len(ixn_bgpv4) == 0:
            ixn_bgpv4.add(**args)[-1]
        else:
            ixn_bgpv4.update(**args)
        self._api.ixn_objects[bgpv4.name] = ixn_bgpv4.href
