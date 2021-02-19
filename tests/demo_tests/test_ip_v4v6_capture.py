import pytest
import snappi


@pytest.fixture
def app_intf(utils):
    api = snappi.api(host=utils.settings.api_server, ext=utils.settings.ext)
    yield api
    if getattr(api, 'assistant', None) is not None:
        api.assistant.Session.remove()


@pytest.mark.e2e
def test_ip_v4v6_capture(app_intf, utils):
    """
    Test to demonstrate ipv4 and ipv6 device and raw type traffic
    configuration, transmit, statistics and capture.
    """
    config = app_intf.config()

    size = 128
    packets = 1000
    src = '00:10:10:20:20:10'
    dst = '00:10:10:20:20:20'
    mac_step = '00:00:00:00:00:01'

    src_ipv4 = '10.1.1.1'
    dst_ipv4 = '10.1.1.2'
    ipv4_step = '0.0.1.0'

    src_ipv6 = 'abcd::1a'
    dst_ipv6 = 'abcd::2a'
    ipv6_step = '1::'

    ##############################
    # Ports configuration
    ##############################
    tx, rx = (
        config.ports
        .port(name='tx', location=utils.settings.ports[0])
        .port(name='rx', location=utils.settings.ports[1])
    )
    l1 = config.layer1.layer1()[-1]
    l1.name = 'L1 Settings'
    l1.port_names = [tx.name, rx.name]
    l1.speed = utils.settings.speed
    l1.media = utils.settings.media

    cap = config.captures.capture(name='c1')[-1]
    cap.port_names = [rx.name]
    cap.format = cap.PCAP

    ##############################
    # Device configuration
    ##############################
    tx_dev, rx_dev = config.devices.device().device()
    tx_dev.name = 'tx_dev'
    rx_dev.name = 'rx_dev'
    tx_dev.container_name = tx.name
    rx_dev.container_name = rx.name
    tx_dev.device_count = 10
    rx_dev.device_count = 10
    tx_eth = tx_dev.ethernet
    rx_eth = rx_dev.ethernet

    tx_eth.name = "tx_eth"
    tx_eth.mac.increment.start = src
    tx_eth.mac.increment.step = mac_step

    tx_ipv4 = tx_eth.ipv4
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address.increment.start = src_ipv4
    tx_ipv4.address.increment.step = ipv4_step
    tx_ipv4.gateway.increment.start = dst_ipv4
    tx_ipv4.gateway.increment.step = ipv4_step
    tx_ipv4.prefix.value = 24
    tx_ipv6 = tx_eth.ipv6
    tx_ipv6.name = "tx_ipv6"
    tx_ipv6.address.increment.start = src_ipv6
    tx_ipv6.address.increment.step = ipv6_step
    tx_ipv6.gateway.increment.start = dst_ipv6
    tx_ipv6.gateway.increment.step = ipv6_step
    tx_ipv6.prefix.value = 48

    rx_eth.name = "rx_eth"
    rx_eth.mac.decrement.start = dst
    rx_eth.mac.decrement.step = mac_step

    rx_ipv4 = rx_eth.ipv4
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address.increment.start = dst_ipv4
    rx_ipv4.address.increment.step = ipv4_step
    rx_ipv4.gateway.increment.start = src_ipv4
    rx_ipv4.gateway.increment.step = ipv4_step
    rx_ipv4.prefix.value = 24
    rx_ipv6 = rx_eth.ipv6
    rx_ipv6.name = "rx_ipv6"
    rx_ipv6.address.increment.start = dst_ipv6
    rx_ipv6.address.increment.step = ipv6_step
    rx_ipv6.gateway.increment.start = src_ipv6
    rx_ipv6.gateway.increment.step = ipv6_step
    rx_ipv6.prefix.value = 48

    ##############################
    # Flows configuration
    ##############################
    f1, f2, f3, f4 = (
        config.flows
        .flow(name='FlowIpv4Device')
        .flow(name='FlowIpv6Device')
        .flow(name='FlowIpv4Raw')
        .flow(name='FlowIpv6Raw')
    )
    f1.tx_rx.device.tx_names = [tx_ipv4.name]
    f1.tx_rx.device.rx_names = [rx_ipv4.name]
    f1.size.fixed = size
    f1.duration.fixed_packets.packets = packets
    f1.rate.percentage = 10

    f2.tx_rx.device.tx_names = [tx_ipv6.name]
    f2.tx_rx.device.rx_names = [rx_ipv6.name]
    f2.size.fixed = size
    f2.duration.fixed_packets.packets = packets
    f2.rate.percentage = 10

    f3.tx_rx.port.tx_name = tx.name
    f3.tx_rx.port.rx_name = rx.name
    f3.packet.ethernet().ipv4()
    eth = f3.packet[0]
    ipv4 = f3.packet[1]
    eth.src.increment.start = src
    eth.src.increment.step = mac_step
    eth.src.increment.count = 10
    eth.dst.decrement.start = dst
    eth.dst.decrement.step = mac_step
    eth.dst.decrement.count = 10
    ipv4.src.increment.start = src_ipv4
    ipv4.src.increment.step = ipv4_step
    ipv4.src.increment.count = 10
    ipv4.dst.increment.start = dst_ipv4
    ipv4.dst.increment.step = ipv4_step
    ipv4.dst.increment.count = 10
    f3.size.fixed = size
    f3.duration.fixed_packets.packets = packets

    f4.tx_rx.port.tx_name = tx.name
    f4.tx_rx.port.rx_name = rx.name
    f4.packet.ethernet().ipv6()
    eth = f4.packet[0]
    ipv6 = f4.packet[1]
    eth.src.increment.start = src
    eth.src.increment.step = mac_step
    eth.src.increment.count = 10
    eth.dst.decrement.start = dst
    eth.dst.decrement.step = mac_step
    eth.dst.decrement.count = 10
    ipv6.src.increment.start = src_ipv6
    ipv6.src.increment.step = ipv6_step
    ipv6.src.increment.count = 10
    ipv6.dst.increment.start = dst_ipv6
    ipv6.dst.increment.step = ipv6_step
    ipv6.dst.increment.count = 10
    f4.size.fixed = size
    f4.duration.fixed_packets.packets = packets

    ##############################
    # Starting transmit on flows
    ##############################
    utils.start_traffic(app_intf, config)

    ##############################
    # Analyzing Traffic metrics
    ##############################
    print('Analyzing flow and port metrics ...')
    utils.wait_for(
        lambda: results_ok(app_intf, utils, size, packets * 4),
        'stats to be as expected', timeout_seconds=10
    )

    ##############################
    # Stopping transmit on flows
    ##############################
    print('Stopping transmit ...')
    utils.stop_traffic(app_intf, config)

    captures_ok(app_intf, config, utils, packets * 4)


