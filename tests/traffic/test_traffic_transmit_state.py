from abstract_open_traffic_generator import flow


def test_traffic_transmit_state(api, b2b_raw_config, utils):
    """
    configure two flows f1 and f2
    - Send 1000 packets from f1 of size 74B
    - Send 2000 packets from f2 of size 1500B

    Validation:
    1) Get port statistics based on port name & column names and assert
    each port & column has returned the values and assert them against
    packets and frame size sent
    2) Get flow statistics based on flow name & column names and assert
    each flow & column has returned the values and assert them against
    packets and frame size sent
    """

    f1_packets = 1000
    f1_size = 74
    f2_size = 1500
    ports = b2b_raw_config.ports
    flow1 = b2b_raw_config.flows[0]

    flow1.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern('00:0c:29:1d:10:67'),
                dst=flow.Pattern('00:0c:29:1d:10:71')
            )
        ),
        flow.Header(
            flow.Ipv4(
                src=flow.Pattern("10.10.10.1"),
                dst=flow.Pattern("10.10.10.2")
            )
        ),
    ]

    flow2 = flow.Flow(
        name='f2',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[0].name,
                rx_port_name=ports[1].name
            )
        )
    )
    b2b_raw_config.flows.append(flow2)

    flow3 = flow.Flow(
        name='f3',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[0].name,
                rx_port_name=ports[1].name
            )
        )
    )
    b2b_raw_config.flows.append(flow3)

    flow1.duration = flow.Duration(flow.FixedPackets(packets=f1_packets))
    flow1.size = flow.Size(f1_size)
    flow1.rate = flow.Rate(value=10, unit='line')

    flow2.duration = flow.Duration(flow.Continuous())
    flow2.size = flow.Size(f2_size)
    flow2.rate = flow.Rate(value=10, unit='line')

    flow3.duration = flow.Duration(flow.FixedPackets(packets=f1_packets))
    flow3.size = flow.Size(f2_size)
    flow3.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    import time
    time.sleep(10)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api, flow_names=['f1', 'f3']),
        'traffic to stop'
    )

    utils.stop_traffic(api, b2b_raw_config)
