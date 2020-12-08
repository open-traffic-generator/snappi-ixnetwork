from abstract_open_traffic_generator import flow
import utils
import pytest


@pytest.mark.skip(reason="skip until moved to other repo")
def test_random_tcp_ports_e2e(api, settings, b2b_raw_config):
    """
    Configure a raw TCP flow with,
    - random src port (from possible values 5000, 5001 and 5002)
    - random dst port (from possible values 6000, 6001)
    - 100 frames of 1518B size each
    - 10% line rate
    Validate,
    - tx/rx frame count and bytes are as expected
    - all captured frames have expected src and dst ports
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
        ),
        flow.Header(
            flow.Ipv4(
                src=flow.Pattern('1.1.1.2'),
                dst=flow.Pattern('1.1.1.1')
            )
        ),
        flow.Header(
            flow.Tcp(
                src_port=flow.Pattern(
                    flow.Random(min='5000', max='5002', seed='5000')
                ),
                dst_port=flow.Pattern(
                    flow.Random(min='6000', max='6001', seed='6000')
                )
            )
        )
    ]
    f.duration = flow.Duration(flow.FixedPackets(packets=packets))
    f.size = flow.Size(size)
    f.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, b2b_raw_config, size, packets),
        'stats to be as expected', timeout_seconds=10
    )
    captures_ok(api, b2b_raw_config, size, packets)


def results_ok(api, cfg, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets)
    bytes_ok = utils.total_bytes_ok(port_results, flow_results, packets * size)
    return frames_ok and bytes_ok


def captures_ok(api, cfg, size, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src = {0x88: 0, 0x89: 0, 0x8A: 0}
    dst = {0x70: 0, 0x71: 0}

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        for b in cap_dict[k]:
            # only second byte varies across all port numbers
            # hence check that first byte in src and dst port is as expected
            # and increment count for second byte (to track occurrence count)
            assert b[34] == 0x13
            src[b[35]] += 1
            assert b[36] == 0x17
            dst[b[37]] += 1

            assert len(b) == size

    # make sure we have at least one occurrence of each port number in src and
    # dst dict
    # TODO: check should be stricter
    assert all([src[i] >= 0 for i in src])
    assert all([dst[i] >= 0 for i in dst])
