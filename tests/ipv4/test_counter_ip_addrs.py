def test_counter_ip_addr(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - Counter Pattern src and dst IPv4 address

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    count = 10
    step = "05:00:00:02:01:00"
    src = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:EA", step, count, True
    )
    dst = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:F4", step, count, True
    )

    step = "0.0.1.0"
    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"

    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[1]
    eth.src.values = src
    eth.dst.values = dst

    ipv4.src.increment.start = src_ip
    ipv4.src.increment.step = step
    ipv4.src.increment.count = count
    ipv4.dst.decrement.start = dst_ip
    ipv4.dst.decrement.step = step
    ipv4.dst.decrement.count = count
    api.set_config(b2b_raw_config)
    attrs = {
        "Destination Address": (dst_ip, step, str(count)),
        "Source Address": (src_ip, step, str(count)),
    }
    utils.validate_config(api, "ipv4", **attrs)
