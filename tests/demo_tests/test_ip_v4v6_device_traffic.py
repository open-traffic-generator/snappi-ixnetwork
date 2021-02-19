import pytest
import snappi


@pytest.fixture
def app_intf(utils):
    api = snappi.api(host=utils.settings.api_server, ext=utils.settings.ext)
    yield api
    if getattr(api, 'assistant', None) is not None:
        api.assistant.Session.remove()


@pytest.mark.e2e
def test_ip_v4v6_device_traffic(app_intf, utils):
    """
    Test to demonstrate ipv4 and ipv6 device traffic
    configuration, transmit and statistics.
    """
    config = app_intf.config()
    size = 128
    packets = 100000

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
    tx_eth.mac.increment.start = '00:10:10:20:20:10'
    tx_eth.mac.increment.step = '00:00:00:00:00:01'

    tx_ipv4 = tx_eth.ipv4
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address.increment.start = '10.1.1.1'
    tx_ipv4.address.increment.step = '0.0.1.0'
    tx_ipv4.gateway.increment.start = '10.1.1.2'
    tx_ipv4.gateway.increment.step = '0.0.1.0'
    tx_ipv4.prefix.value = "24"
    tx_ipv6 = tx_eth.ipv6
    tx_ipv6.name = "tx_ipv6"
    tx_ipv6.address.increment.start = 'abcd::1a'
    tx_ipv6.address.increment.step = '1::'
    tx_ipv6.gateway.increment.start = 'abcd::2a'
    tx_ipv6.gateway.increment.step = '1::'
    tx_ipv6.prefix.value = "48"

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
    rx_ipv6 = rx_eth.ipv6
    rx_ipv6.name = "rx_ipv6"
    rx_ipv6.address.increment.start = 'abcd::2a'
    rx_ipv6.address.increment.step = '1::'
    rx_ipv6.gateway.increment.start = 'abcd::1a'
    rx_ipv6.gateway.increment.step = '1::'
    rx_ipv6.prefix.value = "48"

    ##############################
    # Flows configuration
    ##############################
    f1, f2 = config.flows.flow(name='FlowIpv4').flow(name='FlowIpv6')
    f1.tx_rx.device.tx_names = [tx_ipv4.name]
    f1.tx_rx.device.rx_names = [rx_ipv4.name]
    f1.size.fixed = size
    f1.duration.fixed_packets.packets = packets
    f1.rate.percentage = "10"

    f2.tx_rx.device.tx_names = [tx_ipv6.name]
    f2.tx_rx.device.rx_names = [rx_ipv6.name]
    f2.size.fixed = size
    f2.duration.fixed_packets.packets = packets
    f2.rate.percentage = "10"

    ##############################
    # Starting transmit on flows
    ##############################
    utils.start_traffic(app_intf, config)

    ##############################
    # Analyzing Traffic metrics
    ##############################
    print('Analyzing flow and port metrics ...')
    utils.wait_for(
        lambda: results_ok(app_intf, utils, size, packets * 2),
        'stats to be as expected', timeout_seconds=10
    )

    ##############################
    # Stopping transmit on flows
    ##############################
    print('Stopping transmit ...')
    utils.stop_traffic(app_intf, config)


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
