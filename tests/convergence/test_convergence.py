import re
import pytest
from bgp_convergence_config import bgp_convergence_config

PRIMARY_ROUTES_NAME = "rx_rr"
PRIMARY_PORT_NAME = "rx"


def test_convergence_withdraw_event(utils, cvg_api, bgp_convergence_config):
    """
    1. set convergence config & start traffic
    2. Start traffic
    3. Withdraw Routes and see events are populated properly
    """
    # convergence config
    bgp_convergence_config.rx_rate_threshold = 90
    bgp_convergence_config.convergence_event = (
        bgp_convergence_config.ROUTE_WITHDRAW
    )

    cvg_api.set_config(bgp_convergence_config)

    # Scenario 1: Route withdraw/Advertise
    # Start traffic
    cs = cvg_api.convergence_state()
    cs.transmit.state = cs.transmit.START
    cvg_api.set_state(cs)

    # Wait for traffic to reach configured line rate
    utils.wait_for(
        lambda: is_traffic_running(cvg_api), "traffic in started state"
    )

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


def test_convergence_link_down_event(utils, cvg_api, bgp_convergence_config):
    """
    1. set convergence config & start traffic
    2. Start traffic
    3. Shutdown primary port and see events are populated properly
    """
    # convergence config
    bgp_convergence_config.rx_rate_threshold = 90
    bgp_convergence_config.convergence_event = bgp_convergence_config.LINK_DOWN

    cvg_api.set_config(bgp_convergence_config)

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


def test_convergence_event_exception(cvg_api, bgp_convergence_config):
    """
    1. set convergence config & start traffic
    2. Start traffic
    3. Shutdown primary port and check the exception as event configured
       route_withdraw
    """
    # convergence config
    bgp_convergence_config.rx_rate_threshold = 90
    bgp_convergence_config.convergence_event = (
        bgp_convergence_config.ROUTE_WITHDRAW
    )

    cvg_api.set_config(bgp_convergence_config)

    # Link down the primary port
    cs = cvg_api.convergence_state()
    cs.link.port_names = [PRIMARY_PORT_NAME]
    cs.link.state = cs.link.DOWN

    try:
        cvg_api.set_state(cs)
    except Exception as e:
        print(e)
        assert re.search(
            "link_down can't be performed as route_withdraw event is configured",
            str(e),
        )


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
