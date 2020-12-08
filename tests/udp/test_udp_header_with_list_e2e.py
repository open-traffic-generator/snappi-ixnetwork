import pytest
import utils
from abstract_open_traffic_generator import flow as Flow


@pytest.mark.e2e
def test_udp_header_with_list_e2e(api, b2b_raw_config):
    """
    Configure a raw udp flow with,
    - Non-default list values of src and dst Port address, length, checksum
    - 100 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    flow = b2b_raw_config.flows[0]
    packets = 100
    size = 74

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
                dst=Flow.Pattern("10.10.10.2")
            )
        ),
        Flow.Header(
            Flow.Udp(
                src_port=Flow.Pattern(["3000", "3001"]),
                dst_port=Flow.Pattern(["4000", "4001"]),
                length=Flow.Pattern(["35", "36"]),
                checksum=Flow.Pattern(["5", "6"])
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
    src = [3000, 3001]
    dst = [4000, 4001]
    length = [35, 36]
    checksum = [5, 6]
    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        packet_num = 0
        for packet in cap_dict[k]:
            assert utils.to_hex(packet[34:36]) == hex(src[packet_num])
            assert utils.to_hex(packet[36:38]) == hex(dst[packet_num])
            assert utils.to_hex(packet[38:40]) == hex(length[packet_num])
            assert utils.to_hex(packet[40:42]) == hex(checksum[packet_num])
            assert len(packet) == size
            packet_num = (packet_num + 1) % 2
