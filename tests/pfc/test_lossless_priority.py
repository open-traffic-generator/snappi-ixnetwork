import time
import pytest
from abstract_open_traffic_generator import (
    config, port, layer1, flow, flow_ipv4
)


@pytest.mark.e2e
def test_lossless_priority(api, settings, utils):
    """
    TBD
    """
    tx = port.Port(name='raw_tx', location=settings.ports[0])
    rx = port.Port(name='raw_rx', location=settings.ports[1])

    tx_l1 = layer1.Layer1(
        name='txl1', port_names=[tx.name], speed=settings.speed, media='fiber',
        flow_control=layer1.FlowControl(
            choice=layer1.Ieee8021qbb(pfc_class_3=3)
        )
    )

    rx_l1 = layer1.Layer1(
        name='rxl1', port_names=[rx.name], speed=settings.speed, media='fiber'
    )

    size = 128
    packets = 1000000

    tx_f1 = flow.Flow(
        name='tx_f1',
        tx_rx=flow.TxRx(
            flow.PortTxRx(tx_port_name=tx.name, rx_port_name=rx.name)
        ),
        packet=[
            flow.Header(
                flow.Ethernet(
                    src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                    dst=flow.Pattern('00:AB:BC:AB:BC:AB')
                )
            ),
            flow.Header(
                flow.Ipv4(
                    src=flow.Pattern('1.1.1.2'),
                    dst=flow.Pattern('1.1.1.1'),
                    priority=flow_ipv4.Priority(
                        flow_ipv4.Dscp(
                            flow.Pattern(flow_ipv4.Dscp.PHB_CS1)
                        )
                    )
                )
            )
        ],
        duration=flow.Duration(
            flow.FixedPackets(
                packets=packets, delay=1000000000, delay_unit='nanoseconds'
            )
        ),
        size=flow.Size(size),
        rate=flow.Rate(value=50, unit='line')
    )

    tx_f3 = flow.Flow(
        name='tx_f3',
        tx_rx=flow.TxRx(
            flow.PortTxRx(tx_port_name=tx.name, rx_port_name=rx.name)
        ),
        packet=[
            flow.Header(
                flow.Ethernet(
                    src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                    dst=flow.Pattern('00:AB:BC:AB:BC:AB')
                )
            ),
            flow.Header(
                flow.Ipv4(
                    src=flow.Pattern('1.1.1.2'),
                    dst=flow.Pattern('1.1.1.1'),
                    priority=flow_ipv4.Priority(
                        flow_ipv4.Dscp(
                            flow.Pattern(flow_ipv4.Dscp.PHB_CS3)
                        )
                    )
                )
            )
        ],
        duration=flow.Duration(
            flow.FixedPackets(
                packets=packets, delay=1000000000, delay_unit='nanoseconds'
            )
        ),
        size=flow.Size(size),
        rate=flow.Rate(value=50, unit='line')
    )

    rx_fp = flow.Flow(
        name='rx_fp',
        tx_rx=flow.TxRx(
            flow.PortTxRx(tx_port_name=rx.name, rx_port_name=tx.name)
        ),
        packet=[
            flow.Header(
                flow.PfcPause(
                    src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                    dst=flow.Pattern('00:CD:DC:CD:DC:CD'),
                    pause_class_1=flow.Pattern('111'),
                    pause_class_3=flow.Pattern('111')
                )
            )
        ],
        duration=flow.Duration(flow.FixedPackets(packets=packets * 100)),
        size=flow.Size(size),
        rate=flow.Rate(value=100, unit='line')
    )

    cfg = config.Config(
        ports=[tx, rx], layer1=[tx_l1, rx_l1], flows=[tx_f1, tx_f3, rx_fp],
        options=config.Options(port.Options(location_preemption=True))
    )

    utils.start_traffic(api, cfg)
    time.sleep(5)
    utils.wait_for(
        lambda: results_ok(api, cfg, utils, size, packets),
        'stats to be as expected', timeout_seconds=10
    )


def results_ok(api, cfg, utils, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    # frames_ok = utils.total_frames_ok(port_results, flow_results, packets)

    port_tx = sum(
        [p['frames_tx'] for p in port_results if p['name'] == 'raw_tx']
    )
    tx_f1 = sum(
        [f['frames_rx'] for f in flow_results if f['name'] == 'tx_f1']
    )
    tx_f3 = sum(
        [f['frames_rx'] for f in flow_results if f['name'] == 'tx_f3']
    )

    return port_tx == packets and tx_f1 == packets and tx_f3 == 0


def get_quanta(speed, line_rate, nanoseconds):
    if speed == 'speed_1_gbps':
        speed = 1
    elif speed == 'speed_100_fd_mbps':
        speed = 0.1
    b = (speed * nanoseconds) // 512
    if b > 65535:
        raise Exception('Pause quanta %d greater than 65535' % b)

    return b
