def test_mpls_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw mpls flows with ,
    - fixed pattern for all mpls fields
    - list pattern for all mpls fields
    - counter pattern for all mpls fields
    Validate,
    - fetch the mpls header via restpy framework and validate
      against expected.
    """
    # fixed
    outer_src_mac = "00:00:0a:00:00:01"
    outer_dst_mac = "00:00:0b:00:00:02"
    ether_type = 2048
    src_ip = "200.1.1.1"
    dst_ip = "100.1.1.1"
    src_port = 3000
    dst_port = 4000
    inner_src_mac = "00:00:0c:00:00:03"
    inner_dst_mac = "00:00:0d:00:00:04"
    label = 255
    exp = 5
    ttl = 200

    flow1 = b2b_raw_config_vports.flows[0]

    outer_eth, mpls, inner_eth, inner_ip, inner_udp  = (
        flow1.packet.ethernet().mpls().ethernet().ipv4().udp()
    )

    outer_eth.src.value = outer_src_mac
    outer_eth.dst.value = outer_dst_mac
    outer_eth.ether_type.value = ether_type

    mpls.label.value = label
    mpls.traffic_class.value = exp
    mpls.bottom_of_stack.value = 1
    mpls.time_to_live.value = ttl

    inner_eth.src.value = inner_src_mac
    inner_eth.dst.value = inner_dst_mac

    inner_ip.src.value = src_ip
    inner_ip.dst.value = dst_ip

    inner_udp.src_port.value = src_port
    inner_udp.dst_port.value = dst_port


    # List
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name

    label_list = [0, 15, 255]
    exp_list = [0, 2, 3, 5, 6, 7]
    bos_list = [0, 1, 1, 0]
    ttl_list = [0, 15, 255]

    outer_eth, mpls, inner_eth, inner_ip, inner_udp  = (
        flow2.packet.ethernet().mpls().ethernet().ipv4().udp()
    )

    outer_eth.src.value = outer_src_mac
    outer_eth.dst.value = outer_dst_mac
    outer_eth.ether_type.value = ether_type

    mpls.label.values = label_list
    mpls.traffic_class.values = exp_list
    mpls.bottom_of_stack.values = bos_list
    mpls.time_to_live.values = ttl_list

    inner_eth.src.value = inner_src_mac
    inner_eth.dst.value = inner_dst_mac

    inner_ip.src.value = src_ip
    inner_ip.dst.value = dst_ip

    inner_udp.src_port.value = src_port
    inner_udp.dst_port.value = dst_port

    # Counter
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name

    outer_eth, mpls, inner_eth, inner_ip, inner_udp  = (
        flow3.packet.ethernet().mpls().ethernet().ipv4().udp()
    )

    outer_eth.src.value = outer_src_mac
    outer_eth.dst.value = outer_dst_mac
    outer_eth.ether_type.value = ether_type

    mpls.label.increment.start = 0
    mpls.label.increment.step = 1
    mpls.label.increment.count = 256

    mpls.traffic_class.increment.start = 0
    mpls.traffic_class.increment.step = 1
    mpls.traffic_class.increment.count = 8

    mpls.bottom_of_stack.increment.start = 0
    mpls.bottom_of_stack.increment.step = 1
    mpls.bottom_of_stack.increment.count = 1

    mpls.time_to_live.increment.start = 0
    mpls.time_to_live.increment.step = 1
    mpls.time_to_live.increment.count = 256

    inner_eth.src.value = inner_src_mac
    inner_eth.dst.value = inner_dst_mac

    inner_ip.src.value = src_ip
    inner_ip.dst.value = dst_ip

    inner_udp.src_port.value = src_port
    inner_udp.dst_port.value = dst_port

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "Label Value": str(label),
        "MPLS Exp": str(exp),
        "Bottom of Stack Bit": str(1),
        "Time To Live": str(ttl),
    }
    utils.validate_config(api, "f1", "mpls", **f1_attrs)

    # list validation
    f2_attrs = {
        "Label Value": [str(v) for v in label_list],
        "MPLS Exp": [str(v) for v in exp_list],
        "Bottom of Stack Bit": [str(v) for v in bos_list],
        "Time To Live": [str(v) for v in ttl_list],
    }
    utils.validate_config(api, "f2", "mpls", **f2_attrs)

    # counter validation
    f3_attrs = {
        "Label Value": (
            str(mpls.label.increment.start),
            str(mpls.label.increment.step),
            str(mpls.label.increment.count),
        ),
        "MPLS Exp": (
            str(mpls.traffic_class.increment.start),
            str(mpls.traffic_class.increment.step),
            str(mpls.traffic_class.increment.count),
        ),
        "Bottom of Stack Bit": (
            str(mpls.bottom_of_stack.increment.start),
            str(mpls.bottom_of_stack.increment.step),
            str(mpls.bottom_of_stack.increment.count),
        ),
        "Time To Live": (
            str(mpls.time_to_live.increment.start),
            str(mpls.time_to_live.increment.step),
            str(mpls.time_to_live.increment.count),
        ),
    }
    utils.validate_config(api, "f3", "mpls", **f3_attrs)
