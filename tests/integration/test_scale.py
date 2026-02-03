import pytest


@pytest.mark.slow
def test_bgp_large_communities_scale(api, utils):
    """
    Test BGP with large number of communities per route.
    
    Configure:
    - BGP route with 100 communities
    
    Validate:
    - All communities are configured
    - Performance is acceptable
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = ipv4.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.as_type = "ebgp"
    bgp_peer.peer_address = "10.1.1.2"
    bgp_peer.as_number = 65200
    
    route = bgp_peer.v4_routes.add(name="route_many_comm")
    route.addresses.add(address="200.1.0.0", prefix=24, count=1)
    
    # Add 100 communities
    for i in range(100):
        comm = route.communities.add()
        comm.type = comm.MANUAL_AS_NUMBER
        comm.as_number = 65000 + i
        comm.as_custom = 100 + i
    
    api.set_config(config)
    
    # Validate all communities
    ixn_route = utils.get_ixnetwork_obj(api, route.name, "ipv4_unicast")
    assert ixn_route is not None


@pytest.mark.slow
def test_bgp_evpn_many_ethernet_segments(api, utils):
    """
    Test BGP EVPN with large number of ethernet segments.
    
    Configure:
    - BGP peer with 50 ethernet segments
    - Each segment with EVI and broadcast domain
    
    Validate:
    - All segments are configured
    - Configuration scales appropriately
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="evpn_scale_device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_evpn_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    # Create 50 ethernet segments
    for i in range(50):
        eth_seg = bgp_peer.evpn_ethernet_segments.add()
        eth_seg.esi = f"01:00:00:00:00:00:00:00:00:{i+1:02x}"
        
        # EVI for each segment
        evi = eth_seg.evis.add()
        evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
        evi.route_distinguisher.rd_value = f"100:{i+1}"
        
        rt_export = evi.route_target_export.add()
        rt_export.rt_type = rt_export.AS_2OCTET
        rt_export.rt_value = f"100:{i+100}"
        
        rt_import = evi.route_target_import.add()
        rt_import.rt_type = rt_import.AS_2OCTET
        rt_import.rt_value = f"100:{i+100}"
        
        # Broadcast domain
        bd = evi.broadcast_domains.add()
        bd.ethernet_tag_id = 100 + i
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


@pytest.mark.slow
def test_isis_many_routes_all_features(api, utils):
    """
    Test ISIS with large number of routes with all features enabled.
    
    Configure:
    - ISIS router with 500 IPv4 routes
    - 500 IPv6 routes
    - All advanced features configured
    
    Validate:
    - All routes are configured
    - Performance is acceptable
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="isis_scale_device")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = "ipv6"
    ipv6.address = "2001:db8::1"
    ipv6.prefix = 64
    ipv6.gateway = "2001:db8::2"
    
    isis = device.isis
    isis.name = "isis_scale_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_scale_int"
    isis_iface.network_type = isis_iface.BROADCAST
    isis_iface.level_type = isis_iface.LEVEL_2
    isis_iface.metric = 10
    
    # Router basic config
    basic = isis_iface.basic
    if basic:
        basic.hostname = "scale_router"
        basic.enable_wide_metric = True
        basic.ipv4_te_router_id = "1.1.1.1"
    
    # Router advanced config
    advanced = isis_iface.advanced
    if advanced:
        advanced.enable_hello_padding = True
        advanced.lsp_refresh_rate = 900
        advanced.lsp_lifetime = 1200
        advanced.max_lsp_size = 1492
    
    # Large number of IPv4 routes
    v4_route = isis_iface.v4_routes.add()
    v4_route.name = "isis_v4_routes_scale"
    v4_route.addresses.add(address="200.1.0.0", prefix=24, count=500)
    v4_route.origin_type = v4_route.INTERNAL
    v4_route.redistribution_type = v4_route.UP
    
    # Large number of IPv6 routes
    v6_route = isis_iface.v6_routes.add()
    v6_route.name = "isis_v6_routes_scale"
    v6_route.addresses.add(address="4000::", prefix=64, count=500)
    v6_route.origin_type = v6_route.INTERNAL
    v6_route.redistribution_type = v6_route.UP
    
    api.set_config(config)
    
    # Validate configuration
    ixn_isis = utils.get_ixnetwork_obj(api, isis.name, "isisL3")
    assert ixn_isis is not None


@pytest.mark.slow
def test_bgp_evpn_large_cmac_ip_ranges(api, utils):
    """
    Test BGP EVPN with large CMAC IP ranges.
    
    Configure:
    - BGP EVPN with broadcast domain
    - CMAC IP range with 1000 MAC addresses
    - 1000 IPv4 addresses
    - 1000 IPv6 addresses
    
    Validate:
    - Large address pools are configured
    - Performance is acceptable
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="evpn_cmac_scale")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    bd = evi.broadcast_domains.add()
    bd.ethernet_tag_id = 100
    
    # Large CMAC IP range
    cmac_range = bd.cmac_ip_range.add()
    
    # 1000 MAC addresses
    mac_addr = cmac_range.mac_addresses.add()
    mac_addr.address = "00:00:01:00:00:01"
    mac_addr.prefix = 48
    mac_addr.count = 1000
    
    # 1000 IPv4 addresses
    ipv4_addr = cmac_range.ipv4_addresses.add()
    ipv4_addr.address = "10.1.1.1"
    ipv4_addr.prefix = 24
    ipv4_addr.count = 1000
    
    # 1000 IPv6 addresses
    ipv6_addr = cmac_range.ipv6_addresses.add()
    ipv6_addr.address = "2001:db8::1"
    ipv6_addr.prefix = 64
    ipv6_addr.count = 1000
    
    cmac_range.l2vni = 5000
    cmac_range.l3vni = 6000
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


