import pytest
import utils
from abstract_open_traffic_generator import flow


@pytest.mark.skip(reason="skipped till move to other repo")
@pytest.mark.parametrize('packets', [1])
@pytest.mark.parametrize('size', [74])
def test_udp_fixed_ports(api, b2b_raw_config, size, packets):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    f = b2b_raw_config.flows[0]

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern('00:0c:29:1d:10:67'),
                dst=flow.Pattern('00:0c:29:1d:10:71')
            )
        ),
        flow.Header(
            flow.Ipv4(
                src=flow.Pattern("10.10.10.1"),
                dst=flow.Pattern("10.10.10.2")
            )
        ),
        flow.Header(
            flow.Udp(
                src_port=flow.Pattern("3000"),
                dst_port=flow.Pattern("4000")
            )
        ),
    ]
    f.duration = flow.Duration(flow.FixedPackets(packets=packets))
    f.size = flow.Size(size)
    f.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: stats_ok(api, size, packets), 'stats to be as expected'
    )

    captures_ok(api, b2b_raw_config, size)


def stats_ok(api, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    ok = utils.total_frames_ok(port_results, flow_results, packets)
    ok = ok and utils.total_bytes_ok(
        port_results, flow_results, packets * size
    )
    if utils.flow_transmit_matches(flow_results, 'stopped') and not ok:
        raise Exception('Stats not ok after flows are stopped')

    return ok


def captures_ok(api, cfg, size):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    dst = [0x0F, 0xA0]
    src = [0x0B, 0xB8]
    cap_dict = utils.get_all_captures(api, cfg)
    for k in cap_dict:
        for b in cap_dict[k]:
            assert b[36:38] == dst or b[34:36] == src
            assert len(b) == size
