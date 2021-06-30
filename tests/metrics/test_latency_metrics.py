import pytest


def test_latency_metrics(api, utils, b2b_raw_config, tx_port, rx_port):
    """This is a test script to test latency metrics & timestamps,
    metrics& timestamps should be available only for the flows
     latency is enabled
    1. Create two flows f1&f2
    2. f1 with latency enabled
    3. f2 with latency disabled
    Validation:
    - Check stats and latency metrics are available only for f1
    """
    SIZE = 1024
    PACKETS = 1000

    f1 = b2b_raw_config.flows[0]

    f1.size.fixed = SIZE
    f1.duration.fixed_packets.packets = PACKETS

    f1.metrics.enable = True
    f1.metrics.loss = True
    f1.metrics.timestamps = True

    # flow -f2 config
    f2 = b2b_raw_config.flows.flow(name="f2")[-1]
    f2.tx_rx.port.tx_name = tx_port.name
    f2.tx_rx.port.rx_name = rx_port.name

    f2.size.fixed = SIZE
    f2.duration.fixed_packets.packets = PACKETS

    f2.metrics.enable = True
    f2.metrics.loss = True

    # Latency Config
    f1.metrics.latency.enable = True
    f1.metrics.latency.mode = f1.metrics.latency.STORE_FORWARD

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: stats_ok(api, SIZE, PACKETS * 2, utils),
        "stats to be as expected",
    )

    _, flow_stats = utils.get_all_stats(api)

    # Validation
    for result in flow_stats:
        if result.name == "f1":
            latency = getattr(result, "latency")
            assert getattr(latency, "average_ns") is not None
            assert getattr(latency, "maximum_ns") is not None
            assert getattr(latency, "minimum_ns") is not None

            timestamps = getattr(result, "timestamps")
            assert getattr(timestamps, "first_timestamp_ns") is not None
            assert getattr(timestamps, "last_timestamp_ns") is not None
        if result.name == "f2":
            latency = getattr(result, "latency")
            assert getattr(latency, "average_ns") is None
            assert getattr(latency, "maximum_ns") is None
            assert getattr(latency, "minimum_ns") is None

            timestamps = getattr(result, "timestamps")
            assert getattr(timestamps, "first_timestamp_ns") is None
            assert getattr(timestamps, "last_timestamp_ns") is None


def stats_ok(api, size, packets, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    ok = utils.total_frames_ok(port_results, flow_results, packets)
    ok = ok and utils.total_bytes_ok(
        port_results, flow_results, packets * size
    )
    if utils.flow_transmit_matches(flow_results, "stopped") and not ok:
        raise Exception("Stats not ok after flows are stopped")

    return ok


if __name__ == "__main__":
    pytest.main(["-s", __file__])
