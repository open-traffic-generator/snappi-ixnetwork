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

    # Select type of Traffic
    _DEVICE_ENCAP_MAP = {
        'ethernet' : 'ethernetVlan',
        'ipv4' : 'ipv4',
        'ipv6' : 'ipv6',
        'bgpv4' : 'ipv4',
        'bgpv6': 'ipv6',
    }

    _BGP_AS_MODE = {
        'do_not_include_local_as' : 'dontincludelocalas',
        'include_as_seq' : 'includelocalasasasseq',
        'include_as_set' : 'includelocalasasasset',
        'include_as_confed_seq' : 'includelocalasasasseqconfederation',
        'include_as_confed_set' : 'includelocalasasassetconfederation',
        'prepend_to_first_segment' : 'prependlocalastofirstsegment'
    }
    
    _BGP_SEG_TYPE = {
        'as_seq': 'asseq',
        'as_set': 'asset',
        'as_confed_seq': 'asseqconfederation',
        'as_confed_set': 'assetconfederation'
    }
    
    _BGP_COMMUNITY_TYPE = {
        'manual_as_number': 'manual',
        'no_export': 'noexport',
        'no_advertised': 'noadvertised',
        'no_export_subconfed': 'noexport_subconfed',
        'llgr_stale': 'llgr_stale',
        'no_llgr': 'no_llgr'
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
            if device.container_name is None:
                raise NameError("container_name should not None")
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
            ixn_ng = ixn_device_group.NetworkGroup
            self._api._remove(ixn_ng, [])
            self._update(ixn_device_group, **args)
        
        self._config_proto_stack(ixn_device_group, device, ixn_device_group)
    
    def _config_proto_stack(self, ixn_obj, snappi_obj, ixn_dg):
        self._api.ixn_objects[snappi_obj.name] = ixn_obj.href
        properties = snappi_obj._properties
        for prop_name in properties:
            stack_class = getattr(self, '_configure_{0}'
                                  .format(prop_name), None)
            if stack_class is not None:
                child = properties[prop_name]
                if prop_name not in Ngpf._DEVICE_ENCAP_MAP:
                    raise Exception("Mapping is missing for {0}".format(
                            prop_name))
                self._api._device_encap[ixn_dg.Name] = Ngpf._DEVICE_ENCAP_MAP[
                            prop_name]
                if child.name is not None:
                    self._api._device_encap[child.name] = Ngpf._DEVICE_ENCAP_MAP[
                        prop_name]
                new_ixn_obj = stack_class(ixn_obj,
                                  child,
                                  ixn_dg)
                self._config_proto_stack(new_ixn_obj,
                                 child,
                                 ixn_dg)
            
    def _configure_pattern(self, ixn_obj, pattern, enum_map=None):
        if pattern is None or pattern.choice is None:
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

    def _casting_pattern_value(self, pattern, casting_type):
        """"""
        if pattern is None or pattern.choice is None:
            return
        custom_type = getattr(self, casting_type, None)
        if custom_type is None:
            raise Exception("Please defined this {0} method".format(
                casting_type))
        if pattern.choice == 'value':
            pattern.value = custom_type(pattern.value)
        elif pattern.choice == 'values':
            pattern.values = [custom_type(
                    val) for val in pattern.values]
        elif pattern.choice == 'increment':
            pattern.increment.start = custom_type(pattern.increment.start)
            pattern.increment.step = custom_type(pattern.increment.step)
        elif pattern.choice == 'decrement':
            pattern.decrement.start = custom_type(pattern.decrement.start)
            pattern.decrement.step = custom_type(pattern.decrement.step)
        return pattern
    
    def _ip_to_int(self, ip):
        """Convert IPv4 address to Int"""
        octet= list(map(int, ip.split('.')))
        result = (16777216 * octet[0]) + (65536 * octet[1]) \
                 + (256 * octet[2]) + octet[3]
        return result
    
    def _configure_ethernet(self, ixn_parent, ethernet, ixn_dg):
        """Transform Device.Ethernet to /topology/.../ethernet
        """
        ixn_ethernet = ixn_parent.Ethernet
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
        self._bgp_route_builder(ixn_dg, bgpv4)
        return ixn_bgpv4
    
    def _bgp_route_builder(self, ixn_dg, bgp):
        ixn_ng = ixn_dg.NetworkGroup
        bgpv4_route_ranges = bgp.bgpv4_route_ranges
        bgpv6_route_ranges = bgp.bgpv6_route_ranges
        if len(bgpv4_route_ranges) > 0:
            for route_range in bgpv4_route_ranges:
                self._configure_bgpv4_route(ixn_ng,
                                            route_range,
                                            ixn_dg)
        if len(bgpv6_route_ranges) > 0:
            for route_range in bgpv6_route_ranges:
                self._configure_bgpv6_route(ixn_ng,
                                            route_range,
                                            ixn_dg)

    def _configure_bgpv4_route(self, ixn_ng, route_range, ixn_dg):
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
            self._api._device_encap[route_range.name] = 'ipv4'
        ixn_ng.Multiplier = route_range.range_count
        ixn_pool.NumberOfAddresses = route_range.address_count
        self._configure_pattern(ixn_pool.NetworkAddress, route_range.address)
        self._configure_pattern(ixn_pool.PrefixLength, route_range.prefix)
        self._configure_pattern(ixn_pool.PrefixAddrStep, self._casting_pattern_value(
                route_range.address_step, '_ip_to_int'))
        if self._api.get_device_encap(ixn_dg.Name) == 'ipv4':
            ixn_bgp_property = ixn_pool.BgpIPRouteProperty.find()
        else:
            ixn_bgp_property = ixn_pool.BgpV6IPRouteProperty.find()
        self._configure_pattern(ixn_bgp_property.Ipv4NextHop, route_range.next_hop_address)
        self._config_bgp_as_path(route_range.as_path, ixn_bgp_property)
        self._config_bgp_community(route_range.community, ixn_bgp_property)

    def _configure_ipv6(self, ixn_parent, ipv6, ixn_dg):
        ixn_ipv6 = ixn_parent.Ipv6
        self._api._remove(ixn_ipv6, [ipv6])
        args = {}
        ixn_ipv6.find(Name='^%s$' % ipv6.name)
        if len(ixn_ipv6) == 0:
            ixn_ipv6.add(**args)[-1]
        else:
            self._update(ixn_ipv6, **args)
        if ipv6.name is not None:
            ixn_ipv6.Name = ipv6.name
            self._api.ixn_objects[ipv6.name] = ixn_ipv6.href
        self._configure_pattern(ixn_ipv6.Address, ipv6.address)
        self._configure_pattern(ixn_ipv6.GatewayIp, ipv6.gateway)
        self._configure_pattern(ixn_ipv6.Prefix, ipv6.prefix)
        return ixn_ipv6

    def _configure_bgpv6(self, ixn_parent, bgpv6, ixn_dg):
        ixn_bgpv6 = ixn_parent.BgpIpv6Peer
        self._api._remove(ixn_bgpv6, [bgpv6])
        args = {
            'Name': bgpv6.name,
        }
        ixn_bgpv6.find(Name='^%s$' % bgpv6.name)
        if len(ixn_bgpv6) == 0:
            ixn_bgpv6.add(**args)[-1]
        else:
            self._update(ixn_bgpv6, **args)
        self._api.ixn_objects[bgpv6.name] = ixn_bgpv6.href
        # self._configure_pattern(ixn_dg.RouterData.RouterId, bgpv4.router_id)
        as_type = 'internal'
        if bgpv6.as_type is not None and bgpv6.as_type \
                == 'ebgp':
            as_type = 'external'
        ixn_bgpv6.Type.Single(as_type)
        ixn_bgpv6.Enable4ByteAs.Single(True)
        self._configure_pattern(ixn_bgpv6.LocalAs4Bytes, bgpv6.as_number)
        self._configure_pattern(ixn_bgpv6.HoldTimer, bgpv6.hold_time_interval)
        self._configure_pattern(ixn_bgpv6.KeepaliveTimer, bgpv6.keep_alive_interval)
        self._configure_pattern(ixn_bgpv6.DutIp, bgpv6.dut_ipv6_address)
        # self._configure_pattern(ixn_bgpv4.DutIp, bgpv4.dut_as_number)
        self._bgp_route_builder(ixn_dg, bgpv6)
        return ixn_bgpv6

    def _configure_bgpv6_route(self, ixn_ng, route_range, ixn_dg):
        args = {
            'Name': route_range.name,
        }
        ixn_ng.find(Name='^%s$' % route_range.name)
        if len(ixn_ng) == 0:
            ixn_ng.add(**args)[-1]
            ixn_pool = ixn_ng.Ipv6PrefixPools.add()
        else:
            self._update(ixn_ng, **args)
            ixn_pool = ixn_ng.Ipv6PrefixPools.find()
        if route_range.name is not None:
            self._api.ixn_objects[route_range.name] = ixn_ng.href
            self._api._device_encap[route_range.name] = 'ipv6'
        ixn_ng.Multiplier = route_range.range_count
        ixn_pool.NumberOfAddresses = route_range.address_count
        self._configure_pattern(ixn_pool.NetworkAddress, route_range.address)
        self._configure_pattern(ixn_pool.PrefixLength, route_range.prefix)
        self._configure_pattern(ixn_pool.PrefixAddrStep, route_range.address_step)
        if self._api.get_device_encap(ixn_dg.Name) == 'ipv4':
            ixn_bgp_property = ixn_pool.BgpIPRouteProperty.find()
        else:
            ixn_bgp_property = ixn_pool.BgpV6IPRouteProperty.find()
        self._configure_pattern(ixn_bgp_property.Ipv6NextHop, route_range.next_hop_address)
        self._config_bgp_as_path(route_range.as_path, ixn_bgp_property)
        self._config_bgp_community(route_range.community, ixn_bgp_property)
    
    def _config_bgp_as_path(self, as_path, ixn_bgp_property):
        if as_path.as_set_mode is not None or len(
                as_path.as_path_segments) > 0:
            ixn_bgp_property.EnableAsPathSegments.Single(True)
            if as_path.as_set_mode is not None:
                ixn_bgp_property.AsSetMode.Single(Ngpf._BGP_AS_MODE[
                                                      as_path.as_set_mode])
            if len(as_path.as_path_segments) > 0:
                ixn_bgp_property.NoOfASPathSegmentsPerRouteRange = len(
                        as_path.as_path_segments)
                ixn_segments = ixn_bgp_property.BgpAsPathSegmentList.find()
                for seg_index, segment in enumerate(as_path.as_path_segments):
                    ixn_segment = ixn_segments[seg_index]
                    ixn_segment.SegmentType.Single(Ngpf._BGP_SEG_TYPE[
                                                       segment.segment_type])
                    if segment.as_numbers is not None:
                        ixn_segment.NumberOfAsNumberInSegment = len(segment.as_numbers)
                        ixn_as_numbers = ixn_segment.BgpAsNumberList.find()
                        for as_index, as_number in enumerate(segment.as_numbers):
                            ixn_as_number = ixn_as_numbers[as_index]
                            ixn_as_number.AsNumber.Single(as_number)

    def _config_bgp_community(self, communities, ixn_bgp_property):
        if len(communities) == 0:
            return
        ixn_bgp_property.EnableCommunity.Single(True)
        ixn_bgp_property.NoOfCommunities = len(communities)
        ixn_communities = ixn_bgp_property.BgpCommunitiesList.find()
        for index, community in enumerate(communities):
            ixn_community = ixn_communities[index]
            if community.community_type is not None:
                ixn_community.Type.Single(Ngpf._BGP_COMMUNITY_TYPE[
                                              community.community_type])
            self._configure_pattern(ixn_community.AsNumber, community.as_number)
            self._configure_pattern(ixn_community.LastTwoOctets, community.as_custom)
