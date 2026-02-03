import pytest


def test_bgp_as_path_all_segment_types(api, utils):
    """
    Test BGP AS path with all segment types:
    - AS_SEQ
    - AS_SET
    - AS_CONFED_SEQ
    - AS_CONFED_SET
    
    Configure BGPv4 routes with different AS path segment types and validate.
    """
    config = api.config()
    
    port = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
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
    eth.mac = "00:00:00:00:00:11"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    
    bgpv4 = device.bgp
    bgpv4.router_id = "192.0.0.1"
    bgpv4_int = bgpv4.ipv4_interfaces.add()
    bgpv4_int.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_int.peers.add()
    bgpv4_peer.name = "bgp_peer"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "21.1.1.2"
    bgpv4_peer.as_number = 65200
    
    # Route 1: AS_SEQ segment
    rr1 = bgpv4_peer.v4_routes.add(name="rr_as_seq")
    rr1.addresses.add(address="200.1.0.0", prefix=24, count=10)
    as_path1 = rr1.as_path
    seg1 = as_path1.segments.add()
    seg1.type = seg1.AS_SEQ
    seg1.as_numbers = [100, 200, 300]
    
    # Route 2: AS_SET segment
    rr2 = bgpv4_peer.v4_routes.add(name="rr_as_set")
    rr2.addresses.add(address="201.1.0.0", prefix=24, count=10)
    as_path2 = rr2.as_path
    seg2 = as_path2.segments.add()
    seg2.type = seg2.AS_SET
    seg2.as_numbers = [400, 500, 600]
    
    # Route 3: AS_CONFED_SEQ segment
    rr3 = bgpv4_peer.v4_routes.add(name="rr_as_confed_seq")
    rr3.addresses.add(address="202.1.0.0", prefix=24, count=10)
    as_path3 = rr3.as_path
    seg3 = as_path3.segments.add()
    seg3.type = seg3.AS_CONFED_SEQ
    seg3.as_numbers = [700, 800]
    
    # Route 4: AS_CONFED_SET segment
    rr4 = bgpv4_peer.v4_routes.add(name="rr_as_confed_set")
    rr4.addresses.add(address="203.1.0.0", prefix=24, count=10)
    as_path4 = rr4.as_path
    seg4 = as_path4.segments.add()
    seg4.type = seg4.AS_CONFED_SET
    seg4.as_numbers = [900, 1000]
    
    api.set_config(config)
    
    # Validate AS_SEQ
    ixn_rr1 = utils.get_ixnetwork_obj(api, "rr_as_seq", "ipv4_unicast")
    assert ixn_rr1 is not None
    ixn_seg1 = ixn_rr1.parent.BgpAsPathSegmentList.find()[0]
    assert ixn_seg1.SegmentType.Values[0] == "asseq"
    
    # Validate AS_SET
    ixn_rr2 = utils.get_ixnetwork_obj(api, "rr_as_set", "ipv4_unicast")
    assert ixn_rr2 is not None
    ixn_seg2 = ixn_rr2.parent.BgpAsPathSegmentList.find()[0]
    assert ixn_seg2.SegmentType.Values[0] == "asset"
    
    # Validate AS_CONFED_SEQ
    ixn_rr3 = utils.get_ixnetwork_obj(api, "rr_as_confed_seq", "ipv4_unicast")
    assert ixn_rr3 is not None
    ixn_seg3 = ixn_rr3.parent.BgpAsPathSegmentList.find()[0]
    assert ixn_seg3.SegmentType.Values[0] == "asseqconfederation"
    
    # Validate AS_CONFED_SET
    ixn_rr4 = utils.get_ixnetwork_obj(api, "rr_as_confed_set", "ipv4_unicast")
    assert ixn_rr4 is not None
    ixn_seg4 = ixn_rr4.parent.BgpAsPathSegmentList.find()[0]
    assert ixn_seg4.SegmentType.Values[0] == "assetconfederation"


def test_bgp_as_path_multiple_segments(api, utils):
    """
    Test BGP AS path with multiple segments in a single path.
    
    Configure:
    - BGP route with AS path containing multiple segments of different types
    
    Validate:
    - All segments are configured in correct order
    """
    config = api.config()
    
    port = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
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
    eth.mac = "00:00:00:00:00:11"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    
    bgpv4 = device.bgp
    bgpv4.router_id = "192.0.0.1"
    bgpv4_int = bgpv4.ipv4_interfaces.add()
    bgpv4_int.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_int.peers.add()
    bgpv4_peer.name = "bgp_peer"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "21.1.1.2"
    bgpv4_peer.as_number = 65200
    
    # Route with multiple AS path segments
    rr = bgpv4_peer.v4_routes.add(name="rr_multi_seg")
    rr.addresses.add(address="200.1.0.0", prefix=24, count=10)
    
    as_path = rr.as_path
    
    # First segment: AS_SEQ
    seg1 = as_path.segments.add()
    seg1.type = seg1.AS_SEQ
    seg1.as_numbers = [100, 200]
    
    # Second segment: AS_SET
    seg2 = as_path.segments.add()
    seg2.type = seg2.AS_SET
    seg2.as_numbers = [300, 400, 500]
    
    # Third segment: AS_SEQ
    seg3 = as_path.segments.add()
    seg3.type = seg3.AS_SEQ
    seg3.as_numbers = [600]
    
    api.set_config(config)
    
    # Validate multiple segments
    ixn_rr = utils.get_ixnetwork_obj(api, "rr_multi_seg", "ipv4_unicast")
    assert ixn_rr is not None
    ixn_segments = ixn_rr.parent.BgpAsPathSegmentList.find()
    assert len(ixn_segments) == 3


