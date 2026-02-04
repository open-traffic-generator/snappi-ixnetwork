import pytest


def test_bgpv6_dual_stack_routes(api, b2b_raw_config, utils):
    """
    Test for dual stack BGP configuration with both BGPv4 and BGPv6 sessions
    
    This demonstrates:
    - Ethernet with both IPv4 and IPv6 addresses (dual stack)
    - Separate BGPv4 session over IPv4 transport
    - Separate BGPv6 session over IPv6 transport
    - IPv4 routes advertised over BGPv4 session
    - IPv6 routes advertised over BGPv6 session
    - Traffic validation for both address families
    """
    size = 1500
    packets = 1000
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    # convergence config
    b2b_raw_config.events.cp_events.enable = True
    b2b_raw_config.events.dp_events.enable = True
    b2b_raw_config.events.dp_events.rx_rate_threshold = 90

    # Configure ports and devices
    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="tx_bgp").device(name="rx_bgp")
    
    # Configure Ethernet interfaces
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    eth1.name, eth2.name = "eth1", "eth2"
    
    # Configure IPv4 addresses (dual stack - layer 1)
    ipv4_1, ipv4_2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ipv4_1.name, ipv4_2.name = "ipv4_1", "ipv4_2"
    ipv4_1.address = "10.1.1.1"
    ipv4_1.gateway = "10.1.1.2"
    ipv4_1.prefix = 24
    
    ipv4_2.address = "10.1.1.2"
    ipv4_2.gateway = "10.1.1.1"
    ipv4_2.prefix = 24
    
    # Configure IPv6 addresses (dual stack - layer 2)
    ipv6_1, ipv6_2 = eth1.ipv6_addresses.add(), eth2.ipv6_addresses.add()
    ipv6_1.name, ipv6_2.name = "ipv6_1", "ipv6_2"
    ipv6_1.address = "2000::1"
    ipv6_1.gateway = "2000::2"
    ipv6_1.prefix = 64
    
    ipv6_2.address = "2000::2"
    ipv6_2.gateway = "2000::1"
    ipv6_2.prefix = 64
    
    # Configure BGP routers
    bgp1, bgp2 = d1.bgp, d2.bgp
    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"
    
    # Configure BGPv4 session over IPv4 interface
    bgp1_ipv4_int, bgp2_ipv4_int = bgp1.ipv4_interfaces.add(), bgp2.ipv4_interfaces.add()
    bgp1_ipv4_int.ipv4_name, bgp2_ipv4_int.ipv4_name = ipv4_1.name, ipv4_2.name
    
    # Configure BGPv4 peers
    bgp1_v4_peer, bgp2_v4_peer = bgp1_ipv4_int.peers.add(), bgp2_ipv4_int.peers.add()
    bgp1_v4_peer.name, bgp2_v4_peer.name = "bgpv4_peer1", "bgpv4_peer2"
    
    bgp1_v4_peer.peer_address = "10.1.1.2"
    bgp1_v4_peer.as_type = "ibgp"
    bgp1_v4_peer.as_number = 65001
    
    bgp2_v4_peer.peer_address = "10.1.1.1"
    bgp2_v4_peer.as_type = "ibgp"
    bgp2_v4_peer.as_number = 65001
    
    # Configure BGPv6 session over IPv6 interface
    bgp1_ipv6_int, bgp2_ipv6_int = bgp1.ipv6_interfaces.add(), bgp2.ipv6_interfaces.add()
    bgp1_ipv6_int.ipv6_name, bgp2_ipv6_int.ipv6_name = ipv6_1.name, ipv6_2.name
    
    # Configure BGPv6 peers
    bgp1_v6_peer, bgp2_v6_peer = bgp1_ipv6_int.peers.add(), bgp2_ipv6_int.peers.add()
    bgp1_v6_peer.name, bgp2_v6_peer.name = "bgpv6_peer1", "bgpv6_peer2"
    
    bgp1_v6_peer.peer_address = "2000::2"
    bgp1_v6_peer.as_type = "ibgp"
    bgp1_v6_peer.as_number = 65001
    
    bgp2_v6_peer.peer_address = "2000::1"
    bgp2_v6_peer.as_type = "ibgp"
    bgp2_v6_peer.as_number = 65001
    
    # Configure IPv4 route ranges over BGPv4 session
    bgp1_v4_route = bgp1_v4_peer.v4_routes.add(name="bgp1_v4_routes")
    bgp2_v4_route = bgp2_v4_peer.v4_routes.add(name="bgp2_v4_routes")
    
    bgp1_v4_route.addresses.add(address="100.1.1.1", prefix=32, count=10, step=1)
    bgp2_v4_route.addresses.add(address="200.1.1.1", prefix=32, count=10, step=1)
    
    # Configure IPv6 route ranges over BGPv6 session
    bgp1_v6_route = bgp1_v6_peer.v6_routes.add(name="bgp1_v6_routes")
    bgp2_v6_route = bgp2_v6_peer.v6_routes.add(name="bgp2_v6_routes")
    
    bgp1_v6_route.addresses.add(address="3000::1", prefix=128, count=10, step=1)
    bgp2_v6_route.addresses.add(address="4000::1", prefix=128, count=10, step=1)
    
    
    # Configure traffic flow for IPv4 routes (over BGPv4 session)
    flow_v4 = b2b_raw_config.flows.flow(name="flow_bgpv4")[-1]
    flow_v4.rate.percentage = 50
    flow_v4.size.fixed = size
    flow_v4.tx_rx.device.tx_names = [bgp1_v4_route.name]
    flow_v4.tx_rx.device.rx_names = [bgp2_v4_route.name]
    flow_v4.metrics.enable = True
    
    # Configure traffic flow for IPv6 routes (over BGPv6 session)
    flow_v6 = b2b_raw_config.flows.flow(name="flow_bgpv6")[-1]
    flow_v6.rate.percentage = 50
    flow_v6.size.fixed = size
    flow_v6.tx_rx.device.tx_names = [bgp1_v6_route.name]
    flow_v6.tx_rx.device.rx_names = [bgp2_v6_route.name]
    flow_v6.metrics.enable = True
    
    # Apply configuration
    api.set_config(b2b_raw_config)

    print("Starting all protocols ...")
    ps = api.control_state()
    ps.choice = ps.PROTOCOL
    ps.protocol.choice = ps.protocol.ALL
    ps.protocol.all.state = ps.protocol.all.START
    res = api.set_control_state(ps)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # Start traffic
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # Wait for traffic to reach configured line rate
    utils.wait_for(
        lambda: utils.is_traffic_running(api), "traffic in started state"
    )

    # Wait for traffic to reach configured line rate
    utils.wait_for(
        lambda: utils.is_traffic_running(api), "traffic in started state"
    )

    # Port Metrics
    req = api.metrics_request()
    req.port.port_names = []
    port_metrics = api.get_metrics(req).port_metrics
    utils.print_stats(port_stats=port_metrics)

    # Flow Metrics
    req = api.metrics_request()
    req.flow.flow_names = []
    flow_metrics = api.get_metrics(req).flow_metrics
    utils.print_stats(flow_stats=flow_metrics)
    
    # BGPv4 metrics
    req = api.metrics_request()
    req.bgpv4.peer_names = []
    bgpv4_metrics = api.get_metrics(req).bgpv4_metrics
    utils.print_stats(bgpv4_stats=bgpv4_metrics)

    # Validate all BGPv4 sessions are up
    for bgp_metric in bgpv4_metrics:
        assert bgp_metric.session_state == "up"
    
    # BGPv6 metrics
    req = api.metrics_request()
    req.bgpv6.peer_names = []
    bgpv6_metrics = api.get_metrics(req).bgpv6_metrics
    utils.print_stats(bgpv6_stats=bgpv6_metrics)

    # Validate all BGPv6 sessions are up
    for bgp_metric in bgpv6_metrics:
        assert bgp_metric.session_state == "up"

    # Stop traffic
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP  
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # session to another session
    conv_config = api.config()
    api.set_config(conv_config)




