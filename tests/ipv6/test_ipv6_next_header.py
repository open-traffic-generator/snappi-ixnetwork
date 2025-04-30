def test_ipv6_next_header(
    api, b2b_raw_config_vports, utils, tx_vport, rx_vport
):
    """
    Configure the ipv6 packet,
    - next header shall be set to auto by default

    Validate,
    - Fetch the IPv6 header config via restpy and validate
      against expected
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    eth, ipv6, udp = flow1.packet.ethernet().ipv6().udp()
    eth.src.value = src
    eth.dst.value = dst
    ipv6.version.value = 15
    ipv6.traffic_class.value = 255
    ipv6.flow_label.value = 1048575
    ipv6.payload_length.value = 255
    ipv6.hop_limit.value = 255
    ipv6.src.value = "2001::1"
    ipv6.dst.value = "2002::1"

    # fixed validation
    f1_attrs = {
        "Version": str(ipv6.version.value),
        "Traffic Class": str(ipv6.traffic_class.value),
        "Flow Label": str(ipv6.flow_label.value),
        "Next Header": "17",
        "Hop Limit": str(ipv6.hop_limit.value),
        "Source Address": ipv6.src.value,
        "Destination Address": ipv6.dst.value,
    }
    api.set_config(b2b_raw_config_vports)

    utils.validate_config(api, "f1", "ipv6", **f1_attrs)
