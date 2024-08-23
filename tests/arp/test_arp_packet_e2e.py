import pytest


@pytest.mark.e2e
def test_arp_packet_e2e(api, utils, b2b_raw_config):
    """
    Configure a raw TCP flow with,
    - sender_hardware_addr increase from 00:0c:29:e3:53:ea with count 5
    - target_hardware_addr decrement from 00:0C:29:E3:54:EA with count 5
    - 100 frames of 1518B size each
    - 10% line rate
    Validate,
    - tx/rx frame count and bytes are as expected
    - all captured frames have expected sender_hardware_addr and
      target_hardware_addr
    """
    api.set_config(api.config())
    flow1 = b2b_raw_config.flows[0]
    size = 1518
    packets = 100
    sender_hardware_addr = "00:0C:29:E3:53:EA"
    target_hardware_addr = "00:0C:30:E3:54:EA"
    sender_protocol_addr = "10.1.1.2"
    target_protocol_addr = "20.1.1.5"
    mac_step = "00:00:00:00:01:00"
    ip_step = "0.0.0.1"
    count = 5
    flow1.packet.ethernet().arp()
    flow_arp = flow1.packet[-1]
    flow_arp.sender_hardware_addr.increment.start = sender_hardware_addr
    flow_arp.sender_hardware_addr.increment.step = mac_step
    flow_arp.sender_hardware_addr.increment.count = count
    flow_arp.sender_protocol_addr.increment.start = sender_protocol_addr
    flow_arp.sender_protocol_addr.increment.step = ip_step
    flow_arp.sender_protocol_addr.increment.count = count
    flow_arp.target_hardware_addr.decrement.start = target_hardware_addr
    flow_arp.target_hardware_addr.decrement.step = mac_step
    flow_arp.target_hardware_addr.decrement.count = count
    flow_arp.target_protocol_addr.decrement.start = target_protocol_addr
    flow_arp.target_protocol_addr.decrement.step = ip_step
    flow_arp.target_protocol_addr.decrement.count = count

    flow1.duration.fixed_packets.packets = packets
    flow1.size.fixed = size
    flow1.rate.percentage = 10
    flow1.metrics.enable = True
    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, utils, size, packets),
        "stats to be as expected",
        timeout_seconds=30,
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
    sender_hardware_addr = [
        [0x00, 0x0C, 0x29, 0xE3, 0x53, 0xEA],
        [0x00, 0x0C, 0x29, 0xE3, 0x54, 0xEA],
        [0x00, 0x0C, 0x29, 0xE3, 0x55, 0xEA],
        [0x00, 0x0C, 0x29, 0xE3, 0x56, 0xEA],
        [0x00, 0x0C, 0x29, 0xE3, 0x57, 0xEA],
    ]
    target_hardware_addr = [
        [0x00, 0x0C, 0x30, 0xE3, 0x54, 0xEA],
        [0x00, 0x0C, 0x30, 0xE3, 0x53, 0xEA],
        [0x00, 0x0C, 0x30, 0xE3, 0x52, 0xEA],
        [0x00, 0x0C, 0x30, 0xE3, 0x51, 0xEA],
        [0x00, 0x0C, 0x30, 0xE3, 0x50, 0xEA],
    ]
    sender_protocol_addr = [
        [0x0A, 0x01, 0x01, 0x02],
        [0x0A, 0x01, 0x01, 0x03],
        [0x0A, 0x01, 0x01, 0x04],
        [0x0A, 0x01, 0x01, 0x05],
        [0x0A, 0x01, 0x01, 0x06],
    ]
    target_protocol_addr = [
        [0x14, 0x01, 0x01, 0x05],
        [0x14, 0x01, 0x01, 0x04],
        [0x14, 0x01, 0x01, 0x03],
        [0x14, 0x01, 0x01, 0x02],
        [0x14, 0x01, 0x01, 0x01],
    ]
    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        i = 0
        for b in cap_dict[k]:
            assert b[22:28] == sender_hardware_addr[i]
            assert b[28:32] == sender_protocol_addr[i]
            assert b[32:38] == target_hardware_addr[i]
            assert b[38:42] == target_protocol_addr[i]
            i = (i + 1) % 5
            assert len(b) == size


if __name__ == "__main__":
    pytest.main(["-s", __file__])
