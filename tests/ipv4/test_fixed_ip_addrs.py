def test_fixed_ip_addr(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - fixed src and dst IPv4 address

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"
    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[1]
    eth.src.value = src
    eth.dst.value = dst
    ipv4.src.value = src_ip
    ipv4.dst.value = dst_ip

    api.set_config(b2b_raw_config)
    attrs = {
        "Destination Address": dst_ip,
        "Source Address": src_ip,
    }
    utils.validate_config(api, "ipv4", **attrs)
