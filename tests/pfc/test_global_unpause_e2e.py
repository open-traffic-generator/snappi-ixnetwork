import pytest


@pytest.mark.e2e
def test_global_unpause_e2e(api, settings, utils):
    """
    Configure ports where,
    - tx port can only respond to pause and un-pause frames for
      all priorities
    - rx port is to send pause and un-pause frames on all priorities
    Configure raw IPv4 flows on tx port with all class based priorities where,
    - each flow is mapped to corresponding PHB_CS and priority queue value
    - each flow sends 100K frames at 10% of packets pps rate
      with start delay of 1s
    Configure one raw Global Pause flow and one un-pause flow on rx port where,
    - pause frames are sent for 10 seconds (pause storm)
    - un-pause frames are sent for 10 seconds with start delay of 10s
    Validate,
    - tx/rx frame count is 0 before and (priorities * 100k)
      after pause storm
    """

    size = 128
    packets = 100000
    config = api.config()

    tx, rx = (
        config.ports
        .port(name='raw_tx', location=settings.ports[0])
        .port(name='raw_rx', location=settings.ports[1])
    )
    l1 = config.layer1.layer1(
        name='L1', port_names=[tx.name, rx.name], speed=settings.speed,
    )[-1]

    l1.flow_control.ieee_802_3x
    tx_flow, rx_flow, rx_global_unpause = (
        config.flows
        .flow(name='tx_flow_global')
        .flow(name='rx_global_pause')
        .flow(name='rx_global_unpause')
    )
    tx_flow.tx_rx.port.tx_name, tx_flow.tx_rx.port.rx_name = tx.name, rx.name
    rx_flow.tx_rx.port.tx_name, rx_flow.tx_rx.port.rx_name = rx.name, tx.name
    rx_global_unpause.tx_rx.port.tx_name = rx.name
    rx_global_unpause.tx_rx.port.rx_name = tx.name
    tx_eth = tx_flow.packet.ethernet()[-1]
    tx_ipv4 = tx_flow.packet.ipv4()[-1]
    tx_eth.src.value = '00:CD:DC:CD:DC:CD'
    tx_eth.dst.value = '00:AB:BC:AB:BC:AB'
    tx_ipv4.src.value = '1.1.1.2'
    tx_ipv4.dst.value = '1.1.1.1'
    tx_ipv4.priority.raw.increment.start = 0
    tx_ipv4.priority.raw.increment.step = 1
    tx_ipv4.priority.raw.increment.count = 256
    tx_flow.duration.fixed_packets.packets = packets
    tx_flow.duration.fixed_packets.delay.nanoseconds = 10**9
    tx_flow.size.fixed = size
    tx_flow.rate.percentage = 100
    rx_eth_pause = rx_flow.packet.ethernetpause()[-1]
    rx_eth_pause.src.value = '00:AB:BC:AB:BC:AB'
    rx_eth_pause.ether_type.value = '8808'
    rx_eth_pause.control_op_code.value = '01'
    rx_eth_pause.time.value = 'FFFF'
    rx_flow.duration.fixed_seconds.seconds = 10
    rx_flow.size.fixed = size
    rx_flow.rate.percentage = 50

    rx_eth_unpause = rx_global_unpause.packet.ethernetpause()[-1]
    rx_eth_unpause.src.value = '00:AB:BC:AB:BC:AB'
    rx_eth_unpause.ether_type.value = '8808'
    rx_eth_unpause.control_op_code.value = '01'
    rx_eth_unpause.time.value = 'FFFF'
    rx_global_unpause.duration.fixed_seconds.seconds = 10
    rx_global_unpause.duration.fixed_seconds.delay.nanoseconds = (10**9) * 10
    rx_global_unpause.size.fixed = size
    rx_global_unpause.rate.percentage = 50

    api.set_config(config)
    utils.start_traffic(api, config)

    utils.wait_for(
        lambda: results_ok(
            api, utils, packets
        ),
        'stats to be as expected', timeout_seconds=10
    )

    utils.wait_for(
        lambda: results_ok(api, utils, packets, False),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, utils, packets, check_for_pause=True):
    """
    Returns true if stats are as expected, false otherwise.
    """
    _, flow_results = utils.get_all_stats(api)
    pause = [
        f.frames_rx for f in flow_results if f.name == 'rx_global_pause'
    ][0]
    un_pause = [
        f.frames_rx for f in flow_results if f.name == 'rx_global_unpause'
    ][0]
    ok = False

    for fl in flow_results:
        if fl.name == 'rx_global_pause' or \
           fl.name == 'rx_global_unpause':
            continue
        if pause > 0 and un_pause == 0 and check_for_pause and \
           fl.name == "tx_flow_global":
            ok = fl.frames_tx == fl.frames_rx == 0
            continue
        if un_pause > 0 and (check_for_pause is False) \
           and fl.name == "tx_flow_global":
            ok = fl.frames_tx == fl.frames_rx == packets

    return ok
