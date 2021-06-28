def test_tcp_header_with_fixed(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - Config is applied using validate config
    """
    src_port = 3000
    dst_port = 4000
    size = 74
    packets = 1000
    flow = b2b_raw_config.flows[0]
    flow.packet.ethernet().ipv4().tcp()
    eth = flow.packet[0]
    ipv4 = flow.packet[1]
    tcp = flow.packet[2]
    eth.src.value = "00:0c:29:1d:10:67"
    eth.dst.value = "00:0c:29:1d:10:71"
    ipv4.src.value = "10.10.10.1"
    ipv4.dst.value = "10.10.10.2"
    tcp.src_port.value = 3000
    tcp.dst_port.value = 4000
    flow.duration.fixed_packets.packets = packets
    flow.size.fixed = size
    flow.rate.percentage = 10

    api.set_config(b2b_raw_config)
    attrs = {
        "TCP-Source-Port": str(src_port),
        "TCP-Dest-Port": str(dst_port),
    }
    utils.validate_config(api, "tcp", **attrs)
