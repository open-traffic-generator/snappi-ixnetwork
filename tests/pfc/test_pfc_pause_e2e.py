import pytest


@pytest.mark.skip("skip until migrated to snappi")
@pytest.mark.e2e
@pytest.mark.parametrize('lossless_priorities', [[3, 4]])
def test_pfc_pause_e2e(api, settings, utils, lossless_priorities):
    """
    Configure ports where,
    - tx port can only respond to pause frames for `lossless_priorities`
    - rx port is capable of sending pause frames for all priorities
    Configure 8 raw IPv4 flows on tx port where,
    - each flow is mapped to corresponding PHB_CS and priority queue value
    - each flow sends 100K frames at 10% line rate and with start delay of 1s
    Configure one raw PFC Pause flow on rx port where,
    - pause frames are sent for 20 seconds (pause storm)
    Validate,
    - tx/rx frame count is 600K before and 800K after pause storm
    - rx frame count for flows pertaining to `lossless_priorities` is 0 before
      and 100K after pause storm
    - rx frame count for rest of the flows is 100K before and after pause storm
    """

    size = 128
    packets = 100000

    tx = port.Port(name='raw_tx', location=settings.ports[0])
    rx = port.Port(name='raw_rx', location=settings.ports[1])

    tx_l1 = layer1.Layer1(
        name='txl1', port_names=[tx.name], speed=settings.speed,
        media=settings.media,
        flow_control=layer1.FlowControl(
            choice=layer1.Ieee8021qbb(
                pfc_class_0=0 if 0 in lossless_priorities else None,
                pfc_class_1=1 if 1 in lossless_priorities else None,
                pfc_class_2=2 if 2 in lossless_priorities else None,
                pfc_class_3=3 if 3 in lossless_priorities else None,
                pfc_class_4=4 if 4 in lossless_priorities else None,
                pfc_class_5=5 if 5 in lossless_priorities else None,
                pfc_class_6=6 if 6 in lossless_priorities else None,
                pfc_class_7=7 if 7 in lossless_priorities else None,
            )
        )
    )

    rx_l1 = layer1.Layer1(
        name='rxl1', port_names=[rx.name], speed=settings.speed,
        media=settings.media,
        flow_control=layer1.FlowControl(choice=layer1.Ieee8021qbb())
    )

    flows = []
    for i in range(0, 8):
        flows.append(
            flow.Flow(
                name='tx_p%d' % i,
                tx_rx=flow.TxRx(
                    flow.PortTxRx(tx_port_name=tx.name, rx_port_name=rx.name)
                ),
                packet=[
                    flow.Header(
                        flow.Ethernet(
                            src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                            dst=flow.Pattern('00:AB:BC:AB:BC:AB'),
                            pfc_queue=flow.Pattern(str(i))
                        )
                    ),
                    flow.Header(
                        flow.Ipv4(
                            src=flow.Pattern('1.1.1.2'),
                            dst=flow.Pattern('1.1.1.1'),
                            priority=flow_ipv4.Priority(
                                flow_ipv4.Dscp(phb=flow.Pattern(str(i * 8)))
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
                rate=flow.Rate(value=10, unit='line')
            )
        )

    flows.append(
        flow.Flow(
            name='rx_pause',
            tx_rx=flow.TxRx(
                flow.PortTxRx(tx_port_name=rx.name, rx_port_name=tx.name)
            ),
            packet=[
                flow.Header(
                    flow.PfcPause(
                        src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                        class_enable_vector=flow.Pattern('FF'),
                        control_op_code=flow.Pattern('0101'),
                        pause_class_0=flow.Pattern('FFFF'),
                        pause_class_1=flow.Pattern('FFFF'),
                        pause_class_2=flow.Pattern('FFFF'),
                        pause_class_3=flow.Pattern('FFFF'),
                        pause_class_4=flow.Pattern('FFFF'),
                        pause_class_5=flow.Pattern('FFFF'),
                        pause_class_6=flow.Pattern('FFFF'),
                        pause_class_7=flow.Pattern('FFFF')
                    )
                )
            ],
            duration=flow.Duration(flow.FixedSeconds(seconds=20)),
            size=flow.Size(size),
            rate=flow.Rate(value=100, unit='line')
        )
    )

    cfg = config.Config(
        ports=[tx, rx], layer1=[tx_l1, rx_l1], flows=flows,
        options=config.Options(port.Options(location_preemption=True))
    )

    utils.start_traffic(api, cfg)
    utils.wait_for(
        lambda: results_ok(
            api, cfg, utils, size, packets, lossless_priorities
        ),
        'stats to be as expected', timeout_seconds=30
    )
    utils.wait_for(
        lambda: results_ok(api, cfg, utils, size, packets, []),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, cfg, utils, size, packets, lossless_priorities):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    ok = [False, False, False, False, False, False, False, False, False]

    port_tx = sum(
        [p['frames_tx'] for p in port_results if p['name'] == 'raw_tx']
    )
    ok[8] = port_tx == packets * (8 - len(lossless_priorities))

    for f in flow_results:
        if f['name'] == 'rx_pause':
            continue

        _, p = f['name'].split('tx_p')
        p = int(p)
        if p in lossless_priorities:
            ok[p] = f['frames_rx'] == 0
        else:
            ok[p] = f['frames_rx'] == packets

    return all(ok)
