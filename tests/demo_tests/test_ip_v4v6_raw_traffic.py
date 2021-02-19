import pytest
import snappi


@pytest.fixture
def app_intf(utils):
    api = snappi.api(host=utils.settings.api_server, ext=utils.settings.ext)
    yield api
    if getattr(api, 'assistant', None) is not None:
        api.assistant.Session.remove()


@pytest.mark.e2e
def test_ip_v4v6_raw_traffic(app_intf, utils):
    """
    Test to demonstrate ipv4 and ipv6 raw type traffic
    configuration, transmit and statistics.
    """
    config = app_intf.config()

    src = '00:0C:29:E3:53:EA'
    dst = '00:0C:29:E3:53:F4'

    src_ipv4 = '10.1.1.1'
    dst_ipv4 = '20.1.1.1'

    src_ipv6 = 'abcd::1a'
    dst_ipv6 = 'abcd::2a'

    size = 128
    packets = 100000
    ##############################
    # Ports configuration
    ##############################
    tx, rx = config.ports.port(name='tx').port(name='rx')
    tx.location = utils.settings.ports[0]
    rx.location = utils.settings.ports[1]
    l1 = config.layer1.layer1()[-1]
    l1.name = 'L1 Settings'
    l1.port_names = [tx.name, rx.name]
    l1.speed = utils.settings.speed
    l1.media = utils.settings.media

    ##############################
    # Flow configuration
    ##############################
    f = config.flows.flow()[-1]
    f.name = 'Ipv4 Flow'
    f.tx_rx.port.tx_name = tx.name
    f.tx_rx.port.rx_name = rx.name
    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[1]
    eth.src.value = src
    eth.dst.value = dst
    ipv4.src.value = src_ipv4
    ipv4.dst.value = dst_ipv4
    f.size.fixed = size
    f.duration.fixed_packets.packets = packets

    f1 = config.flows.flow()[-1]
    f1.name = 'Ipv6 Flow'
    f1.tx_rx.port.tx_name = tx.name
    f1.tx_rx.port.rx_name = rx.name
    f1.packet.ethernet().ipv6()
    eth = f1.packet[0]
    ipv6 = f1.packet[1]
    eth.src.value = src
    eth.dst.value = dst
    ipv6.src.value = src_ipv6
    ipv6.dst.value = dst_ipv6
    f1.size.fixed = size
    f1.duration.fixed_packets.packets = packets

    ##############################
    # Setting the config to Ixia
    ##############################
    app_intf.set_config(config)

    ##############################
    # Starting transmit on flows
    ##############################
    print('Starting transmit on all flows ...')
    ts = app_intf.transmit_state()
    ts.state = ts.START
    app_intf.set_transmit_state(ts)

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
    ts = app_intf.transmit_state()
    ts.state = ts.STOP
    app_intf.set_transmit_state(ts)


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
