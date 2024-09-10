import pytest


@pytest.mark.e2e
def test_udp_header_with_counter_e2e(api, b2b_raw_config, utils):
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
    api.set_config(api.config())
    flow = b2b_raw_config.flows[0]
    packets = 100
    size = 74
    flow.packet.ethernet().ipv4().udp()
    eth, ip, udp = flow.packet[0], flow.packet[1], flow.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ip.src.value = "10.10.10.1"
    ip.dst.value = "10.10.10.2"
    udp.src_port.increment.start = 5000
    udp.src_port.increment.step = 2
    udp.src_port.increment.count = 10
    udp.dst_port.decrement.start = 6000
    udp.dst_port.decrement.step = 2
    udp.dst_port.decrement.count = 10
    udp.length.increment.start = 35
    udp.length.increment.step = 1
    udp.length.increment.count = 2
    udp.checksum.GOOD
    flow.duration.fixed_packets.packets = packets
    flow.size.fixed = size
    flow.rate.percentage = 10
    flow.metrics.enable = True

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, size, packets, utils),
        "stats to be as expected",
    )

    captures_ok(api, b2b_raw_config, size, utils)


def results_ok(api, size, packets, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets)
    bytes_ok = utils.total_bytes_ok(port_results, flow_results, packets * size)
    return frames_ok and bytes_ok


def captures_ok(api, cfg, size, utils):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src = [src_port for src_port in range(5000, 5020, 2)]
    dst = [dst_port for dst_port in range(6000, 5980, -2)]
    length = [35, 36]
    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        i = 0
        j = 0
        for packet in cap_dict[k]:
            assert utils.to_hex(packet[34:36]) == hex(src[i])
            assert utils.to_hex(packet[36:38]) == hex(dst[i])
            assert utils.to_hex(packet[38:40]) == hex(length[j])
            assert len(packet) == size
            i = (i + 1) % 10
            j = (j + 1) % 2
