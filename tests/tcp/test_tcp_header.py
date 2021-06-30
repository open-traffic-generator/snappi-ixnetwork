def test_tcp_header(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw udp flows with ,
    - fixed src and dst Port address
    - list pattern src and dst Port address
    - counter pattern src and dst Port address

    Validate,
    - Config is applied using validate config
    """
    # fixed
    src_port = 3000
    dst_port = 4000
    size = 74
    packets = 1000
    flow1 = b2b_raw_config_vports.flows[0]
    flow1.packet.ethernet().ipv4().tcp()
    eth = flow1.packet[0]
    ipv4 = flow1.packet[1]
    tcp = flow1.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ipv4.src.value = "10.10.10.1"
    ipv4.dst.value = "10.10.10.2"
    tcp.src_port.value = 3000
    tcp.dst_port.value = 4000
    flow1.duration.fixed_packets.packets = packets
    flow1.size.fixed = size
    flow1.rate.percentage = 10

    # list
    src_port_lst = [3000, 3001]
    dst_port_lst = [4000, 4001]
    packets = 100
    size = 74
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    flow2.packet.ethernet().ipv4().tcp()
    eth = flow2.packet[0]
    ipv4 = flow2.packet[1]
    tcp = flow2.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ipv4.src.value = "10.10.10.1"
    ipv4.dst.value = "10.10.10.2"
    tcp.src_port.values = src_port_lst
    tcp.dst_port.values = dst_port_lst
    flow2.duration.fixed_packets.packets = packets
    flow2.size.fixed = size
    flow2.rate.percentage = 10

    # counter
    src_port_cnt = (5000, 2, 10)
    dst_port_cnt = (6000, 2, 10)
    size = 74
    packets = 100
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    flow3.packet.ethernet().ipv4().tcp()
    eth = flow3.packet[0]
    ipv4 = flow3.packet[1]
    tcp = flow3.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ipv4.src.value = "10.10.10.1"
    ipv4.dst.value = "10.10.10.2"
    tcp.src_port.increment.start = src_port_cnt[0]
    tcp.src_port.increment.step = src_port_cnt[1]
    tcp.src_port.increment.count = src_port_cnt[2]
    tcp.dst_port.increment.start = dst_port_cnt[0]
    tcp.dst_port.increment.step = dst_port_cnt[1]
    tcp.dst_port.increment.count = dst_port_cnt[2]
    flow3.duration.fixed_packets.packets = packets
    flow3.size.fixed = size
    flow3.rate.percentage = 10

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "TCP-Source-Port": str(src_port),
        "TCP-Dest-Port": str(dst_port),
    }
    utils.validate_config(api, "f1", "tcp", **f1_attrs)

    # list validation
    f2_attrs = {
        "TCP-Source-Port": [str(i) for i in src_port_lst],
        "TCP-Dest-Port": [str(i) for i in dst_port_lst],
    }
    utils.validate_config(api, "f2", "tcp", **f2_attrs)

    # counter validation
    f3_attrs = {
        "TCP-Source-Port": ("5000", "2", "10"),
        "TCP-Dest-Port": ("6000", "2", "10"),
    }
    utils.validate_config(api, "f3", "tcp", **f3_attrs)
