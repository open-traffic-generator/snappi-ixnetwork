def test_udp_header_with_fixed(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address, length, checksum
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    src_port = 3000
    dst_port = 4000
    length = 38
    packets = 1000
    size = 74
    flow = b2b_raw_config.flows[0]

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

    api.set_config(b2b_raw_config)

    attrs = {
        'UDP-Source-Port': str(src_port),
        'UDP-Dest-Port': str(dst_port),
        'UDP-Length': str(length),
    }
    utils.validate_config(api, 'udp', **attrs)
