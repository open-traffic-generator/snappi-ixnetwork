import pytest


@pytest.mark.e2e
def test_list_tcp_ports_e2e(api, utils, b2b_raw_config):
    """
    Configure a raw TCP flow with,
    - list of 6 src ports and 3 dst ports
    - 100 frames of 1518B size each
    - 10% line rate
    Validate,
    - tx/rx frame count and bytes are as expected
    - all captured frames have expected src and dst ports
    """
    api.set_config(api.config())
    f = b2b_raw_config.flows[0]
    size = 1518
    packets = 100
    f.packet.ethernet().ipv4().tcp()
    eth, ip, tcp = f.packet[0], f.packet[1], f.packet[2]
    eth.src.value = '00:CD:DC:CD:DC:CD'
    eth.dst.value = '00:AB:BC:AB:BC:AB'
    ip.src.value = '1.1.1.2'
    ip.dst.value = '1.1.1.1'
    tcp.src_port.values = [5000, 5050, 5015, 5040, 5032, 5021]
    tcp.dst_port.values = [6000, 6015, 6050]
    f.duration.fixed_packets.packets = packets
    f.size.fixed = size
    f.rate.percentage = 10
    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, utils, size, packets),
        'stats to be as expected', timeout_seconds=10
    )
    captures_ok(api, b2b_raw_config, size, utils)


def results_ok(api, utils, size, packets):
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
    src = [
        [0x13, 0x88], [0x13, 0xBA], [0x13, 0x97], [0x13, 0xB0], [0x13, 0xA8],
        [0x13, 0x9D]
    ]
    dst = [[0x17, 0x70], [0x17, 0x7F], [0x17, 0xA2]]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        i = 0
        j = 0
        for b in cap_dict[k]:
            assert b[34:36] == src[i] and b[36:38] == dst[j]
            i = (i + 1) % 6
            j = (j + 1) % 3
            assert len(b) == size
