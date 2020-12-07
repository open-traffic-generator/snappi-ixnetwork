import pytest
import utils
from abstract_open_traffic_generator import flow as Flow


@pytest.mark.skip(reason="skip until moved to other repo")
@pytest.mark.parametrize('packets', [100])
@pytest.mark.parametrize('size', [74])
def test_udp_header_with_counter(api, b2b_raw_config, size, packets):
    """
    Configure a raw udp flow with,
    - Non-default Counter Pattern values of src and
      dst Port address, length, checksum
    - 100 frames of 74B size each
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
                dst=Flow.Pattern("10.10.10.2")
            )
        ),
        Flow.Header(
            Flow.Udp(
                src_port=Flow.Pattern(
                    Flow.Counter(start='5000', step='2', count=10)
                ),
                dst_port=Flow.Pattern(
                    Flow.Counter(start='6000', step='2', count=10, up=False)
                ),
                length=Flow.Pattern(
                    Flow.Counter(start="35", step="1", count=2)
                ),
                checksum=Flow.Pattern(
                    Flow.Counter(start="6", step="1", count=2)
                )
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
    src = [src_port for src_port in range(5000, 5020, 2)]
    dst = [dst_port for dst_port in range(6000, 5980, -2)]
    length = [35, 36]
    checksum = [6, 7]
    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        i = 0
        j = 0
        for packet in cap_dict[k]:
            assert utils.to_hex(packet[34:36]) == hex(src[i])
            assert utils.to_hex(packet[36:38]) == hex(dst[i])
            assert utils.to_hex(packet[38:40]) == hex(length[j])
            assert utils.to_hex(packet[40:42]) == hex(checksum[j])
            assert len(packet) == size
            i = (i + 1) % 10
            j = (j + 1) % 2
