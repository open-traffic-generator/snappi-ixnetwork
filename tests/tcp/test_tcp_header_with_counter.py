def test_tcp_header_with_counter(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - Non-default Counter Pattern values of src and
      dst Port address, length, checksum
    - 100 frames of 74B size each
    - 10% line rate

    Validate,
    - Config is applied using validate config
    """
    src_port = (5000, 2, 10)
    dst_port = (6000, 2, 10)
    size = 74
    packets = 100
    flow = b2b_raw_config.flows[0]
    flow.packet.ethernet().ipv4().tcp()
    eth = flow.packet[0]
    ipv4 = flow.packet[1]
    tcp = flow.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ipv4.src.value = "10.10.10.1"
    ipv4.dst.value = "10.10.10.2"
    tcp.src_port.increment.start = src_port[0]
    tcp.src_port.increment.step = src_port[1]
    tcp.src_port.increment.count = src_port[2]
    tcp.dst_port.increment.start = dst_port[0]
    tcp.dst_port.increment.step = dst_port[1]
    tcp.dst_port.increment.count = dst_port[2]
    flow.duration.fixed_packets.packets = packets
    flow.size.fixed = size
    flow.rate.percentage = 10

    api.set_config(b2b_raw_config)
    attrs = {
        "TCP-Source-Port": ("5000", "2", "10"),
        "TCP-Dest-Port": ("6000", "2", "10"),
    }
    utils.validate_config(api, "tcp", **attrs)
