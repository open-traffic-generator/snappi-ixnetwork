def test_flow_duration(api, utils):
    """
    This will test different transmit durations:
    [1] Fixed : A fixed number of packets will be transmitted after which the flow will stop
                If the number of packets is set to 0 the flow will not stop
        Args
        ----
        - packets (int): Stop transmit of the flow after this number of packets. A value of 0 means that the flow will not stop transmitting
        - gap (int): The minimum gap between packets expressed as bytes
        - delay (int): The delay before starting transmission of packets
        - delay_unit (Union[bytes, nanoseconds]): The delay expressed as a number of this value

    [2] Burst : A continuous burst of packets that will not automatically stop
        Args
        ----
        - packets (int): The number of packets transmitted per burst
        - gap (int): The minimum gap between packets expressed as bytes
        - inter_burst_gap (int): The gap between the transmission of each burst. A value of 0 means there is no gap between bursts
        - inter_burst_gap_unit (Union[bytes, nanoseconds]): The inter burst gap expressed as a number of this value
    """

    config = api.config()
    config.ports.port(name='tx').port(name='rx')
    tx_port, rx_port = config.ports
    tx_port.location = utils.settings.ports[0]
    rx_port.location = utils.settings.ports[1]
    l1, l2 = config.layer1.layer1(name='l10').layer1(name='l11')
    l1.port_names, l2.port_names = [tx_port.name], [rx_port.name]
    l1.media, l1.media = utils.settings.media, utils.settings.media
    l1.speed, l2.speed = utils.settings.speed, utils.settings.speed
    c, fp, fs, b = config.flows.flow().flow().flow().flow()

    # Test for Continuous Flow
    c.name = 'Continuous Duration'
    c.packet.ethernet().vlan().ipv4()
    c.duration.choice = c.duration.CONTINUOUS
    c.tx_rx.port.tx_name = tx_port.name
    c.tx_rx.port.rx_name = rx_port.name

    # Test for Fix packet with Gap and Delay
    fp.name = 'Fixed Packet Duration'
    fp.tx_rx.port.tx_name = tx_port.name
    fp.tx_rx.port.rx_name = rx_port.name
    fp.packet.ethernet().vlan().ipv4()
    fp.duration.fixed_packets.packets = 125
    fp.duration.fixed_packets.gap = 2
    fp.duration.fixed_packets.delay.bytes = 8

    # Test for Fix second with Gap and Delay
    fs.name = 'Fixed Seconds Duration'
    fs.tx_rx.port.tx_name = tx_port.name
    fs.tx_rx.port.rx_name = rx_port.name
    fs.packet.ethernet().vlan().ipv4()
    fs.duration.fixed_seconds.seconds = 312
    fs.duration.fixed_seconds.gap = 2
    fs.duration.fixed_seconds.delay.bytes = 8

    # Test for Burst Duration with Gap and inter burst gap
    b.name = 'Fixed Burst Duration'
    b.tx_rx.port.tx_name = tx_port.name
    b.tx_rx.port.rx_name = rx_port.name
    b.packet.ethernet().vlan().ipv4()
    b.duration.burst.packets = 700
    b.duration.burst.gap = 8
    b.duration.burst.inter_burst_gap.nanoseconds = 4

    api.set_config(config)
