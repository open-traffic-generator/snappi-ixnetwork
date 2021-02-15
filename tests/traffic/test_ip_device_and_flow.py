
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
    tx_dev, rx_dev = b2b_raw_config.devices.device().device()
    tx_dev.name = 'tx_dev'
    rx_dev.name = 'rx_dev'
    tx_dev.container_name = b2b_raw_config.ports[0].name
    rx_dev.container_name = b2b_raw_config.ports[1].name
    tx_dev.device_count = 10
    rx_dev.device_count = 10
    tx_eth = tx_dev.ethernet
    rx_eth = rx_dev.ethernet
    tx_eth.name = "tx_eth"
    tx_eth.mac.increment.start = '00:10:10:20:20:10'
    tx_eth.mac.increment.step = '00:00:00:00:00:01'
    tx_ipv4 = tx_eth.ipv4
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address.increment.start = '10.1.1.1'
    tx_ipv4.address.increment.step = '0.0.1.0'
    tx_ipv4.gateway.increment.start = '10.1.1.2'
    tx_ipv4.gateway.increment.step = '0.0.1.0'
    tx_ipv4.prefix.value = "24"

    rx_eth.name = "rx_eth"
    rx_eth.mac.decrement.start = '00:10:10:20:20:20'
    rx_eth.mac.decrement.step = '00:00:00:00:00:01'
    rx_ipv4 = rx_eth.ipv4
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address.increment.start = '10.1.1.2'
    rx_ipv4.address.increment.step = '0.0.1.0'
    rx_ipv4.gateway.increment.start = '10.1.1.1'
    rx_ipv4.gateway.increment.step = '0.0.1.0'
    rx_ipv4.prefix.value = "24"

    f1, f2 = b2b_raw_config.flows.flow(name='TxFlow-2')
    f1.name = 'TxFlow-1'
    f1.tx_rx.device.tx_names = [tx_dev.name]
    f1.tx_rx.device.rx_names = [rx_dev.name]
    f1.size.fixed = size
    f1.duration.fixed_packets.packets = packets
    f1.rate.percentage = "10"

    f2.tx_rx.device.tx_names = [tx_dev.name]
    f2.tx_rx.device.rx_names = [rx_dev.name]
    f2.packet.ethernet().ipv4().tcp()
    tcp = f2.packet[-1]
    tcp.src_port.increment.start = "5000"
    tcp.src_port.increment.step = "1"
    tcp.src_port.increment.count = "10"
    tcp.dst_port.increment.start = "2000"
    tcp.dst_port.increment.step = "1"
    tcp.dst_port.increment.count = "10"
    f2.size.fixed = size * 2
    f2.duration.fixed_packets.packets = packets
    f2.rate.percentage = "10"

    utils.start_traffic(api, b2b_raw_config)

    utils.wait_for(
        lambda: results_ok(api, utils, size, size * 2, packets),
        'stats to be as expected', timeout_seconds=10
    )
    utils.stop_traffic(api, b2b_raw_config)
    captures_ok(api, b2b_raw_config, utils, packets * 2)


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


def captures_ok(api, cfg, utils, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x10 + i] for i in range(10)]
    dst_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x20 - i] for i in range(10)]

    src_ip = [
        [0x0a, 0x01, 0x01, 0x01], [0x0a, 0x01, 0x02, 0x01],
        [0x0a, 0x01, 0x03, 0x01], [0x0a, 0x01, 0x04, 0x01],
        [0x0a, 0x01, 0x05, 0x01], [0x0a, 0x01, 0x06, 0x01],
        [0x0a, 0x01, 0x07, 0x01], [0x0a, 0x01, 0x08, 0x01],
        [0x0a, 0x01, 0x09, 0x01], [0x0a, 0x01, 0x0a, 0x01]
    ]
    dst_ip = [
        [0x0a, 0x01, 0x01, 0x02], [0x0a, 0x01, 0x02, 0x02],
        [0x0a, 0x01, 0x03, 0x02], [0x0a, 0x01, 0x04, 0x02],
        [0x0a, 0x01, 0x05, 0x02], [0x0a, 0x01, 0x06, 0x02],
        [0x0a, 0x01, 0x07, 0x02], [0x0a, 0x01, 0x08, 0x02],
        [0x0a, 0x01, 0x09, 0x02], [0x0a, 0x01, 0x0a, 0x02]
    ]

    src_port = [[0x13, 0x88 + i] for i in range(10)]
    dst_port = [[0x07, 0xd0 + i] for i in range(10)]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1
    sizes = [128, 256]
    size_dt = {
        128: [0 for i in range(10)],
        256: [0 for i in range(10)]
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
