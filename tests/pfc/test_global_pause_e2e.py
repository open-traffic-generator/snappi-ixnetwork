import pytest
import time


@pytest.mark.e2e
def test_global_pause_e2e(api, settings, utils):
    """
    Configure ports where,
    - tx port can respond to global pause frames
    - rx port is capable of sending global pause frames
    Configure a raw IPv4 flows on tx port where,
    - frames corresponding to all priority values are sent (counter pattern)
    - 1M frames are sent at 100% line rate and with start delay of 1s
    Configure one raw Global Pause flow on rx port where,
    - pause frames are sent for 20 seconds (pause storm)
    Validate,
    - tx/rx frame count is 0 before and 1M after pause storm
    """

    size = 128
    packets = 1000000
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
    tx_flow, rx_flow = config.flows.flow(name='tx_flow').flow('rx_flow')
    tx_flow.tx_rx.port.tx_name, tx_flow.tx_rx.port.rx_name = tx.name, rx.name
    rx_flow.tx_rx.port.tx_name, rx_flow.tx_rx.port.rx_name = rx.name, tx.name
    tx_eth = tx_flow.packet.ethernet()[-1]
    tx_ipv4 = tx_flow.packet.ipv4()[-1]
    rx_eth_pause = rx_flow.packet.ethernetpause()[-1]
    tx_eth.src.value = '00:CD:DC:CD:DC:CD'
    tx_eth.dst.value = '00:AB:BC:AB:BC:AB'
    tx_ipv4.src.value = '1.1.1.2'
    tx_ipv4.dst.value = '1.1.1.1'
    tx_ipv4.priority.raw.increment.start = 0
    tx_ipv4.priority.raw.increment.step = 1
    tx_ipv4.priority.raw.increment.count = 256
    tx_flow.duration.fixed_packets.packets = packets
    tx_flow.duration.fixed_packets.delay = 10**9
    tx_flow.duration.fixed_packets.delay_unit = 'nanoseconds'
    tx_flow.size.fixed = size
    tx_flow.rate.percentage = 100
    rx_eth_pause.src.value = '00:AB:BC:AB:BC:AB'
    rx_eth_pause.control_op_code.value = '01'
    rx_eth_pause.time.value = 'FFFF'
    rx_flow.duration.fixed_seconds.seconds = 20
    rx_flow.size.fixed = size
    rx_flow.rate.percentage = 100
    api.set_config(config)
    utils.start_traffic(api, config)
    # wait for some packets to start flowing
    time.sleep(10)

    utils.wait_for(
        lambda: results_ok(api, config, utils, size, 0),
        'stats to be as expected', timeout_seconds=30
    )
    utils.wait_for(
        lambda: results_ok(api, config, utils, size, packets),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, cfg, utils, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    return packets == sum(
        [p.frames_tx for p in port_results if p.name == 'raw_tx']
    )
