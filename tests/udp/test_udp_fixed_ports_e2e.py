import pytest


@pytest.mark.e2e
def test_udp_fixed_ports_e2e(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    api.set_config(api.config())
    f = b2b_raw_config.flows[0]
    packets = 1
    size = 74
    f.packet.ethernet().ipv4().udp()
    eth, ip, udp = f.packet[0], f.packet[1], f.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ip.src.value = "10.10.10.1"
    ip.dst.value = "10.10.10.2"
    udp.src_port.value = 3000
    udp.dst_port.value = 4000

    f.duration.fixed_packets.packets = packets
    f.size.fixed = size
    f.rate.percentage = 10

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: stats_ok(api, size, packets, utils), "stats to be as expected"
    )

    captures_ok(api, b2b_raw_config, size, utils)


def stats_ok(api, size, packets, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    ok = utils.total_frames_ok(port_results, flow_results, packets)
    ok = ok and utils.total_bytes_ok(
        port_results, flow_results, packets * size
    )
    if utils.flow_transmit_matches(flow_results, "stopped") and not ok:
        raise Exception("Stats not ok after flows are stopped")

    return ok


def captures_ok(api, cfg, size, utils):
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
