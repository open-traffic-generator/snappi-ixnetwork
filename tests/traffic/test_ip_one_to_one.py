
import pytest


@pytest.mark.e2e
def test_ip_device_and_flow(api, b2b_raw_config, utils):
    """
    Configure the devices on Tx and Rx Port.
    Configure the flow with devices as end points.
    run the traffic
    Validation,
    - validate the port and flow statistics.
    """

    size = 128
    packets = 100000
    count = 10
    mac_tx = utils.mac_or_ip_addr_from_counter_pattern(
        '00:10:10:20:20:10', '00:00:00:00:00:01', count, True
    )
    mac_rx = utils.mac_or_ip_addr_from_counter_pattern(
        '00:10:10:20:20:20', '00:00:00:00:00:01', count, False
    )
    ip_tx = utils.mac_or_ip_addr_from_counter_pattern(
        '10.1.1.1', '0.0.1.0', count, True, False
    )

    ip_rx = utils.mac_or_ip_addr_from_counter_pattern(
        '10.1.1.2', '0.0.1.0', count, True, False
    )

    addrs = {
        'mac_tx': mac_tx, 'mac_rx': mac_rx, 'ip_tx': ip_tx, 'ip_rx': ip_rx
    }

    # import snappi
    # b2b_raw_config = snappi.Api().config()

    for i in range(count * 2):
        port = int(i / count)
        node = 'tx' if port == 0 else 'rx'
        if i >= count:
            i = i - count
        dev = b2b_raw_config.devices.device()[-1]

        dev.name = '%s_dev_%d' % (node, i + 1)
        dev.container_name = b2b_raw_config.ports[port].name

        dev.ethernet.name = '%s_eth_%d' % (node, i + 1)
        dev.ethernet.mac = addrs['mac_%s' % node][i]

        dev.ethernet.ipv4.name = '%s_ipv4_%d' % (node, i + 1)
        dev.ethernet.ipv4.address = addrs['ip_%s' % node][i]
        dev.ethernet.ipv4.gateway = addrs[
            'ip_%s' % ('rx' if node == 'tx' else 'tx')
        ][i]
        dev.ethernet.ipv4.prefix = 24
    b2b_raw_config.flows.clear()
    f1, f2 = b2b_raw_config.flows.flow(name='TxFlow-1').flow(name='TxFlow-2')
    f1.tx_rx.device.tx_names = [
        b2b_raw_config.devices[i].name for i in range(count)
    ]
    f1.tx_rx.device.rx_names = [
        b2b_raw_config.devices[i + count].name for i in range(count)
    ]
    f1.tx_rx.device.mode = f1.tx_rx.device.ONE_TO_ONE
    f1.size.fixed = size
    f1.duration.fixed_packets.packets = packets
    f1.rate.percentage = "10"

    f2.tx_rx.device.tx_names = [
        b2b_raw_config.devices[i].name for i in range(count)
    ]
    f2.tx_rx.device.rx_names = [
        b2b_raw_config.devices[i + count].name for i in range(count)
    ]
    f2.tx_rx.device.mode = f1.tx_rx.device.ONE_TO_ONE
    f2.packet.ethernet().ipv4().tcp()
    tcp = f2.packet[-1]
    tcp.src_port.increment.start = "5000"
    tcp.src_port.increment.step = "1"
    tcp.src_port.increment.count = "%d" % count
    tcp.dst_port.increment.start = "2000"
    tcp.dst_port.increment.step = "1"
    tcp.dst_port.increment.count = "%d" % count
    f2.size.fixed = size * 2
    f2.duration.fixed_packets.packets = packets
    f2.rate.percentage = "10"
    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, utils, size, size * 2, packets),
        'stats to be as expected', timeout_seconds=20
    )
    utils.stop_traffic(api, b2b_raw_config)
    captures_ok(api, b2b_raw_config, utils, count, packets * 2)


def results_ok(api, utils, size1, size2, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets * 2)
    bytes_ok = utils.total_bytes_ok(
        port_results, flow_results, packets * size1 + packets * size2
    )
    return frames_ok and bytes_ok


def captures_ok(api, cfg, utils, count, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x10 + i] for i in range(count)]
    dst_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x20 - i] for i in range(count)]

    src_ip = [[0x0a, 0x01, 0x01 + i, 0x01] for i in range(count)]
    dst_ip = [[0x0a, 0x01, 0x01 + i, 0x02] for i in range(count)]

    src_port = [[0x13, 0x88 + i] for i in range(count)]
    dst_port = [[0x07, 0xd0 + i] for i in range(count)]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1
    sizes = [128, 256]
    size_dt = {
        128: [0 for i in range(count)],
        256: [0 for i in range(count)]
    }
    for b in cap_dict[list(cap_dict.keys())[0]]:
        i = dst_mac.index(b[0:6])
        assert b[0:6] == dst_mac[i] and b[6:12] == src_mac[i]
        assert b[26:30] == src_ip[i] and b[30:34] == dst_ip[i]
        assert len(b) in sizes
        size_dt[len(b)][i] += 1
        if len(b) == 256:
            assert b[34:36] == src_port[i] and b[36:38] == dst_port[i]

    assert sum(size_dt[128]) + sum(size_dt[256]) == packets
