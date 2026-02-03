import pytest


def test_bgp_isis_same_device(api, b2b_raw_config, utils):
    """
    Test BGP and ISIS on the same device.
    
    Configure:
    - Single device with both BGP and ISIS enabled
    - BGP advertising ISIS routes
    
    Validate:
    - Both protocols configure correctly
    - No conflicts between protocols
    """
    config = b2b_raw_config
    
    device = config.devices.device(name="multi_proto_device")[-1]
    device.container_name = config.ports[0].name
    
    # Ethernet interface
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.mac = "00:00:00:00:00:01"
    
    # IPv4 address
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    # BGP configuration
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = ipv4.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.as_type = "ebgp"
    bgp_peer.peer_address = "10.1.1.2"
    bgp_peer.as_number = 65200
    
    # BGP routes
    bgp_route = bgp_peer.v4_routes.add(name="bgp_routes")
    bgp_route.addresses.add(address="200.1.0.0", prefix=24, count=100)
    
    # ISIS configuration on same device
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    isis_iface.network_type = isis_iface.BROADCAST
    isis_iface.level_type = isis_iface.LEVEL_2
    isis_iface.metric = 10
    
    # ISIS routes
    isis_basic = isis_iface.basic
    if isis_basic:
        isis_basic.hostname = "router1"
        isis_basic.enable_wide_metric = True
    
    isis_route = isis_iface.v4_routes.add()
    isis_route.name = "isis_routes"
    isis_route.addresses.add(address="201.1.0.0", prefix=24, count=100)
    isis_route.origin_type = isis_route.INTERNAL
    isis_route.redistribution_type = isis_route.UP
    
    api.set_config(config)
    
    # Validate both protocols are configured
    ixn_bgp = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_bgp is not None
    
    ixn_isis = utils.get_ixnetwork_obj(api, isis.name, "isisL3")
    assert ixn_isis is not None


def test_dual_stack_bgp_ipv4_ipv6(api, b2b_raw_config, utils):
    """
    Test BGP dual-stack with both IPv4 and IPv6 peers on same device.
    
    Configure:
    - Device with both IPv4 and IPv6 addresses
    - BGPv4 peer over IPv4
    - BGPv6 peer over IPv6
    
    Validate:
    - Both BGP sessions configure correctly
    - Independent route advertisements
    """
    config = b2b_raw_config
    
    device = config.devices.device(name="dual_stack_device")[-1]
    device.container_name = config.ports[0].name
    
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.mac = "00:00:00:00:00:01"
    
    # IPv4 address
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    # IPv6 address
    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = "ipv6"
    ipv6.address = "2001:db8::1"
    ipv6.prefix = 64
    ipv6.gateway = "2001:db8::2"
    
    # BGP configuration
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    
    # BGPv4 peer
    bgpv4_iface = bgp.ipv4_interfaces.add()
    bgpv4_iface.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_iface.peers.add()
    bgpv4_peer.name = "bgpv4_peer"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "10.1.1.2"
    bgpv4_peer.as_number = 65200
    
    bgpv4_route = bgpv4_peer.v4_routes.add(name="v4_routes")
    bgpv4_route.addresses.add(address="200.1.0.0", prefix=24, count=50)
    
    # BGPv6 peer
    bgpv6_iface = bgp.ipv6_interfaces.add()
    bgpv6_iface.ipv6_name = ipv6.name
    bgpv6_peer = bgpv6_iface.peers.add()
    bgpv6_peer.name = "bgpv6_peer"
    bgpv6_peer.as_type = "ebgp"
    bgpv6_peer.peer_address = "2001:db8::2"
    bgpv6_peer.as_number = 65200
    
    bgpv6_route = bgpv6_peer.v6_routes.add(name="v6_routes")
    bgpv6_route.addresses.add(address="4000::", prefix=64, count=50)
    
    api.set_config(config)
    
    # Validate both BGP sessions
    ixn_bgpv4 = utils.get_ixnetwork_obj(api, bgpv4_peer.name, "bgpIpv4Peer")
    assert ixn_bgpv4 is not None
    
    ixn_bgpv6 = utils.get_ixnetwork_obj(api, bgpv6_peer.name, "bgpIpv6Peer")
    assert ixn_bgpv6 is not None


