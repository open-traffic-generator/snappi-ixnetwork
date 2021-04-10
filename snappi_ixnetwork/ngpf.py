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

    _BGP_AS_SET_MODE = {
        'do_not_include_as': 'dontincludelocalas',
        'include_as_seq': 'includelocalasasasseq',
        'include_as_set': 'includelocalasasasset',
        'include_as_seq_confed': 'includelocalasasasseqconfederation',
        'include_as_set_confed': 'includelocalasasassetconfederation',
        'prepend_as_to_first_segment': 'prependlocalastofirstsegment'
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
            name = self._api._get_topology_name(device.container_name)
            ixn_topology.find(
                Name='^%s$' % self._api.special_char(name))
            if len(ixn_topology) > 0:
                self._api._remove(ixn_topology.DeviceGroup, [device])
        for device in devices:
            args = {
                'Name': self._api._get_topology_name(device.container_name),
                'Ports': [self._api.ixn_objects[device.container_name]]
            }
            ixn_topology.find(Name='^%s$' % self._api.special_char(
                                        args['Name']))
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
        args = {'Name': device.name, 'Multiplier': 1}
        ixn_device_group.find(Name='^%s$' % self._api.special_char(
                                        device.name))
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
        if pattern is None:
            return
        # Asymmetric support- without pattern
        if getattr(pattern, 'choice', None) is None:
            if enum_map is not None:
                ixn_obj.Single(enum_map[pattern])
            elif isinstance(pattern, list):
                ixn_obj.ValueList(pattern)
            else:
                ixn_obj.Single(pattern)
        # Symmetric support with pattern
        else:
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
        self._api._remove(ixn_ethernet, [ethernet])
        args = {}
        ixn_ethernet.find(Name='^%s$' % self._api.special_char(
                                ethernet.name))
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
        ixn_ipv4.find(Name='^%s$' % self._api.special_char(ipv4.name))
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
        ixn_bgpv4.find(Name='^%s$' % self._api.special_char(bgpv4.name))
        if len(ixn_bgpv4) == 0:
            ixn_bgpv4.add(**args)[-1]
        else:
            self._update(ixn_bgpv4, **args)
        self._api.ixn_objects[bgpv4.name] = ixn_bgpv4.href
        as_type = 'internal'
        if bgpv4.as_type is not None and bgpv4.as_type \
                    == 'ebgp':
            as_type = 'external'
        ixn_bgpv4.Type.Single(as_type)
        as_bytes = bgpv4.as_number_width
        if as_bytes is None or as_bytes == 'two':
            self._configure_pattern(ixn_bgpv4.LocalAs2Bytes, bgpv4.as_number)
        elif as_bytes == 'four':
            ixn_bgpv4.Enable4ByteAs.Single(True)
            self._configure_pattern(ixn_bgpv4.LocalAs4Bytes, bgpv4.as_number)
        else:
            raise Exception("Please configure supported [two, four] as_number_width")
        self._configure_pattern(ixn_bgpv4.DutIp, bgpv4.dut_address)
        self._configure_pattern(ixn_bgpv4.AsSetMode, bgpv4.as_number_set_mode, enum_map=
                                Ngpf._BGP_AS_SET_MODE)
        # self._configure_pattern(ixn_dg.RouterData.RouterId, bgpv4.router_id)
        advanced = bgpv4.advanced
        self._configure_pattern(ixn_bgpv4.HoldTimer, advanced.hold_time_interval)
        self._configure_pattern(ixn_bgpv4.KeepaliveTimer, advanced.keep_alive_interval)
        self._configure_pattern(ixn_bgpv4.Md5Key, advanced.md5_key)
        self._configure_pattern(ixn_bgpv4.UpdateInterval, advanced.update_interval)
        self._configure_pattern(ixn_bgpv4.Ttl, advanced.time_to_live)
        self._bgp_route_builder(ixn_dg, ixn_bgpv4, bgpv4)
        return ixn_bgpv4
    
    def _bgp_route_builder(self, ixn_dg, ixn_bgp, bgp):
        bgpv4_routes = bgp.bgpv4_routes
        bgpv6_routes = bgp.bgpv6_routes
        if len(bgpv4_routes) > 0:
            for route_range in bgpv4_routes:
                self._configure_bgpv4_route(ixn_dg,
                                            ixn_bgp,
                                            route_range)
        if len(bgpv6_routes) > 0:
            for route_range in bgpv6_routes:
                self._configure_bgpv6_route(ixn_dg,
                                            ixn_bgp,
                                            route_range)

    def _configure_bgpv4_route(self, ixn_dg, ixn_bgp, route_range):
        ixn_ng = ixn_dg.NetworkGroup
        args = {
            'Name': route_range.name,
        }
        ixn_ng.find(Name='^%s$' % self._api.special_char(route_range.name))
        if len(ixn_ng) == 0:
            self.stop_topology()
            ixn_ng.add(**args)[-1]
            ixn_pool = ixn_ng.Ipv4PrefixPools.add()
        else:
            self._update(ixn_ng, **args)
            ixn_pool = ixn_ng.Ipv4PrefixPools.find()
        ixn_pool.Connector.find().ConnectedTo = ixn_bgp.href
        if route_range.name is not None:
            self._api.ixn_objects[route_range.name] = ixn_ng.href
            self._api._device_encap[route_range.name] = 'ipv4'
        addresses = route_range.addresses
        if len(addresses) > 0:
            ixn_ng.Multiplier = len(addresses)
            route_addresses = RouteAddresses()
            for address in addresses:
                route_addresses.address = address.address
                route_addresses.step = address.step
                route_addresses.prefix = address.prefix
                route_addresses.count = address.count
            self._configure_pattern(ixn_pool.NetworkAddress, route_addresses.address)
            self._configure_pattern(ixn_pool.PrefixAddrStep, route_addresses.step)
            self._configure_pattern(ixn_pool.PrefixLength, route_addresses.prefix)
            self._configure_pattern(ixn_pool.NumberOfAddressesAsy, route_addresses.count)
        if self._api.get_device_encap(ixn_dg.Name) == 'ipv4':
            ixn_bgp_property = ixn_pool.BgpIPRouteProperty.find()
        else:
            ixn_bgp_property = ixn_pool.BgpV6IPRouteProperty.find()
        self._configure_pattern(ixn_bgp_property.Ipv4NextHop, route_range.next_hop_address)
        advanced = route_range.advanced
        if advanced.multi_exit_discriminator is not None:
            ixn_bgp_property.EnableMultiExitDiscriminator.Single(True)
            self._configure_pattern(ixn_bgp_property.MultiExitDiscriminator,
                                    advanced.multi_exit_discriminator)
        self._configure_pattern(ixn_bgp_property.Origin, advanced.origin)
        self._config_bgp_as_path(route_range.as_path, ixn_bgp_property)
        self._config_bgp_community(route_range.communities, ixn_bgp_property)

    def _configure_ipv6(self, ixn_parent, ipv6, ixn_dg):
        ixn_ipv6 = ixn_parent.Ipv6
        self._api._remove(ixn_ipv6, [ipv6])
        args = {}
        ixn_ipv6.find(Name='^%s$' % self._api.special_char(ipv6.name))
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
        ixn_bgpv6.find(Name='^%s$' % self._api.special_char(bgpv6.name))
        if len(ixn_bgpv6) == 0:
            ixn_bgpv6.add(**args)[-1]
        else:
            self._update(ixn_bgpv6, **args)
        self._api.ixn_objects[bgpv6.name] = ixn_bgpv6.href
        as_type = 'internal'
        if bgpv6.as_type is not None and bgpv6.as_type \
                == 'ebgp':
            as_type = 'external'
        ixn_bgpv6.Type.Single(as_type)
        as_bytes = bgpv6.as_number_width
        if as_bytes is None or as_bytes == 'two':
            self._configure_pattern(ixn_bgpv6.LocalAs2Bytes, bgpv6.as_number)
        elif as_bytes == 'four':
            ixn_bgpv6.Enable4ByteAs.Single(True)
            self._configure_pattern(ixn_bgpv6.LocalAs4Bytes, bgpv6.as_number)
        else:
            raise Exception("Please configure supported [two, four] as_number_width")
        self._configure_pattern(ixn_bgpv6.DutIp, bgpv6.dut_address)
        self._configure_pattern(ixn_bgpv6.AsSetMode, bgpv6.as_number_set_mode, enum_map=
                                Ngpf._BGP_AS_SET_MODE)
        # self._configure_pattern(ixn_dg.RouterData.RouterId, bgpv4.router_id)
        advanced = bgpv6.advanced
        self._configure_pattern(ixn_bgpv6.HoldTimer, advanced.hold_time_interval)
        self._configure_pattern(ixn_bgpv6.KeepaliveTimer, advanced.keep_alive_interval)
        self._configure_pattern(ixn_bgpv6.Md5Key, advanced.md5_key)
        self._configure_pattern(ixn_bgpv6.UpdateInterval, advanced.update_interval)
        self._configure_pattern(ixn_bgpv6.Ttl, advanced.time_to_live)
        self._bgp_route_builder(ixn_dg, ixn_bgpv6, bgpv6)
        return ixn_bgpv6

    def _configure_bgpv6_route(self, ixn_dg, ixn_bgp, route_range):
        ixn_ng = ixn_dg.NetworkGroup
        args = {
            'Name': route_range.name,
        }
        ixn_ng.find(Name='^%s$' % self._api.special_char(
                                route_range.name))
        if len(ixn_ng) == 0:
            self.stop_topology()
            ixn_ng.add(**args)[-1]
            ixn_pool = ixn_ng.Ipv6PrefixPools.add()
        else:
            self._update(ixn_ng, **args)
            ixn_pool = ixn_ng.Ipv6PrefixPools.find()
        ixn_pool.Connector.find().ConnectedTo = ixn_bgp.href
        if route_range.name is not None:
            self._api.ixn_objects[route_range.name] = ixn_ng.href
            self._api._device_encap[route_range.name] = 'ipv6'
        addresses = route_range.addresses
        if len(addresses) > 0:
            ixn_ng.Multiplier = len(addresses)
            route_addresses = RouteAddresses()
            for address in addresses:
                route_addresses.address = address.address
                route_addresses.step = address.step
                route_addresses.prefix = address.prefix
                route_addresses.count = address.count
            self._configure_pattern(ixn_pool.NetworkAddress, route_addresses.address)
            self._configure_pattern(ixn_pool.PrefixAddrStep, route_addresses.step)
            self._configure_pattern(ixn_pool.PrefixLength, route_addresses.prefix)
            self._configure_pattern(ixn_pool.NumberOfAddressesAsy, route_addresses.count)
        if self._api.get_device_encap(ixn_dg.Name) == 'ipv4':
            ixn_bgp_property = ixn_pool.BgpIPRouteProperty.find()
        else:
            ixn_bgp_property = ixn_pool.BgpV6IPRouteProperty.find()
        self._configure_pattern(ixn_bgp_property.Ipv6NextHop, route_range.next_hop_address)
        advanced = route_range.advanced
        if advanced.multi_exit_discriminator is not None:
            ixn_bgp_property.EnableMultiExitDiscriminator.Single(True)
            self._configure_pattern(ixn_bgp_property.MultiExitDiscriminator,
                                    advanced.multi_exit_discriminator)
        self._configure_pattern(ixn_bgp_property.Origin, advanced.origin)
        self._config_bgp_as_path(route_range.as_path, ixn_bgp_property)
        self._config_bgp_community(route_range.communities, ixn_bgp_property)
    
    def _config_bgp_as_path(self, as_path, ixn_bgp_property):
        as_path_segments = as_path.as_path_segments
        if as_path.as_set_mode is not None or len(
                as_path_segments) > 0:
            ixn_bgp_property.EnableAsPathSegments.Single(True)
            self._configure_pattern(ixn_bgp_property.AsSetMode,
                                    as_path.as_set_mode, Ngpf._BGP_AS_MODE)
            self._configure_pattern(ixn_bgp_property.OverridePeerAsSetMode,
                                    as_path.override_peer_as_set_mode)
            if len(as_path_segments) > 0:
                ixn_bgp_property.NoOfASPathSegmentsPerRouteRange = len(
                        as_path_segments)
                ixn_segments = ixn_bgp_property.BgpAsPathSegmentList.find()
                for seg_index, segment in enumerate(as_path_segments):
                    ixn_segment = ixn_segments[seg_index]
                    ixn_segment.SegmentType.Single(Ngpf._BGP_SEG_TYPE[
                                                       segment.segment_type])
                    as_numbers = segment.as_numbers
                    if as_numbers is not None:
                        ixn_segment.NumberOfAsNumberInSegment = len(as_numbers)
                        ixn_as_numbers = ixn_segment.BgpAsNumberList.find()
                        for as_index, as_number in enumerate(as_numbers):
                            ixn_as_number = ixn_as_numbers[as_index]
                            ixn_as_number.AsNumber.Single(as_number)

    def _config_bgp_community(self, communities, ixn_bgp_property):
        if len(communities) == 0:
            ixn_bgp_property.EnableCommunity.Single(False)
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

    def stop_topology(self):
        glob_topo = self._api._globals.Topology.refresh()
        if glob_topo.Status == 'started':
            self._api._ixnetwork.StopAllProtocols('sync')

class RouteAddresses(object):
    def __init__(self):
        self._address = []
        self._count = []
        self._prefix = []
        self._step = []
    
    @property
    def address(self):
        return self._address
    
    @address.setter
    def address(self, value):
        self._address.append(value)
    
    @property
    def count(self):
        return self._count
    
    @count.setter
    def count(self, value):
        self._count.append(value)
    
    @property
    def prefix(self):
        return self._prefix
    
    @prefix.setter
    def prefix(self, value):
        self._prefix.append(value)
    
    @property
    def step(self):
        return self._step
    
    @step.setter
    def step(self, value):
        self._step.append(value)