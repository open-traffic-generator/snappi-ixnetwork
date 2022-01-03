import pytest


@pytest.mark.e2e
def test_vxlan_e2e(api, b2b_raw_config, utils):
    """
    Configure a raw vxlan flow with,
    - fixed src and dst Port address
    - 1 frames of 128B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    api.set_config(api.config())
    f = b2b_raw_config.flows[0]
    f.metrics.enable = True
    packets = 1
    size = 128

    outer_eth, ip, udp, vxlan, inner_eth = (
        f.packet.ethernet().ipv4().udp().vxlan().ethernet()
    )

    outer_eth.src.value = "00:00:0a:00:00:01"
    outer_eth.dst.value = "00:00:0b:00:00:02"
    outer_eth.ether_type.value = 2048

    ip.src.value = "200.1.1.1"
    ip.dst.value = "100.1.1.1"

    udp.src_port.value = 3000
    udp.dst_port.value = 4789
    udp.length.value = 90

    vxlan.flags.value = 255
    vxlan.vni.value = 2000

    inner_eth.src.value = "00:00:0c:00:00:03"
    inner_eth.dst.value = "00:00:0d:00:00:04"

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
    flags = 0xFF
    vni = [0x00, 0x07, 0xD0]
    cap_dict = utils.get_all_captures(api, cfg)
    for k in cap_dict:
        for b in cap_dict[k]:
            assert b[42] == flags and b[46:49] == vni
            assert len(b) == size