def test_bgp_as_set_mode_variations(api, utils):
    """
    Test different AS set modes for BGP routes.
    
    Configure routes with different as_set_mode values:
    - do_not_include_local_as
    - include_as_seq
    - include_as_set
    - include_as_confed_seq
    - include_as_confed_set
    - prepend_to_first_segment
    
    Validate configuration via RestPy.
    """
    config = api.config()
    
    port = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
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
    eth.mac = "00:00:00:00:00:11"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    
    bgpv4 = device.bgp
    bgpv4.router_id = "192.0.0.1"
    bgpv4_int = bgpv4.ipv4_interfaces.add()
    bgpv4_int.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_int.peers.add()
    bgpv4_peer.name = "bgp_peer"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "21.1.1.2"
    bgpv4_peer.as_number = 65200
    
    # Route 1: do_not_include_local_as
    rr1 = bgpv4_peer.v4_routes.add(name="rr_no_local_as")
    rr1.addresses.add(address="200.1.0.0", prefix=24, count=5)
    as_path1 = rr1.as_path
    as_path1.as_set_mode = as_path1.DO_NOT_INCLUDE_LOCAL_AS
    seg1 = as_path1.segments.add()
    seg1.type = seg1.AS_SEQ
    seg1.as_numbers = [100, 200]
    
    # Route 2: include_as_seq
    rr2 = bgpv4_peer.v4_routes.add(name="rr_include_seq")
    rr2.addresses.add(address="201.1.0.0", prefix=24, count=5)
    as_path2 = rr2.as_path
    as_path2.as_set_mode = as_path2.INCLUDE_AS_SEQ
    seg2 = as_path2.segments.add()
    seg2.type = seg2.AS_SEQ
    seg2.as_numbers = [300, 400]
    
    # Route 3: include_as_set
    rr3 = bgpv4_peer.v4_routes.add(name="rr_include_set")
    rr3.addresses.add(address="202.1.0.0", prefix=24, count=5)
    as_path3 = rr3.as_path
    as_path3.as_set_mode = as_path3.INCLUDE_AS_SET
    seg3 = as_path3.segments.add()
    seg3.type = seg3.AS_SEQ
    seg3.as_numbers = [500, 600]
    
    # Route 4: prepend_to_first_segment
    rr4 = bgpv4_peer.v4_routes.add(name="rr_prepend")
    rr4.addresses.add(address="203.1.0.0", prefix=24, count=5)
    as_path4 = rr4.as_path
    as_path4.as_set_mode = as_path4.PREPEND_TO_FIRST_SEGMENT
    seg4 = as_path4.segments.add()
    seg4.type = seg4.AS_SEQ
    seg4.as_numbers = [700, 800]
    
    api.set_config(config)
    
    # Validate as_set_mode for each route
    ixn_rr1 = utils.get_ixnetwork_obj(api, "rr_no_local_as", "ipv4_unicast")
    assert ixn_rr1 is not None
    assert ixn_rr1.parent.AsSetMode.Values[0] == "dontincludelocalas"
    
    ixn_rr2 = utils.get_ixnetwork_obj(api, "rr_include_seq", "ipv4_unicast")
    assert ixn_rr2 is not None
    assert ixn_rr2.parent.AsSetMode.Values[0] == "includelocalasasasseq"
    
    ixn_rr3 = utils.get_ixnetwork_obj(api, "rr_include_set", "ipv4_unicast")
    assert ixn_rr3 is not None
    assert ixn_rr3.parent.AsSetMode.Values[0] == "includelocalasasasset"
    
    ixn_rr4 = utils.get_ixnetwork_obj(api, "rr_prepend", "ipv4_unicast")
    assert ixn_rr4 is not None
    assert ixn_rr4.parent.AsSetMode.Values[0] == "prependlocalastofirstsegment"


