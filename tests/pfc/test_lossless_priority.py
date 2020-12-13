import pytest
from abstract_open_traffic_generator import (
    config, port, layer1, flow, flow_ipv4
)


@pytest.mark.e2e
def test_lossless_priority(api, settings, utils):
    """
    Configure ports where,
    - tx port can only respond to pause frames for priority 3 (lossless)
    - rx port is capable of sending pause frames for priorities 1 (lossy) and 3
    Configure two raw IPv4 flows on tx port where,
    - 1st flow is mapped to priority queue 1 and sends 1M frames with PHB_CS1
    - 2nd flow is mapped to priority queue 3 and sends 1M frames with PHB_CS3
    - both flows start after 1 second delay
    - 10% line rate
    Configure one raw PFC Pause flow on rx port where,
    - pause frames for priorties 1 and 3 are sent for 20 seconds (pause storm)
    Validate,
    - tx/rx frame count is 1M until pause storm is over
    - flow 3 has no rx until pause storm is over
    - tx/rx frame count is 2M after pause storm is over
    - flow 3 has expected rx after pause storm is over
    """

    size = 128
    packets = 1000000
    # these are mostly not required when configuring raw traffic
    tx_mac = '00:CD:DC:CD:DC:CD'
    rx_mac = '00:AB:BC:AB:BC:AB'
    tx_ip = '1.1.1.2'
    rx_ip = '1.1.1.1'

    tx = port.Port(name='raw_tx', location=settings.ports[0])
    rx = port.Port(name='raw_rx', location=settings.ports[1])

    tx_l1 = layer1.Layer1(
        name='txl1', port_names=[tx.name], speed=settings.speed, media='fiber',
        flow_control=layer1.FlowControl(
            choice=layer1.Ieee8021qbb(pfc_class_3=3)
        )
    )

    rx_l1 = layer1.Layer1(
        name='rxl1', port_names=[rx.name], speed=settings.speed, media='fiber',
        flow_control=layer1.FlowControl(choice=layer1.Ieee8021qbb())
    )

    tx_f1 = flow.Flow(
        name='tx_f1',
        tx_rx=flow.TxRx(
            flow.PortTxRx(tx_port_name=tx.name, rx_port_name=rx.name)
        ),
        packet=[
            flow.Header(
                flow.Ethernet(
                    src=flow.Pattern(tx_mac),
                    dst=flow.Pattern(rx_mac),
                    pfc_queue=flow.Pattern('1')
                )
            ),
            flow.Header(
                flow.Ipv4(
                    src=flow.Pattern(tx_ip),
                    dst=flow.Pattern(rx_ip),
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
                packets=packets, delay=10**9, delay_unit='nanoseconds'
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
                    src=flow.Pattern(tx_mac),
                    dst=flow.Pattern(rx_mac),
                    pfc_queue=flow.Pattern('3')
                )
            ),
            flow.Header(
                flow.Ipv4(
                    src=flow.Pattern(tx_ip),
                    dst=flow.Pattern(rx_ip),
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
                packets=packets, delay=10**9, delay_unit='nanoseconds'
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
                    src=flow.Pattern(rx_mac),
                    class_enable_vector=flow.Pattern('8'),
                    pause_class_1=flow.Pattern('FFFF'),
                    pause_class_3=flow.Pattern('FFFF')
                )
            )
        ],
        duration=flow.Duration(flow.FixedSeconds(seconds=20)),
        size=flow.Size(size),
        rate=flow.Rate(value=100, unit='line')
    )

    cfg = config.Config(
        ports=[tx, rx], layer1=[tx_l1, rx_l1], flows=[tx_f1, tx_f3, rx_fp],
        options=config.Options(port.Options(location_preemption=True))
    )

    utils.start_traffic(api, cfg)
    utils.wait_for(
        lambda: results_ok(api, cfg, utils, size, packets, 0),
        'stats to be as expected', timeout_seconds=30
    )
    utils.wait_for(
        lambda: results_ok(api, cfg, utils, size, packets, packets),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, cfg, utils, size, f1_pkt, f3_pkt):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    port_tx = sum(
        [p['frames_tx'] for p in port_results if p['name'] == 'raw_tx']
    )
    tx_f1 = sum(
        [f['frames_rx'] for f in flow_results if f['name'] == 'tx_f1']
    )
    tx_f3 = sum(
        [f['frames_rx'] for f in flow_results if f['name'] == 'tx_f3']
    )

    return port_tx == f1_pkt + f3_pkt and tx_f1 == f1_pkt and tx_f3 == f3_pkt
