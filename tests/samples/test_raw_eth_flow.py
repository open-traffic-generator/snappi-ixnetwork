import pytest

from abstract_open_traffic_generator import flow
import utils


@pytest.mark.parametrize('size', [64, 128, 1518])
@pytest.mark.parametrize('packets', [1000])
def test_raw_eth_flow(api, settings, b2b_raw_config, size, packets):
    """
    Configure a raw ethernet flow with,
    - fixed src and dst MAC address
    - 1000 frames of 128B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst MAC address
    """
    f = b2b_raw_config.flows[0]

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern('00:00:00:00:00:0b'),
                dst=flow.Pattern('00:00:00:00:00:0a')
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

    ok = utils.total_frames_ok(port_results, flow_results, packets)
    if utils.flow_transmit_matches(flow_results, 'stopped') and not ok:
        raise Exception('Stats not ok after flows are stopped')

    return ok


def captures_ok(api, cfg, size, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    dst = [0x00, 0x00, 0x00, 0x00, 0x00, 0x0A]
    src = [0x00, 0x00, 0x00, 0x00, 0x00, 0x0B]
    cap_dict = utils.get_all_captures(api, cfg)
    for k in cap_dict:
        for b in cap_dict[k]:
            assert b[0:6] == dst or b[6:12] == src
            assert len(b) == size
