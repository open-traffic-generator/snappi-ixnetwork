import pytest


def test_flow_metrics(api, utils, b2b_raw_config, tx_port, rx_port):
    """This is a test script to test flow metrics,
    metrics should be available only for the flows metrics are enabled

    1. Create two flows f1&f2
    2. f1 with TCP and metrics enabled
    3. f2 with UDP and metrics to default, i.e disabled

    Validation:
    - Check flow stats and check we don't get metrics for f2
    """
    SIZE = 1024
    PACKETS = 1000

    f1 = b2b_raw_config.flows[0]

    f1.packet.ethernet().ipv4().tcp()
    f1.size.fixed = SIZE
    f1.duration.fixed_packets.packets = PACKETS

    f1.metrics.enable = True
    f1.metrics.loss = True

    # flow -f2 config(with UDP)
    f2 = b2b_raw_config.flows.flow(name='f2')[-1]
    f2.tx_rx.port.tx_name = tx_port.name
    f2.tx_rx.port.rx_name = rx_port.name

    f2.packet.ethernet().ipv4().udp()
    f2.size.fixed = SIZE
    f2.duration.fixed_packets.packets = PACKETS

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: stats_ok(api, PACKETS, utils), 'stats to be as expected'
    )

    _, flow_stats = utils.get_all_stats(api)

    # Validation
    for result in flow_stats:
        assert result.name != 'f2'


def stats_ok(api, packets, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    _, flow_stats = utils.get_all_stats(api)

    flow_rx = sum([f.frames_rx for f in flow_stats])
    return flow_rx == packets


if __name__ == '__main__':
    pytest.main(['-s', __file__])

