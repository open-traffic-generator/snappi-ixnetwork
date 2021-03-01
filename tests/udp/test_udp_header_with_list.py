def test_udp_header_with_list(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - Non-default list values of src and dst Port address, length, checksum
    - 100 frames of 74B size each
    - 10% line rate

    Validate,
    - Validate the config against restpy
    """
    flow = b2b_raw_config.flows[0]

    src_port = [3000, 3001]
    dst_port = [4000, 4001]
    length = [35, 36]
    size = 74
    packets = 100

    flow.size.fixed = size
    flow.duration.fixed_packets.packets = packets
    flow.rate.percentage = 10

    eth, ip, udp = flow.packet.ethernet().ipv4().udp()

    eth.src.value = '00:0c:29:1d:10:67'
    eth.dst.value = '00:0c:29:1d:10:71'

    ip.src.value = '10.10.10.1'
    ip.dst.value = '10.10.10.2'

    udp.src_port.values = src_port
    udp.dst_port.values = dst_port
    udp.length.values = length

    api.set_config(b2b_raw_config)

    attrs = {
        'UDP-Source-Port': [str(src) for src in src_port],
        'UDP-Dest-Port': [str(dst) for dst in dst_port],
        'UDP-Length': [str(len) for len in length],
    }
    utils.validate_config(api, 'udp', **attrs)
