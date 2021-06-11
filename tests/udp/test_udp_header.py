def test_udp_header(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address, length, checksum
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    # fixed
    src_port = 3000
    dst_port = 4000
    length = 38
    packets = 1000
    size = 74
    flow = b2b_raw_config_vports.flows[0]

    flow.size.fixed = size
    flow.duration.fixed_packets.packets = packets
    flow.rate.percentage = 10

    eth, ip, udp = flow.packet.ethernet().ipv4().udp()

    eth.src.value = '00:0c:29:1d:10:67'
    eth.dst.value = '00:0c:29:1d:10:71'

    ip.src.value = '10.10.10.1'
    ip.dst.value = '10.10.10.2'

    udp.src_port.value = src_port
    udp.dst_port.value = dst_port
    udp.length.value = length

    # list
    flow2 = b2b_raw_config_vports.flows.flow(name='f2')[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name

    src_port_lst = [3000, 3001]
    dst_port_lst = [4000, 4001]
    length_lst = [35, 36]
    size = 74
    packets = 100

    flow2.size.fixed = size
    flow2.duration.fixed_packets.packets = packets
    flow2.rate.percentage = 10

    eth, ip, udp = flow2.packet.ethernet().ipv4().udp()

    eth.src.value = '00:0c:29:1d:10:67'
    eth.dst.value = '00:0c:29:1d:10:71'

    ip.src.value = '10.10.10.1'
    ip.dst.value = '10.10.10.2'

    udp.src_port.values = src_port_lst
    udp.dst_port.values = dst_port_lst
    udp.length.values = length_lst

    # counter
    flow3 = b2b_raw_config_vports.flows.flow(name='f3')[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name

    src_port_cnt = (5000, 2, 10)
    dst_port_cnt = (6000, 2, 10)
    length_cnt = (35, 1, 2)
    packets = 100
    size = 74

    flow3.size.fixed = size
    flow3.duration.fixed_packets.packets = packets
    flow3.rate.percentage = 10

    eth, ip, udp = flow3.packet.ethernet().ipv4().udp()

    eth.src.value = '00:0c:29:1d:10:67'
    eth.dst.value = '00:0c:29:1d:10:71'

    ip.src.value = '10.10.10.1'
    ip.dst.value = '10.10.10.2'

    udp.src_port.increment.start = src_port_cnt[0]
    udp.src_port.increment.step = src_port_cnt[1]
    udp.src_port.increment.count = src_port_cnt[2]

    udp.dst_port.decrement.start = dst_port_cnt[0]
    udp.dst_port.decrement.step = dst_port_cnt[1]
    udp.dst_port.decrement.count = dst_port_cnt[2]

    udp.length.increment.start = length_cnt[0]
    udp.length.increment.step = length_cnt[1]
    udp.length.increment.count = length_cnt[2]

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        'UDP-Source-Port': str(src_port),
        'UDP-Dest-Port': str(dst_port),
        'UDP-Length': str(length),
    }
    utils.validate_config(api, 'f1', 'udp', **f1_attrs)

    # list validation
    f2_attrs = {
        'UDP-Source-Port': [str(src) for src in src_port_lst],
        'UDP-Dest-Port': [str(dst) for dst in dst_port_lst],
        'UDP-Length': [str(len) for len in length_lst],
    }
    utils.validate_config(api, 'f2', 'udp', **f2_attrs)

    # counter validation
    f3_attrs = {
        'UDP-Source-Port': tuple(map(str, src_port_cnt)),
        'UDP-Dest-Port': tuple(map(str, dst_port_cnt)),
        'UDP-Length': tuple(map(str, length_cnt)),
    }
    utils.validate_config(api, 'f3', 'udp', **f3_attrs)
