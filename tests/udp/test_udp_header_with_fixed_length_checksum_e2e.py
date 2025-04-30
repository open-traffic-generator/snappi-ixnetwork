def test_udp_header_with_fixed_length_checksum_e2e(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address, length, checksum
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    f = b2b_raw_config.flows[0]
    packets = 1000
    size = 74

    f.packet.ethernet().ipv4().udp()
    eth, ip, udp = f.packet[0], f.packet[1], f.packet[2]

    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ip.src.value = "10.10.10.1"
    ip.dst.value = "10.10.10.2"
    udp.src_port.value = 3000
    udp.dst_port.value = 4000
    udp.length.value = 38
    udp.checksum.custom = 5

    f.duration.fixed_packets.packets = packets
    f.size.fixed = size
    f.rate.percentage = 10

    f.metrics.enable = True

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
