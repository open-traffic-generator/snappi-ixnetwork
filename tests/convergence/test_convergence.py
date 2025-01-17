import pytest

PRIMARY_ROUTES_NAME = "rx_rr"
PRIMARY_PORT_NAME = "rx"


def test_convergence(utils, api):
    """
    1. set convergence config & start traffic
    Scenario 1:
    1. Start traffic
    2. Withdraw Routes and see events are populated properly
    Scenario 2:
    1. Start traffic
    2. Shutdown primary port and see events are populated properly
    """
    bgp_convergence_config = convergence_config(utils, api)
    # convergence config
    bgp_convergence_config.events.cp_events.enable = True
    bgp_convergence_config.events.dp_events.enable = True
    bgp_convergence_config.events.dp_events.rx_rate_threshold = 90

    api.set_config(bgp_convergence_config)
    print("Starting all protocols ...")
    ps = api.control_state()
    ps.choice = ps.PROTOCOL
    ps.protocol.choice = ps.protocol.ALL
    ps.protocol.all.state = ps.protocol.all.START
    res = api.set_control_state(ps)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # Scenario 1: Route withdraw/Advertise
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
        lambda: is_traffic_running(api), "traffic in started state"
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

    # Withdraw routes from primary path
    cs = api.control_state()
    cs.protocol.route.names = [PRIMARY_ROUTES_NAME]
    cs.protocol.route.state = cs.protocol.route.WITHDRAW
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))
    
    # get convergence metrics
    request = api.metrics_request()
    request.convergence.flow_names = ["convergence_test"]
    convergence_metrics = api.get_metrics(request).convergence_metrics
    print("Convergence Metrics")
    print(convergence_metrics)
    for metrics in convergence_metrics:
        assert isinstance(
            metrics.control_plane_data_plane_convergence_us, float
        )
        assert len(metrics.events) > 0
        for event in metrics.events:
            assert event.type == "route_withdraw"

    # Re-advertise the routes
    cs = api.control_state()
    cs.protocol.route.names = [PRIMARY_ROUTES_NAME]
    cs.protocol.route.state = cs.protocol.route.ADVERTISE
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # Stop traffic
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP  
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # Scenario 2: Link Up/Down
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
        lambda: is_traffic_running(api), "traffic in started state"
    )

    # Link down the primary port
    cs = api.control_state()
    cs.port.link.port_names = [PRIMARY_PORT_NAME]
    cs.port.link.state = cs.port.link.DOWN
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # get convergence metrics
    request = api.metrics_request()
    request.convergence.flow_names = ["convergence_test"]
    convergence_metrics = api.get_metrics(request).convergence_metrics
    print("Convergence Metrics")
    print(convergence_metrics)
    for metrics in convergence_metrics:
        assert isinstance(
            metrics.control_plane_data_plane_convergence_us, float
        )
        assert len(metrics.events) > 0
        for event in metrics.events:
            assert event.type == "link_down"

    # Link up primary port
    cs = api.control_state()
    cs.port.link.port_names = [PRIMARY_PORT_NAME]
    cs.port.link.state = cs.port.link.UP
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # Stop traffic
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP  
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    # TODO: As ixNetwork sometimes not clearing the ownership from one
    # session to another session
    conv_config = api.config()
    api.set_config(conv_config)


def convergence_config(utils, api):
    """
    1.Configure IPv4 EBGP sessions between Keysight ports(rx & tx)
    2.Configure and advertise IPv4 routes from rx
    """

    conv_config = api.config()

    tx, rx = conv_config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    conv_config.options.port_options.location_preemption = True
    ly = conv_config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [tx.name, rx.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    tx_device, rx_device = conv_config.devices.device(name="tx_device").device(
        name="rx_device"
    )

    # tx_device config
    tx_eth = tx_device.ethernets.add()
    tx_eth.connection.port_name = tx.name
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:00:00:00:00:aa"
    tx_ipv4 = tx_eth.ipv4_addresses.add()
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address = "21.1.1.2"
    tx_ipv4.prefix = 24
    tx_ipv4.gateway = "21.1.1.1"
    tx_bgpv4 = tx_device.bgp
    tx_bgpv4.router_id = "192.0.0.1"
    tx_bgpv4_int = tx_bgpv4.ipv4_interfaces.add()
    tx_bgpv4_int.ipv4_name = tx_ipv4.name
    tx_bgpv4_peer = tx_bgpv4_int.peers.add()
    tx_bgpv4_peer.name = "tx_bgpv4"
    tx_bgpv4_peer.as_type = "ebgp"
    tx_bgpv4_peer.peer_address = "21.1.1.1"
    tx_bgpv4_peer.as_number = 65201

    # rx_device config
    rx_eth = rx_device.ethernets.add()
    rx_eth.connection.port_name = rx.name
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv4 = rx_eth.ipv4_addresses.add()
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address = "21.1.1.1"
    rx_ipv4.prefix = 24
    rx_ipv4.gateway = "21.1.1.2"
    rx_bgpv4 = rx_device.bgp
    rx_bgpv4.router_id = "192.0.0.2"
    rx_bgpv4_int = rx_bgpv4.ipv4_interfaces.add()
    rx_bgpv4_int.ipv4_name = rx_ipv4.name
    rx_bgpv4_peer = rx_bgpv4_int.peers.add()
    rx_bgpv4_peer.name = "rx_bgpv4"
    rx_bgpv4_peer.as_type = "ebgp"
    rx_bgpv4_peer.peer_address = "21.1.1.2"
    rx_bgpv4_peer.as_number = 65200
    rx_rr = rx_bgpv4_peer.v4_routes.add(name="rx_rr")
    rx_rr.addresses.add(count=1000, address="200.1.0.1", prefix=32)

    # flow config
    flow = conv_config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_device.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    flow.size.fixed = 1024
    flow.rate.percentage = 50
    flow.metrics.enable = True

    # flow2 config
    rx1_rr = rx_bgpv4_peer.v4_routes.add(name="rx1_rr")
    rx1_rr.addresses.add(count=1000, address="200.1.0.1", prefix=32)

    # flow config
    flow2 = conv_config.flows.flow(name="background_flow")[-1]
    flow2.tx_rx.device.tx_names = [tx_device.name]
    flow2.tx_rx.device.rx_names = [rx1_rr.name]

    flow2.size.fixed = 1024
    flow2.rate.percentage = 50
    flow2.metrics.enable = True

    return conv_config


def is_traffic_running(api):
    """
    Returns true if traffic in start state
    """
    flow_stats = get_flow_stats(api)
    return all([int(fs.frames_rx_rate) > 0 for fs in flow_stats])


def get_flow_stats(api):
    request = api.metrics_request()
    request.convergence.flow_names = []
    return api.get_metrics(request).flow_metrics


if __name__ == "__main__":
    pytest.main(["-s", __file__])