def results_ok(api, utils, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets)
    bytes_ok = utils.total_bytes_ok(
        port_results, flow_results, packets * size
    )
    return frames_ok and bytes_ok


def captures_ok(api, cfg, utils, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x10 + i] for i in range(10)]
    dst_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x20 - i] for i in range(10)]
    src_ip = [[0x0a, 0x01, 0x01 + i, 0x01] for i in range(10)]
    dst_ip = [[0x0a, 0x01, 0x01 + i, 0x02] for i in range(10)]
    src_ip6 = [
        [
            0xab, 0xcd + i, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1a
        ]
        for i in range(10)
    ]
    dst_ip6 = [
        [
            0xab, 0xcd + i, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x2a
        ]
        for i in range(10)
    ]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1
    size = 128
    size_dt = {
        128: [0 for i in range(10)]
    }

    for index, b in enumerate(cap_dict[list(cap_dict.keys())[0]]):
        try:
            i = dst_mac.index(b[0:6])
        except Exception:
            continue
        assert b[0:6] == dst_mac[i] and b[6:12] == src_mac[i]
        if b[14] == 0x45:
            assert b[26:30] == src_ip[i] and b[30:34] == dst_ip[i]
        else:
            assert b[22:38] == src_ip6[i] and b[38:54] == dst_ip6[i]
        assert len(b) == size
        size_dt[len(b)][i] += 1

    assert sum(size_dt[128]) == packets
