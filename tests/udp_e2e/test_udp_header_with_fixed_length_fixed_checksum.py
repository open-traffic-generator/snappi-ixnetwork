import pytest
import utils
from abstract_open_traffic_generator import flow as Flow


@pytest.mark.skip(reason="skip until moved to other repo")
@pytest.mark.parametrize('packets', [1000])
@pytest.mark.parametrize('size', [74])
def test_udp_header_with_fixed_length_fixed_checksum(api,
                                                     b2b_raw_config,
                                                     size,
                                                     packets):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address, length, checksum
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    flow = b2b_raw_config.flows[0]

    flow.packet = [
        Flow.Header(
            Flow.Ethernet(
                src=Flow.Pattern('00:0c:29:1d:10:67'),
                dst=Flow.Pattern('00:0c:29:1d:10:71')
                )
            ),
        Flow.Header(
            Flow.Ipv4(
                src=Flow.Pattern("10.10.10.1"),
                dst=Flow.Pattern("10.10.10.2"),
                )
            ),
        Flow.Header(
            Flow.Udp(
                src_port=Flow.Pattern("3000"),
                dst_port=Flow.Pattern("4000"),
                length=Flow.Pattern("38"),
                checksum=Flow.Pattern("5")
            )
        ),
    ]
    flow.duration = Flow.Duration(Flow.FixedPackets(packets=packets))
    flow.size = Flow.Size(size)
    flow.rate = Flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, size, packets), 'stats to be as expected'
    )

    captures_ok(api, b2b_raw_config, size)


def results_ok(api, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets)
    bytes_ok = utils.total_bytes_ok(port_results, flow_results, packets * size)
    return frames_ok and bytes_ok


def captures_ok(api, cfg, size):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src = 3000
    dst = 4000
    length = 38
    checksum = 5
    cap_dict = utils.get_all_captures(api, cfg)
    for k in cap_dict:
        for packet in cap_dict[k]:
            assert utils.to_hex(packet[36:38]) == hex(dst)
            assert utils.to_hex(packet[34:36]) == hex(src)
            assert utils.to_hex(packet[38:40]) == hex(length)
            assert utils.to_hex(packet[40:42]) == hex(checksum)
            assert len(packet) == size
