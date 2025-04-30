def test_ipv6_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw raw IPv6 flows with ,
    - fixed pattern for the fields
    - list pattern for the fields
    - counter pattern for the fields

    Validate,
    - Fetch the IPv6 header config via restpy and validate
      against expected
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    eth, ipv6 = flow1.packet.ethernet().ipv6()
    eth.src.value = src
    eth.dst.value = dst
    ipv6.version.value = 15
    ipv6.traffic_class.value = 255
    ipv6.flow_label.value = 1048575
    ipv6.payload_length.value = 255
    ipv6.next_header.value = 255
    ipv6.hop_limit.value = 255
    ipv6.src.value = "2001::1"
    ipv6.dst.value = "2002::1"

    # fixed validation
    f1_attrs = {
        "Version": str(ipv6.version.value),
        "Traffic Class": str(ipv6.traffic_class.value),
        "Flow Label": str(ipv6.flow_label.value),
        # this value is learned
        # "Payload Length": str(ipv6.payload_length.value),
        "Next Header": str(ipv6.next_header.value),
        "Hop Limit": str(ipv6.hop_limit.value),
        "Source Address": ipv6.src.value,
        "Destination Address": ipv6.dst.value,
    }

    # list
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name

    version_list = [0, 15]
    traffic_class_list = [0, 15, 255]
    flow_label_list = [0, 15, 255, 4095, 65535, 1048575]
    next_header_list = [0, 15, 255]
    hop_limit_list = [0, 15, 255]
    src_ip_list = ["2001::1", "2002::1", "2003::1", "2004::1"]
    dst_ip_list = ["2005::1", "2006::1", "2007::1", "2008::1"]

    eth, ipv6 = flow2.packet.ethernet().ipv6()
    eth.src.value = src
    eth.dst.value = dst
    ipv6.version.values = version_list
    ipv6.traffic_class.values = traffic_class_list
    ipv6.flow_label.values = flow_label_list
    ipv6.next_header.values = next_header_list
    ipv6.hop_limit.values = hop_limit_list
    ipv6.src.values = src_ip_list
    ipv6.dst.values = dst_ip_list

    # # list validation
    f2_attrs = {
        "Version": [str(v) for v in version_list],
        "Traffic Class": [str(t) for t in traffic_class_list],
        "Flow Label": [str(f) for f in flow_label_list],
        "Next Header": [str(n) for n in next_header_list],
        "Hop Limit": [str(h) for h in hop_limit_list],
        "Source Address": src_ip_list,
        "Destination Address": dst_ip_list,
    }

    # counter
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    fields = [
        "version",
        "traffic_class",
        "flow_label",
        "next_header",
        "hop_limit",
        "src",
        "dst",
    ]
    start = [0, 0, 0, 0, 0, "2001::1", "2002::1"]
    step = [1, 2, 4, 2, 2, "1::", "1::"]
    count = [15, 128, 262144, 128, 128, 1000, 1000]

    eth, ipv6 = flow3.packet.ethernet().ipv6()
    eth.src.value = src
    eth.dst.value = dst
    for i, field in enumerate(fields):
        f_obj = getattr(ipv6, field)
        f_obj.increment.start = start[i]
        f_obj.increment.step = step[i]
        f_obj.increment.count = count[i]

    # counter validation
    keys = [
        "Version",
        "Traffic Class",
        "Flow Label",
        "Next Header",
        "Hop Limit",
        "Source Address",
        "Destination Address",
    ]
    f3_attrs = dict()
    for i, k in enumerate(keys):
        f3_attrs[k] = (str(start[i]), str(step[i]), str(count[i]))

    api.set_config(b2b_raw_config_vports)

    utils.validate_config(api, "f1", "ipv6", **f1_attrs)
    utils.validate_config(api, "f2", "ipv6", **f2_attrs)
    utils.validate_config(api, "f3", "ipv6", **f3_attrs)
