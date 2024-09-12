import pytest
# from bgp_convergence_config import bgp_convergence_config

PRIMARY_ROUTES_NAME = "rx_rr"
PRIMARY_PORT_NAME = "rx"

@pytest.mark.skip(reason="Fix -convergence support TBD")
def test_convergence(utils, cvg_api, bgp_convergence_config):
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
    bgp_convergence_config.rx_rate_threshold = 90

    cvg_api.set_config(bgp_convergence_config)

    print("Starting all protocols ...")
    cs = cvg_api.convergence_state()
    cs.protocol.state = cs.protocol.START
    cvg_api.set_state(cs)

    # Scenario 1: Route withdraw/Advertise
    # Start traffic
    cs = cvg_api.convergence_state()
    cs.transmit.state = cs.transmit.START
    cvg_api.set_state(cs)

    # Wait for traffic to reach configured line rate
    utils.wait_for(
        lambda: is_traffic_running(cvg_api), "traffic in started state"
    )

    # Validate bgpv4 metrics
    req = cvg_api.convergence_request()
    req.bgpv4.peer_names = []
    bgpv4_metrics = cvg_api.get_results(req).bgpv4_metrics
    print(bgpv4_metrics)

    for bgp_metric in bgpv4_metrics:
        assert bgp_metric.session_state == "up"

    # Withdraw routes from primary path
    cs = cvg_api.convergence_state()
    cs.route.names = [PRIMARY_ROUTES_NAME]
    cs.route.state = cs.route.WITHDRAW
    cvg_api.set_state(cs)

    # get convergence metrics
    request = cvg_api.convergence_request()
    request.convergence.flow_names = ["convergence_test"]
    convergence_metrics = cvg_api.get_results(request).flow_convergence

    print(convergence_metrics)
    for metrics in convergence_metrics:
        assert isinstance(
            metrics.control_plane_data_plane_convergence_us, float
        )
        assert len(metrics.events) > 0
        for event in metrics.events:
            assert event.type == "route_withdraw"

    # Re-advertise the routes
    cs = cvg_api.convergence_state()
    cs.route.names = [PRIMARY_ROUTES_NAME]
    cs.route.state = cs.route.ADVERTISE
    cvg_api.set_state(cs)

    # Stop traffic
    cs = cvg_api.convergence_state()
    cs.transmit.state = cs.transmit.STOP
    cvg_api.set_state(cs)

    # Scenario 2: Link Up/Down
    # Start traffic
    cs = cvg_api.convergence_state()
    cs.transmit.state = cs.transmit.START
    cvg_api.set_state(cs)

    # Wait for traffic to reach configured line rate
    utils.wait_for(
        lambda: is_traffic_running(cvg_api), "traffic in started state"
    )

    # Link down the primary port
    cs = cvg_api.convergence_state()
    cs.link.port_names = [PRIMARY_PORT_NAME]
    cs.link.state = cs.link.DOWN
    cvg_api.set_state(cs)

    # get convergence metrics
    request = cvg_api.convergence_request()
    request.convergence.flow_names = ["convergence_test"]
    convergence_metrics = cvg_api.get_results(request).flow_convergence

    print(convergence_metrics)
    for metrics in convergence_metrics:
        assert isinstance(
            metrics.control_plane_data_plane_convergence_us, float
        )
        assert len(metrics.events) > 0
        for event in metrics.events:
            assert event.type == "link_down"

    # Link up primary port
    cs = cvg_api.convergence_state()
    cs.link.port_names = [PRIMARY_PORT_NAME]
    cs.link.state = cs.link.UP
    cvg_api.set_state(cs)

    # Stop traffic
    cs = cvg_api.convergence_state()
    cs.transmit.state = cs.transmit.STOP
    cvg_api.set_state(cs)

    # TODO: As ixNetwork sometimes not clearing the ownership from one
    # session to another session
    conv_config = cvg_api.convergence_config()
    conv_config.config
    cvg_api.set_config(conv_config)


def is_traffic_running(cvg_api):
    """
    Returns true if traffic in start state
    """
    flow_stats = get_flow_stats(cvg_api)
    return all([int(fs.frames_rx_rate) > 0 for fs in flow_stats])


def get_flow_stats(cvg_api):
    request = cvg_api.convergence_request()
    request.metrics.flow_names = []
    return cvg_api.get_results(request).flow_metric


if __name__ == "__main__":
    pytest.main(["-s", __file__])