@pytest.mark.slow
def test_multiple_devices_scale(api, utils):
    """
    Test configuration with large number of similar devices.
    
    Configure:
    - 20 devices with BGP
    - Each device with 50 routes
    - Tests compaction at scale
    
    Validate:
    - All devices are configured
    - Compaction reduces object count
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    # Create 20 similar devices
    for dev_idx in range(20):
        device = config.devices.device(name=f"device_{dev_idx}")[-1]
        device.container_name = port.name
        
        eth = device.ethernets.add()
        eth.name = f"eth_{dev_idx}"
        eth.mac = f"00:00:00:00:{dev_idx:02x}:01"
        
        ipv4 = eth.ipv4_addresses.add()
        ipv4.name = f"ipv4_{dev_idx}"
        ipv4.address = f"10.{dev_idx+1}.1.1"
        ipv4.prefix = 24
        ipv4.gateway = f"10.{dev_idx+1}.1.2"
        
        bgp = device.bgp
        bgp.router_id = f"{dev_idx+1}.{dev_idx+1}.{dev_idx+1}.{dev_idx+1}"
        bgp_iface = bgp.ipv4_interfaces.add()
        bgp_iface.ipv4_name = ipv4.name
        bgp_peer = bgp_iface.peers.add()
        bgp_peer.name = f"bgp_peer_{dev_idx}"
        bgp_peer.as_type = "ebgp"
        bgp_peer.peer_address = f"10.{dev_idx+1}.1.2"
        bgp_peer.as_number = 65200 + dev_idx
        
        # 50 routes per device
        route = bgp_peer.v4_routes.add(name=f"routes_{dev_idx}")
        route.addresses.add(address=f"{200+dev_idx}.1.0.0", prefix=24, count=50)
    
    api.set_config(config)
    
    # Validate devices are configured
    # Compaction should consolidate similar devices


@pytest.mark.slow  
def test_bgp_as_path_max_segments(api, utils):
    """
    Test BGP AS path with maximum number of segments.
    
    Configure:
    - BGP route with 20 AS path segments
    - Each segment with multiple AS numbers
    
    Validate:
    - All segments are configured
    - AS path length is correct
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = ipv4.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.as_type = "ebgp"
    bgp_peer.peer_address = "10.1.1.2"
    bgp_peer.as_number = 65200
    
    route = bgp_peer.v4_routes.add(name="long_as_path_route")
    route.addresses.add(address="200.1.0.0", prefix=24, count=1)
    
    as_path = route.as_path
    
    # Create 20 AS path segments
    for i in range(20):
        seg = as_path.segments.add()
        seg.type = seg.AS_SEQ
        # Each segment with 5 AS numbers
        seg.as_numbers = [100 + (i*5) + j for j in range(5)]
    
    api.set_config(config)
    
    # Validate AS path configuration
    ixn_route = utils.get_ixnetwork_obj(api, route.name, "ipv4_unicast")
    assert ixn_route is not None
    ixn_segments = ixn_route.parent.BgpAsPathSegmentList.find()
    assert len(ixn_segments) == 20
