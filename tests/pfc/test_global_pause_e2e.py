import pytest


@pytest.mark.skip("skip until migrated to snappi")
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

    tx = port.Port(name='raw_tx', location=settings.ports[0])
    rx = port.Port(name='raw_rx', location=settings.ports[1])

    tx_l1 = layer1.Layer1(
        name='txl1', port_names=[tx.name], speed=settings.speed,
        media=settings.media,
        flow_control=layer1.FlowControl(choice=layer1.Ieee8023x())
    )

    rx_l1 = layer1.Layer1(
        name='rxl1', port_names=[rx.name], speed=settings.speed,
        media=settings.media,
        flow_control=layer1.FlowControl(choice=layer1.Ieee8023x())
    )

    tx_flow = flow.Flow(
        name='tx_flow',
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
                        flow.Pattern(
                            flow.Counter(start='0', step='1', count=256)
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
        rate=flow.Rate(value=100, unit='line')
    )

    rx_flow = flow.Flow(
        name='rx_flow',
        tx_rx=flow.TxRx(
            flow.PortTxRx(tx_port_name=rx.name, rx_port_name=tx.name)
        ),
        packet=[
            flow.Header(
                flow.EthernetPause(
                    src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                    control_op_code=flow.Pattern('01'),
                    time=flow.Pattern('FFFF')
                )
            )
        ],
        duration=flow.Duration(flow.FixedSeconds(seconds=20)),
        size=flow.Size(size),
        rate=flow.Rate(value=100, unit='line')
    )

    cfg = config.Config(
        ports=[tx, rx], layer1=[tx_l1, rx_l1], flows=[tx_flow, rx_flow],
        options=config.Options(port.Options(location_preemption=True))
    )

    utils.start_traffic(api, cfg)
    # wait for some packets to start flowing
    time.sleep(10)

    utils.wait_for(
        lambda: results_ok(api, cfg, utils, size, 0),
        'stats to be as expected', timeout_seconds=30
    )
    utils.wait_for(
        lambda: results_ok(api, cfg, utils, size, packets),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, cfg, utils, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    return packets == sum(
        [p['frames_tx'] for p in port_results if p['name'] == 'raw_tx']
    )
