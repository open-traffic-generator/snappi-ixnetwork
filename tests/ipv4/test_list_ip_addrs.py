def test_list_ip_addr(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - list pattern src and dst IPv4 address

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    step = "05:00:00:02:01:00"
    src = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:EA", step, 5, True
    )
    dst = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:F4", step, 5, True
    )

    step = "0.0.1.0"
    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"

    src_ip_list = utils.mac_or_ip_addr_from_counter_pattern(
        src_ip, step, 5, True, False
    )
    dst_ip_list = utils.mac_or_ip_addr_from_counter_pattern(
        dst_ip, step, 5, True, False
    )
    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[1]
    eth.src.values = src
    eth.dst.values = dst
    ipv4.src.values = src_ip_list
    ipv4.dst.values = dst_ip_list
    api.set_config(b2b_raw_config)
    attrs = {
        "Destination Address": dst_ip_list,
        "Source Address": src_ip_list,
    }
    utils.validate_config(api, "ipv4", **attrs)
