import json


class Ngpf(object):
    """Ngpf configuration

    Args
    ----
    - ixnetworkapi (Api): instance of the ixnetworkapi class
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
        self._configure_topology(self._api._topology, self._api.snappi_config.devices)

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
        devices = devices._items
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
        self._config_proto_stack(ixn_device_group, device, ixn_device_group)
    
    def _config_proto_stack(self, ixn_obj, snappi_obj, ixn_dg):
        self._api.ixn_objects[snappi_obj.name] = ixn_obj.href
        for prop_name in snappi_obj._properties:
            stack_class = getattr(self, '_configure_{0}'
                                  .format(prop_name), None)
            if stack_class is not None:
                new_ixn_obj = stack_class(ixn_obj,
                                  snappi_obj._properties[prop_name],
                                  ixn_dg)
                self._config_proto_stack(new_ixn_obj,
                                 snappi_obj._properties[prop_name],
                                 ixn_dg)
            
    def _configure_pattern(self, ixn_obj, pattern, enum_map=None):
        if pattern.choice is None:
            return
        elif enum_map is not None and pattern.choice == 'value':
            ixn_obj.Single(enum_map[pattern.value])
        elif pattern.choice == 'value':
            ixn_obj.Single(pattern.value)
        elif pattern.choice == 'values':
            ixn_obj.ValueList(pattern.values)
        elif pattern.choice == 'increment':
            ixn_obj.Increment(pattern.increment.start,
                              pattern.increment.step)
        elif pattern.choice == 'decrement':
            ixn_obj.Decrement(pattern.decrement.start,
                              pattern.decrement.step)
        elif pattern.choice == 'random':
            pass

    def _configure_ethernet(self, ixn_parent, ethernet, ixn_dg):
        """Transform Device.Ethernet to /topology/.../ethernet
        """
        ixn_ethernet = ixn_parent.Ethernet
        self._api._device_encap[ixn_dg.Name] = 'ethernetVlan'
        self._api._remove(ixn_ethernet, [ethernet])
        args = {}
        ixn_ethernet.find(Name='^%s$' % ethernet.name)
        if len(ixn_ethernet) == 0:
            ixn_ethernet.add(**args)
        else:
            self._update(ixn_ethernet, **args)
        if ethernet.name is not None:
            self._api.ixn_objects[ethernet.name] = ixn_ethernet.href
            ixn_ethernet.Name = ethernet.name
        self._configure_pattern(ixn_ethernet.Mac, ethernet.mac)
        self._configure_pattern(ixn_ethernet.Mtu, ethernet.mtu)
        if len(ethernet.vlans) > 0:
            ixn_ethernet.VlanCount = len(ethernet.vlans)
            ixn_ethernet.EnableVlans.Single(ixn_ethernet.VlanCount > 0)
            self._configure_vlan(ixn_ethernet.Vlan, ethernet.vlans)
        return ixn_ethernet

    def _configure_vlan(self, ixn_vlans, vlans):
        """Transform Device.Vlan to /topology/.../vlan
        """
        for i in range(0, len(ixn_vlans.find())):
            ixn_vlan = ixn_vlans[i]
            if vlans[i].name is not None:
                args = {'Name': vlans[i].name}
                self._update(ixn_vlan, **args)
                self._api.ixn_objects[vlans[i].name] = ixn_vlan.href
            self._configure_pattern(ixn_vlan.VlanId, vlans[i].id)
            self._configure_pattern(ixn_vlan.Priority, vlans[i].priority)
            self._configure_pattern(ixn_vlan.Tpid,
                                    vlans[i].tpid,
                                    enum_map=Ngpf._TPID_MAP)

    def _configure_ipv4(self, ixn_parent, ipv4, ixn_dg):
        """Transform Device.Ipv4 to /topology/.../ipv4
        """
        ixn_ipv4 = ixn_parent.Ipv4
        self._api._device_encap[ixn_dg.Name] = 'ipv4'
        self._api._remove(ixn_ipv4, [ipv4])
        args = {}
        ixn_ipv4.find(Name='^%s$' % ipv4.name)
        if len(ixn_ipv4) == 0:
            ixn_ipv4.add(**args)[-1]
        else:
            self._update(ixn_ipv4, **args)
        if ipv4.name is not None:
            ixn_ipv4.Name = ipv4.name
            self._api.ixn_objects[ipv4.name] = ixn_ipv4.href
        self._configure_pattern(ixn_ipv4.Address, ipv4.address)
        self._configure_pattern(ixn_ipv4.GatewayIp, ipv4.gateway)
        self._configure_pattern(ixn_ipv4.Prefix, ipv4.prefix)
        return ixn_ipv4
    
    def _configure_ipv6(self, ixn_parent, ipv6, ixn_dg):
        ixn_ipv6 = ixn_parent.Ipv6
        self._api._device_encap[ixn_dg.Name] = 'ipv6'
        self._api._remove(ixn_ipv6, [ipv6])
        args = {}
        ixn_ipv6.find(Name='^%s$' % ipv6.name)
        if len(ixn_ipv6) == 0:
            ixn_ipv6.add(**args)[-1]
        else:
            self.update(ixn_ipv6, **args)
        if ipv6.name is not None:
            ixn_ipv6.Name = ipv6.name
            self._api.ixn_objects[ipv6.name] = ixn_ipv6.href
        self._configure_pattern(ixn_ipv6.Address, ipv6.address)
        self._configure_pattern(ixn_ipv6.GatewayIp, ipv6.gateway)
        self._configure_pattern(ixn_ipv6.Prefix, ipv6.prefix)
        return ixn_ipv6

    def _configure_bgpv4(self, ixn_parent, bgpv4, ixn_dg):
        ixn_bgpv4 = ixn_parent.BgpIpv4Peer
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
        # self._configure_pattern(ixn_dg.RouterData.RouterId, bgpv4.router_id)
        as_type = 'internal'
        if bgpv4.as_type is not None and bgpv4.as_type \
                    == 'ebgp':
            as_type = 'external'
        ixn_bgpv4.Type.Single(as_type)
        ixn_bgpv4.Enable4ByteAs.Single(True)
        self._configure_pattern(ixn_bgpv4.LocalAs4Bytes, bgpv4.as_number)
        self._configure_pattern(ixn_bgpv4.HoldTimer, bgpv4.hold_time_interval)
        self._configure_pattern(ixn_bgpv4.KeepaliveTimer, bgpv4.keep_alive_interval)
        self._configure_pattern(ixn_bgpv4.DutIp, bgpv4.dut_ipv4_address)
        # self._configure_pattern(ixn_bgpv4.DutIp, bgpv4.dut_as_number)
        
        if len(bgpv4.bgpv4_route_ranges) > 0:
            for route_range in bgpv4.bgpv4_route_ranges:
                self._configure_bgpv4_route(ixn_dg.NetworkGroup, route_range)
                
        return ixn_bgpv4

    def _configure_bgpv4_route(self, ixn_ng, route_range):
        args = {
            'Name': route_range.name,
        }
        ixn_ng.find(Name='^%s$' % route_range.name)
        if len(ixn_ng) == 0:
            ixn_ng.add(**args)[-1]
            ixn_pool = ixn_ng.Ipv4PrefixPools.add()
        else:
            self._update(ixn_ng, **args)
            ixn_pool = ixn_ng.Ipv4PrefixPools.find()
        if route_range.name is not None:
            self._api.ixn_objects[route_range.name] = ixn_ng.href
        ixn_ng.Multiplier = route_range.range_count
        ixn_pool.NumberOfAddresses = route_range.address_count
        self._configure_pattern(ixn_pool.NetworkAddress, route_range.address)
        self._configure_pattern(ixn_pool.PrefixLength, route_range.prefix)
        self._configure_pattern(ixn_pool.PrefixAddrStep, route_range.address_step)
        bgp_property = ixn_pool.BgpIPRouteProperty.find()
        # if route_range.as_path.choice is not None:
        #     bgp_property.EnableAsPathSegments.Single(True)
        #     self._configure_pattern(bgp_property.BgpAsPathSegmentList.find().BgpAsNumberList.find().AsNumber,
        #                             route_range.as_path)
        self._configure_pattern(bgp_property.Ipv4NextHop, route_range.next_hop_address)
        