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
        """Transform /components/schemas/Device into /topology
        """
        self._imports = []
        self._configure_topology(self._api._topology, self._api.config.devices)

    def _update(self, ixn_object, **kwargs):
        update = False
        for name, value in kwargs.items():
            if getattr(ixn_object, name) != value:
                update = True
        if update is True:
            ixn_object.update(**kwargs)

    def _configure_topology(self, ixn_topology, devices):
        """One /topology for every unique device.container_name
        Topology name is device.container_name
        """
        topologies = {}
        for device in devices:
            topology = lambda: None
            topology.name = self._api._get_topology_name(device.container_name)
            topologies[topology.name] = topology
        self._api._remove(ixn_topology, topologies.values())
        for device in devices:
            ixn_topology.find(
                Name='^%s$' % self._api._get_topology_name(device.container_name))
            if len(ixn_topology) > 0:
                self._api._remove(ixn_topology.DeviceGroup, [device])
        for device in devices:
            args = {
                'Name': self._api._get_topology_name(device.container_name),
                'Ports': [self._api.ixn_objects[device.container_name]]
            }
            ixn_topology.find(Name='^%s$' % args['Name'])
            if len(ixn_topology) == 0:
                ixn_topology.add(**args)
            else:
                self._update(ixn_topology, **args)
            self._api.ixn_objects[ixn_topology.Name] = ixn_topology.href
            self._configure_device_group(ixn_topology.DeviceGroup, device)

    def _configure_device_group(self, ixn_device_group, device):
        """Transform /components/schemas/Device into /topology/deviceGroup
        One /topology/deviceGroup for every device in port.devices 
        """
        args = {'Name': device.name, 'Multiplier': device.device_count}
        ixn_device_group.find(Name='^%s$' % device.name)
        if len(ixn_device_group) == 0:
            ixn_device_group.add(**args)[-1]
        else:
            self._update(ixn_device_group, **args)
        self._api.ixn_objects[device.name] = ixn_device_group.href
        if device.choice == 'ethernet':
            self._configure_ethernet(ixn_device_group.Ethernet,
                                     device.ethernet)
        elif device.choice == 'ipv4':
            ixn_ethernet = self._configure_ethernet(ixn_device_group.Ethernet,
                                                    device.ipv4.ethernet)
            self._configure_ipv4(ixn_ethernet.Ipv4, device.ipv4)
        elif device.choice == 'ipv6':
            ixn_ethernet = self._configure_ethernet(ixn_device_group.Ethernet,
                                                    device.ipv6.ethernet)
            self._configure_ipv6(ixn_ethernet.Ipv6, device.ipv6)
        elif device.choice == 'bgpv4':
            ixn_ethernet = self._configure_ethernet(ixn_device_group.Ethernet,
                                                    device.bgpv4.ipv4.ethernet)
            ixn_ipv4 = self._configure_ipv4(ixn_ethernet.Ipv4,
                                            device.bgpv4.ipv4)
            self._configure_bgpv4(ixn_ipv4.BgpIpv4Peer, device.bgpv4)

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
            method = "Increment" if pattern.counter.up else "Decrement"
            getattr(ixn_obj, method)(
                start_value=pattern.counter.start,
                step_value=pattern.counter.step
            )
        elif pattern.choice == 'random':
            pass

    def _configure_ethernet(self, ixn_ethernet, ethernet):
        """Transform Device.Ethernet to /topology/.../ethernet
        """
        self._api._remove(ixn_ethernet, [ethernet])
        args = {
            'Name': ethernet.name,
        }
        ixn_ethernet.find(Name='^%s$' % ethernet.name)
        if len(ixn_ethernet) == 0:
            ixn_ethernet.add(**args)
        else:
            self._update(ixn_ethernet, **args)
        self._api.ixn_objects[ethernet.name] = ixn_ethernet.href
        self._configure_pattern(ixn_ethernet.Mac, ethernet.mac)
        self._configure_pattern(ixn_ethernet.Mtu, ethernet.mtu)
        if ethernet.vlans is not None:
            ixn_ethernet.VlanCount = len(ethernet.vlans)
            ixn_ethernet.EnableVlans.Single(ixn_ethernet.VlanCount > 0)
            self._configure_vlan(ixn_ethernet.Vlan, ethernet.vlans)
        return ixn_ethernet

    def _configure_vlan(self, ixn_vlans, vlans):
        """Transform Device.Vlan to /topology/.../vlan
        """
        for i in range(0, len(ixn_vlans.find())):
            args = {'Name': vlans[i].name}
            ixn_vlan = ixn_vlans[i]
            self._update(ixn_vlan, **args)
            self._api.ixn_objects[vlans[i].name] = ixn_vlan.href
            self._configure_pattern(ixn_vlan.VlanId, vlans[i].id)
            self._configure_pattern(ixn_vlan.Priority, vlans[i].priority)
            self._configure_pattern(ixn_vlan.Tpid,
                                    vlans[i].tpid,
                                    enum_map=Ngpf._TPID_MAP)

    def _configure_ipv4(self, ixn_ipv4, ipv4):
        """Transform Device.Ipv4 to /topology/.../ipv4
        """
        self._api._remove(ixn_ipv4, [ipv4])
        args = {
            'Name': ipv4.name,
        }
        ixn_ipv4.find(Name='^%s$' % ipv4.name)
        if len(ixn_ipv4) == 0:
            ixn_ipv4.add(**args)[-1]
        else:
            self._update(ixn_ipv4, **args)
        self._api.ixn_objects[ipv4.name] = ixn_ipv4.href
        self._configure_pattern(ixn_ipv4.Address, ipv4.address)
        self._configure_pattern(ixn_ipv4.GatewayIp, ipv4.gateway)
        self._configure_pattern(ixn_ipv4.Prefix, ipv4.prefix)
        return ixn_ipv4

    def _configure_ipv6(self, ixn_ipv6, ipv6):
        self._api._remove(ixn_ipv6, [ipv6])
        args = {
            'Name': ipv6.name,
        }
        ixn_ipv6.find(Name='^%s$' % ipv6.name)
        if len(ixn_ipv6) == 0:
            ixn_ipv6.add(**args)[-1]
        else:
            self.update(ixn_ipv6, **args)
        self._api.ixn_objects[ipv6.name] = ixn_ipv6.href
        self._configure_pattern(ixn_ipv6.Address, ipv6.address)
        self._configure_pattern(ixn_ipv6.GatewayIp, ipv6.gateway)
        self._configure_pattern(ixn_ipv6.Prefix, ipv6.prefix)
        return ipv6

    def _configure_bgpv4(self, ixn_bgpv4, bgpv4):
        self._api._remove(ixn_bgpv4, [bgpv4])
        args = {
            'Name': bgpv4.name,
        }
        ixn_bgpv4.find(Name='^%s$' % bgpv4.name)
        if len(ixn_bgpv4) == 0:
            ixn_bgpv4.add(**args)[-1]
        else:
            self._update(ixn_bgpv4, **args)
        self._api.ixn_objects[bgpv4.name] = ixn_bgpv4.href
