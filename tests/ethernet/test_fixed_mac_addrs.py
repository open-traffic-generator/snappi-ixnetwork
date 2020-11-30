from abstract_open_traffic_generator import flow
import utils


def test_fixed_mac_addrs(api, settings, b2b_raw_config):
    """
    Configure a raw ethernet flow with,
    - fixed src and dst MAC address
    - 100 frames of 1518B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst MAC address
    """
    f = b2b_raw_config.flows[0]
    size = 1518
    packets = 100

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                dst=flow.Pattern('00:AB:BC:AB:BC:AB')
            )
        )
    ]
    f.duration = flow.Duration(flow.FixedPackets(packets=packets))
    f.size = flow.Size(size)
    f.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: stats_ok(api, size, packets), 'stats to be as expected'
    )

    captures_ok(api, b2b_raw_config, size, packets)


def stats_ok(api, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    frames_ok = utils.total_frames_ok(port_results, flow_results, packets)
    bytes_ok = utils.total_bytes_ok(port_results, flow_results, packets * size)
    ok = frames_ok and bytes_ok

    if utils.flow_transmit_matches(flow_results, 'stopped') and not ok:
        raise Exception('Stats not ok after flows are stopped')

    return ok


def captures_ok(api, cfg, size, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    dst = [0x00, 0xAB, 0xBC, 0xAB, 0xBC, 0xAB]
    src = [0x00, 0xCD, 0xDC, 0xCD, 0xDC, 0xCD]
    cap_dict = utils.get_all_captures(api, cfg)
    for k in cap_dict:
        for b in cap_dict[k]:
            assert b[0:6] == dst and b[6:12] == src
            assert len(b) == size