def test_dual_stack_isis_ipv4_ipv6_routes(api, b2b_raw_config, utils):
    """
    Test ISIS dual-stack with both IPv4 and IPv6 routes.
    
    Configure:
    - ISIS router advertising both IPv4 and IPv6 routes
    
    Validate:
    - Both address families are advertised
    """
    config = b2b_raw_config
    
    device = config.devices.device(name="isis_dual_stack")[-1]
    device.container_name = config.ports[0].name
    
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.mac = "00:00:00:00:00:01"
    
    # IPv4 address
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    # IPv6 address
    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = "ipv6"
    ipv6.address = "2001:db8::1"
    ipv6.prefix = 64
    ipv6.gateway = "2001:db8::2"
    
    # ISIS configuration
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    isis_iface.network_type = isis_iface.BROADCAST
    isis_iface.level_type = isis_iface.LEVEL_2
    
    # IPv4 routes
    v4_route = isis_iface.v4_routes.add()
    v4_route.name = "isis_v4_routes"
    v4_route.addresses.add(address="200.1.0.0", prefix=24, count=100)
    v4_route.origin_type = v4_route.INTERNAL
    
    # IPv6 routes
    v6_route = isis_iface.v6_routes.add()
    v6_route.name = "isis_v6_routes"
    v6_route.addresses.add(address="4000::", prefix=64, count=100)
    v6_route.origin_type = v6_route.INTERNAL
    
    api.set_config(config)
    
    # Validate ISIS configuration
    ixn_isis = utils.get_ixnetwork_obj(api, isis.name, "isisL3")
    assert ixn_isis is not None


def test_bgp_evpn_with_vlan(api, b2b_raw_config, utils):
    """
    Test BGP EVPN configuration with VLAN tagging.
    
    Configure:
    - VLAN-tagged ethernet
    - BGP EVPN over VLAN interface
    
    Validate:
    - VLAN and EVPN work together
    """
    config = b2b_raw_config
    
    device = config.devices.device(name="evpn_vlan_device")[-1]
    device.container_name = config.ports[0].name
    
    # Ethernet with VLAN
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.mac = "00:00:00:00:00:01"
    
    vlan = eth.vlans.add()
    vlan.name = "vlan100"
    vlan.id = 100
    vlan.priority = 7
    
    # Loopback for BGP EVPN
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.eth_name = eth.name
    loopback.address = "1.1.1.1"
    
    # BGP EVPN configuration
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_evpn_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    # EVPN Ethernet Segment
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    # EVI
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    rt_export = evi.route_target_export.add()
    rt_export.rt_type = rt_export.AS_2OCTET
    rt_export.rt_value = "100:100"
    
    rt_import = evi.route_target_import.add()
    rt_import.rt_type = rt_import.AS_2OCTET
    rt_import.rt_value = "100:100"
    
    api.set_config(config)
    
    # Validate VLAN and EVPN
    ixn_vlan = utils.get_ixnetwork_obj(api, vlan.name, "vlan")
    assert ixn_vlan is not None
    
    ixn_bgp = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_bgp is not None


