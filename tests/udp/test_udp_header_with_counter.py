def test_udp_header_with_counter(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - Non-default Counter Pattern values of src and
      dst Port address, length, checksum
    - 100 frames of 74B size each
    - 10% line rate

    Validate,
    - validate the config against restpy
    """
    flow = b2b_raw_config.flows[0]

    src_port = (5000, 2, 10)
    dst_port = (6000, 2, 10)
    length = (35, 1, 2)
    checksum = (6, 1, 2)
    packets = 100
    size = 74

    flow.size.fixed = size
    flow.duration.fixed_packets.packets = packets
    flow.rate.percentage = 10

    eth, ip, udp = flow.packet.ethernet().ipv4().udp()

    eth.src.value = '00:0c:29:1d:10:67'
    eth.dst.value = '00:0c:29:1d:10:71'

    ip.src.value = '10.10.10.1'
    ip.dst.value = '10.10.10.2'

    udp.src_port.increment.start = src_port[0]
    udp.src_port.increment.step = src_port[1]
    udp.src_port.increment.count = src_port[2]

    udp.dst_port.decrement.start = dst_port[0]
    udp.dst_port.decrement.step = dst_port[1]
    udp.dst_port.decrement.count = dst_port[2]

    udp.length.increment.start = length[0]
    udp.length.increment.step = length[1]
    udp.length.increment.count = length[2]

    udp.checksum.increment.start = checksum[0]
    udp.checksum.increment.step = checksum[1]
    udp.checksum.increment.count = checksum[2]

    api.set_config(b2b_raw_config)

    attrs = {
        'UDP-Source-Port': tuple(map(str, src_port)),
        'UDP-Dest-Port': tuple(map(str, dst_port)),
        'UDP-Length': tuple(map(str, length)),
        'UDP-Checksum': tuple(map(str, checksum)),
    }
    utils.validate_config(api, 'udp', **attrs)
