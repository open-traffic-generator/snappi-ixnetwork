import pytest


@pytest.mark.skip(reason="Fix -breaks build - needs investigation")
def test_update_flows(api, b2b_raw_config, utils):
    """
    This test is to validate update_flows API

    1. once initial config is set, the test will update rate on one flow
       and size on other flow and validates if the rate and size got updated
       on the fly.

    2. Negative tests include updating other properties which are not allowed
       currently and the server should throw and exception.
    """

    ports = b2b_raw_config.ports
    flow1 = b2b_raw_config.flows[0]
    flow1.name = "tx_flow1"
    flow1.packet.ethernet().ipv4()
    flow1.packet[0].src.value = "00:0c:29:1d:10:67"
    flow1.packet[0].dst.value = "00:0c:29:1d:10:71"
    flow1.packet[1].src.value = "10.10.10.1"
    flow1.packet[1].dst.value = "10.10.10.2"
    flow2 = b2b_raw_config.flows.flow()[-1]
    flow2.name = "tx_flow2"
    flow2.tx_rx.port.tx_name = ports[0].name
    flow2.tx_rx.port.rx_name = ports[1].name

    flow3 = b2b_raw_config.flows.flow()[-1]
    flow3.name = "tx_flow3"
    flow3.tx_rx.port.tx_name = ports[0].name
    flow3.tx_rx.port.rx_name = ports[1].name

    flow1.duration.fixed_packets.packets = 1000
    flow1.size.fixed = 1000
    flow1.duration.choice = flow1.duration.CONTINUOUS
    flow1.rate.pps = 1000

    flow2.duration.fixed_packets.packets = 1000
    flow2.size.fixed = 1000
    flow2.duration.choice = flow1.duration.CONTINUOUS
    flow2.rate.pps = 1000

    flow3.duration.fixed_packets.packets = 1000
    flow3.size.fixed = 1000
    flow3.duration.choice = flow3.duration.CONTINUOUS
    flow3.rate.pps = 1000

    flow1.metrics.enable = True
    flow1.metrics.loss = True

    flow3.metrics.enable = True
    flow3.metrics.loss = True

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=False)

    utils.wait_for(
        lambda: stats_ok(api, 2 * 1000, utils), "stats to be as expected"
    )

    req = api.flows_update()
    req.property_names = [req.RATE, req.SIZE]

    update_flow1 = b2b_raw_config.flows[0]
    update_flow1.rate.pps = 2000
    req.flows.append(update_flow1)

    update_flow2 = b2b_raw_config.flows[2]
    update_flow2.size.fixed = 2000
    req.flows.append(update_flow2)

    api.update_flows(req)

    # update size validation
    validate_config(api, "tx_flow3", 2000)
    import time

    time.sleep(5)

    # update rate validation total 3000 = 1000(tx_flow1) + 2000(tx_flow3)
    utils.wait_for(
        lambda: stats_ok(api, 3000, utils), "stats to be as expected"
    )

    # Negative test
    req = api.flows_update()
    req.property_names = [req.RATE, req.SIZE]

    update_flow1 = b2b_raw_config.flows[0]
    update_flow1.tx_rx.port.tx_name = "rx"
    update_flow1.tx_rx.port.rx_name = "tx"
    update_flow1.packet.ethernet().ipv4()
    update_flow1.packet[0].src.value = "00:0c:29:1d:10:98"
    update_flow1.packet[0].dst.value = "00:0c:29:1e:10:71"
    update_flow1.packet[1].src.value = "20.20.20.1"
    update_flow1.packet[1].dst.value = "10.20.30.2"
    req.flows.append(update_flow1)

    try:
        api.update_flows(req)
    except Exception as e:
        assert (
            "tx_rx property update is not supported on flow tx_flow1"
            in ",".join(e.message)
        )
        assert (
            "packet property update is not supported on flow tx_flow1"
            in ",".join(e.message)
        )

    utils.stop_traffic(api, b2b_raw_config)


def validate_config(api, flow_name, updated_size):
    assert (
        api._ixnetwork.Traffic.TrafficItem.find(Name=flow_name)
        .HighLevelStream.find()
        .FrameSize.FixedSize
    ) == updated_size


def stats_ok(api, framerate, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    _, flow_stats = utils.get_all_stats(api)

    frame_rate = sum([f.frames_tx_rate for f in flow_stats])

    return frame_rate == framerate


if __name__ == "__main__":
    pytest.main(["-s", __file__])