def test_bgp_with_all_attributes_combined(api, utils):
    """
    Test BGP with complete feature matrix - all attributes combined.
    
    Configure:
    - BGP peer with communities, extended communities, AS path, MED, origin
    - IPv4 and IPv6 routes
    - Advanced settings (hold time, keepalive, MD5)
    - All capabilities enabled
    
    Validate:
    - All features work together without conflicts
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="full_bgp_device")[-1]
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
    bgp_peer.name = "full_featured_peer"
    bgp_peer.as_type = "ebgp"
    bgp_peer.peer_address = "10.1.1.2"
    bgp_peer.as_number = 65200
    
    # Advanced settings
    adv = bgp_peer.advanced
    adv.hold_time_interval = 180
    adv.keep_alive_interval = 60
    adv.update_interval = 30
    adv.time_to_live = 64
    adv.md5_key = "bgp_secret_key"
    
    # Capabilities
    cap = bgp_peer.capability
    cap.ipv4_unicast = True
    cap.ipv4_multicast = True
    cap.ipv6_unicast = True
    cap.ipv6_multicast = True
    cap.evpn = True
    cap.route_refresh = True
    cap.ipv4_sr_te_policy = True
    cap.ipv6_sr_te_policy = True
    
    # Route with all attributes
    route = bgp_peer.v4_routes.add(name="full_featured_route")
    route.addresses.add(address="200.1.0.0", prefix=24, count=100)
    
    # Communities (multiple types)
    comm1 = route.communities.add()
    comm1.type = comm1.MANUAL_AS_NUMBER
    comm1.as_number = 65100
    comm1.as_custom = 100
    
    comm2 = route.communities.add()
    comm2.type = comm2.NO_EXPORT
    
    comm3 = route.communities.add()
    comm3.type = comm3.LLGR_STALE
    
    # AS Path (multiple segments)
    as_path = route.as_path
    as_path.as_set_mode = as_path.INCLUDE_AS_SEQ
    
    seg1 = as_path.segments.add()
    seg1.type = seg1.AS_SEQ
    seg1.as_numbers = [100, 200, 300]
    
    seg2 = as_path.segments.add()
    seg2.type = seg2.AS_SET
    seg2.as_numbers = [400, 500]
    
    # Advanced route attributes
    route_adv = route.advanced
    route_adv.multi_exit_discriminator = 100
    route_adv.origin = route_adv.IGP
    route_adv.local_preference = 200
    
    # Next-hop
    route.next_hop_mode = route.MANUAL
    route.next_hop_address_type = route.IPV4
    route.next_hop_ipv4_address = "50.50.50.1"
    
    api.set_config(config)
    
    # Validate complete configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None
    assert ixn_peer.HoldTimer.Values[0] == 180
    assert ixn_peer.KeepaliveTimer.Values[0] == 60
    
    ixn_route = utils.get_ixnetwork_obj(api, route.name, "ipv4_unicast")
    assert ixn_route is not None


def test_vlan_stacking_with_bgp(api, b2b_raw_config, utils):
    """
    Test VLAN stacking (Q-in-Q) with BGP routing.
    
    Configure:
    - Double VLAN tags
    - BGP over stacked VLANs
    
    Validate:
    - VLAN stacking and BGP coexist
    """
    config = b2b_raw_config
    
    device = config.devices.device(name="qinq_bgp_device")[-1]
    device.container_name = config.ports[0].name
    
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.mac = "00:00:00:00:00:01"
    
    # Outer VLAN (Provider)
    vlan_outer = eth.vlans.add()
    vlan_outer.name = "vlan_outer"
    vlan_outer.id = 100
    vlan_outer.tpid = "x88a8"
    vlan_outer.priority = 7
    
    # Inner VLAN (Customer)
    vlan_inner = eth.vlans.add()
    vlan_inner.name = "vlan_inner"
    vlan_inner.id = 200
    vlan_inner.tpid = "x8100"
    vlan_inner.priority = 5
    
    # IPv4 address
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    # BGP over stacked VLANs
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = ipv4.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_qinq_peer"
    bgp_peer.as_type = "ebgp"
    bgp_peer.peer_address = "10.1.1.2"
    bgp_peer.as_number = 65200
    
    route = bgp_peer.v4_routes.add(name="qinq_routes")
    route.addresses.add(address="200.1.0.0", prefix=24, count=50)
    
    api.set_config(config)
    
    # Validate VLAN stacking
    ixn_eth = utils.get_ixnetwork_obj(api, eth.name, "ethernet")
    assert ixn_eth is not None
    assert ixn_eth.VlanCount.Values[0] == 2
    
    # Validate BGP
    ixn_bgp = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_bgp is not None
