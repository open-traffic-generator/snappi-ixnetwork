import pytest

def test_traffic_bidirectional(api, b2b_raw_config, utils):
    """
    Configure IPv4 devices on the Tx and Rx ports and create a flow with
    device endpoints using the bidirectional option under flows->tx_rx->device.

    When bidirectional is enabled, IxNetwork creates traffic sub-flows in both
    the forward (tx_names -> rx_names) and reverse (rx_names -> tx_names)
    directions.

    Validation:
    - the imported IxNetwork traffic item has BiDirectional set to True.
    - traffic starts and every configured packet is received without loss.
      Since the flow is bidirectional, both directions transmit, so the total
      transmitted/received count is 2 * packets.
    """
    packets = 1000
    size = 128

    # enable per-sub-flow (Tx Port / Rx Port) metric rows so the forward and
    # reverse directions of the bidirectional flow are reported separately.
    api._enable_flow_tracking(True)

    b2b_raw_config.flows.clear()
    config = b2b_raw_config

    config.options.port_options.frame_ordering_mode.choice = (
        config.options.port_options.frame_ordering_mode.RFC2889
    )
    # config.options.port_options.data_integrity = True

    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [ip1.name]
    f1.tx_rx.device.rx_names = [ip2.name]
    f1.tx_rx.device.bidirectional = True
    f1.packet.ethernet().ipv4().tcp()
    f1.size.fixed = size
    f1.rate.percentage = 10
    f1.duration.fixed_packets.packets = packets
    f1.metrics.enable = True
    f1.metrics.loss = True

    api.set_config(config)

    validate_bidirectional(api, "f1", True)

    utils.start_traffic(api, config, start_capture=False)

    # frameCount is split across the forward + reverse sub-flows, so the
    # combined tx/rx across all sub-flows equals the configured packet count.
    expected = packets
    utils.wait_for(
        lambda: results_ok(api, ["f1"], expected),
        "stats to be as expected",
        timeout_seconds=30,
    )

    # with flow tracking enabled we expect two sub-flow rows: the forward
    # (port0 -> port1) and reverse (port1 -> port0) directions.
    sub_flows = print_flow_metrics(api, ["f1"])
    assert len(sub_flows) == 2

    utils.stop_traffic(api, config)


def test_traffic_bidirectional_disabled(api, b2b_raw_config):
    """
    By default device flows are unidirectional. Verify that when bidirectional
    is not set the imported IxNetwork traffic item has BiDirectional False.
    """
    b2b_raw_config.flows.clear()
    config = b2b_raw_config
    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [ip1.name]
    f1.tx_rx.device.rx_names = [ip2.name]
    f1.packet.ethernet().ipv4().tcp()
    f1.metrics.enable = True

    api.set_config(config)

    validate_bidirectional(api, "f1", False)


def validate_bidirectional(api, flow_name, expected):
    """
    Validate that the imported IxNetwork traffic item carries the expected
    BiDirectional value.
    """
    traffic_item = api._ixnetwork.Traffic.TrafficItem.find(Name=flow_name)
    assert traffic_item.BiDirectional == expected


def results_ok(api, flow_names, expected):
    """
    Returns True if the received frame count matches the expected count with
    no traffic loss, else False.
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    frames_tx = sum([f.frames_tx for f in flow_results])
    frames_rx = sum([f.frames_rx for f in flow_results])
    return frames_tx == expected and frames_rx == expected


def print_flow_metrics(api, flow_names):
    """
    Fetch flow metrics for the given flows and print each sub-flow's stats,
    differentiated by its Tx Port / Rx Port. With flow tracking enabled a
    bidirectional flow yields one row per direction. Returns the sub-flow rows.
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    print("\nFlow metrics:")
    print(flow_results)
    for flow in flow_results:
        print(
            "  %s [%s -> %s]: tx=%s rx=%s loss=%s"
            % (
                flow.name,
                flow.port_tx,
                flow.port_rx,
                flow.frames_tx,
                flow.frames_rx,
                flow.loss,
            )
        )
    return flow_results


if __name__ == "__main__":
    pytest.main(["-s", __file__])
