import pytest
from bgp_convergence_config_b2b import bgp_convergence_config

PRIMARY_ROUTES_NAME = "rx_rr"
PRIMARY_PORT_NAME = "rx"


def test_convergence(utils, api, bgp_convergence_config):
    """
    1. set convergence config & start traffic
    Scenario 1:
    1. Start traffic
    2. Withdraw Routes and see events are populated properly
    Scenario 2:
    1. Start traffic
    2. Shutdown primary port and see events are populated properly
    """
    
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
        lambda: utils.is_traffic_running(api), "traffic in started state"
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


if __name__ == "__main__":
    pytest.main(["-s", __file__])
