def test_traffic_transmit_state(api, b2b_raw_config, utils):
    """
    configure two flows f1 and f2
    - Send fixed packets from f1
    - Send continuous packets from f2
    - Send fixed packets from f3

    Validation:
    1) Validate the transmit state of the f1 & f3
       as stopped after packets exhausted
    """

    f1_packets = 1000
    f1_size = 74
    f2_size = 1500
    ports = b2b_raw_config.ports
    flow1 = b2b_raw_config.flows[0]
    flow1.name = "tx_flow1"
    flow1.packet.ethernet().ipv4()
    flow1.packet[0].src.value = "00:0c:29:1d:10:67"
    flow1.packet[0].dst.value = "00:0c:29:1d:10:71"
    flow1.packet[1].src.value = "10.10.10.1"
    flow1.packet[1].dst.value = "10.10.10.2"
    flow2 = b2b_raw_config.flows.flow()[-1]
    flow2.name = "tx_flow2"
    flow2.tx_rx.port.tx_name = ports[0].name
    flow2.tx_rx.port.rx_name = ports[1].name

    flow3 = b2b_raw_config.flows.flow()[-1]
    flow3.name = "tx_flow3"
    flow3.tx_rx.port.tx_name = ports[0].name
    flow3.tx_rx.port.rx_name = ports[1].name

    flow1.duration.fixed_packets.packets = f1_packets
    flow1.size.fixed = f1_size
    flow1.rate.percentage = 10

    flow2.duration.continuous
    flow2.size.fixed = f2_size
    flow2.rate.percentage = 10

    flow3.duration.fixed_packets.packets = f1_packets
    flow3.size.fixed = f2_size
    flow3.rate.percentage = 10

    flow1.metrics.enable = True
    flow1.metrics.loss = True

    flow3.metrics.enable = True
    flow3.metrics.loss = True

    utils.start_traffic(api, b2b_raw_config)
    import time

    time.sleep(10)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(
            api, flow_names=["tx_flow1", "tx_flow3"]
        ),
        "traffic to stop",
    )

    utils.stop_traffic(api, b2b_raw_config)