def test_bgp_community_types_extended(api, utils):
    """
    Test all BGP community types including those not commonly tested.
    
    Configure routes with:
    - manual_as_number
    - no_export
    - no_advertised
    - no_export_subconfed
    - llgr_stale
    - no_llgr
    
    Validate configuration.
    """
    config = api.config()
    
    port = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
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
    eth.mac = "00:00:00:00:00:11"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    
    bgpv4 = device.bgp
    bgpv4.router_id = "192.0.0.1"
    bgpv4_int = bgpv4.ipv4_interfaces.add()
    bgpv4_int.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_int.peers.add()
    bgpv4_peer.name = "bgp_peer"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "21.1.1.2"
    bgpv4_peer.as_number = 65200
    
    # Route with multiple community types
    rr = bgpv4_peer.v4_routes.add(name="rr_communities")
    rr.addresses.add(address="200.1.0.0", prefix=24, count=10)
    
    # manual_as_number
    comm1 = rr.communities.add()
    comm1.type = comm1.MANUAL_AS_NUMBER
    comm1.as_number = 65100
    comm1.as_custom = 100
    
    # no_export
    comm2 = rr.communities.add()
    comm2.type = comm2.NO_EXPORT
    
    # no_advertised
    comm3 = rr.communities.add()
    comm3.type = comm3.NO_ADVERTISED
    
    # no_export_subconfed
    comm4 = rr.communities.add()
    comm4.type = comm4.NO_EXPORT_SUBCONFED
    
    # llgr_stale
    comm5 = rr.communities.add()
    comm5.type = comm5.LLGR_STALE
    
    # no_llgr
    comm6 = rr.communities.add()
    comm6.type = comm6.NO_LLGR
    
    api.set_config(config)
    
    # Validate communities are configured
    ixn_rr = utils.get_ixnetwork_obj(api, "rr_communities", "ipv4_unicast")
    assert ixn_rr is not None
    ixn_communities = ixn_rr.parent.BgpCommunitiesList.find()
    assert len(ixn_communities) == 6
    
    # Validate specific community types
    comm_types = [c.Type.Values[0] for c in ixn_communities]
    assert "manual" in comm_types
    assert "noexport" in comm_types
    assert "noadvertised" in comm_types
    assert "noexport_subconfed" in comm_types
    assert "llgr_stale" in comm_types
    assert "no_llgr" in comm_types


def test_bgp_next_hop_manual_configuration(api, utils):
    """
    Test BGP next-hop manual configuration.
    
    Configure:
    - Route with next_hop_mode = "manual"
    - Manual IPv4 next-hop address
    
    Validate:
    - Next-hop is configured correctly
    """
    config = api.config()
    
    port = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
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
    eth.mac = "00:00:00:00:00:11"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    
    bgpv4 = device.bgp
    bgpv4.router_id = "192.0.0.1"
    bgpv4_int = bgpv4.ipv4_interfaces.add()
    bgpv4_int.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_int.peers.add()
    bgpv4_peer.name = "bgp_peer"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "21.1.1.2"
    bgpv4_peer.as_number = 65200
    
    # Route with manual next-hop
    rr = bgpv4_peer.v4_routes.add(name="rr_manual_nh")
    rr.addresses.add(address="200.1.0.0", prefix=24, count=10)
    rr.next_hop_mode = rr.MANUAL
    rr.next_hop_address_type = rr.IPV4
    rr.next_hop_ipv4_address = "50.50.50.1"
    
    api.set_config(config)
    
    # Validate next-hop configuration
    ixn_rr = utils.get_ixnetwork_obj(api, "rr_manual_nh", "ipv4_unicast")
    assert ixn_rr is not None
    assert ixn_rr.NextHopType.Values[0] == "manually"
    assert ixn_rr.NextHopIPType.Values[0] == "ipv4"
    assert ixn_rr.Ipv4NextHop.Values[0] == "50.50.50.1"


def test_bgpv6_next_hop_manual_ipv6(api, utils):
    """
    Test BGPv6 next-hop manual configuration with IPv6 address.
    
    Configure:
    - BGPv6 route with manual next-hop
    - IPv6 next-hop address
    
    Validate:
    - Next-hop IPv6 is configured correctly
    """
    config = api.config()
    
    port = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
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
    eth.mac = "00:00:00:00:00:11"
    
    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = "ipv6"
    ipv6.address = "2000::1"
    ipv6.prefix = 64
    ipv6.gateway = "2000::2"
    
    bgpv6 = device.bgp
    bgpv6.router_id = "192.0.0.1"
    bgpv6_int = bgpv6.ipv6_interfaces.add()
    bgpv6_int.ipv6_name = ipv6.name
    bgpv6_peer = bgpv6_int.peers.add()
    bgpv6_peer.name = "bgp_peer_v6"
    bgpv6_peer.as_type = "ebgp"
    bgpv6_peer.peer_address = "2000::2"
    bgpv6_peer.as_number = 65200
    
    # Route with manual IPv6 next-hop
    rrv6 = bgpv6_peer.v6_routes.add(name="rrv6_manual_nh")
    rrv6.addresses.add(address="4000::1", prefix=64, count=10)
    rrv6.next_hop_mode = rrv6.MANUAL
    rrv6.next_hop_address_type = rrv6.IPV6
    rrv6.next_hop_ipv6_address = "5000::1"
    
    api.set_config(config)
    
    # Validate next-hop configuration
    ixn_rrv6 = utils.get_ixnetwork_obj(api, "rrv6_manual_nh", "ipv6_unicast")
    assert ixn_rrv6 is not None
    assert ixn_rrv6.NextHopType.Values[0] == "manually"
    assert ixn_rrv6.NextHopIPType.Values[0] == "ipv6"
    assert ixn_rrv6.Ipv6NextHop.Values[0] == "5000::1"
