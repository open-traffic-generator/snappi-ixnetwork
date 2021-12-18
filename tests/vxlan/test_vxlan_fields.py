def test_vxlan_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw vxlan flows with ,
    - fixed pattern for all vxlan fields
    - list pattern for all vxlan fields
    - counter pattern for all vxlan fields
    Validate,
    - fetch the vxlan header via restpy framework and validate
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
    flags = 255
    vni = 2000

    flow1 = b2b_raw_config_vports.flows[0]

    outer_eth, ip, udp, vxlan, inner_eth = (
        flow1.packet.ethernet().ipv4().udp().vxlan().ethernet()
    )

    outer_eth.src.value = outer_src_mac
    outer_eth.dst.value = outer_dst_mac
    outer_eth.ether_type.value = ether_type

    ip.src.value = src_ip
    ip.dst.value = dst_ip

    udp.src_port.value = src_port
    udp.dst_port.value = dst_port

    vxlan.flags.value = flags
    vxlan.vni.value = vni

    inner_eth.src.value = inner_src_mac
    inner_eth.dst.value = inner_dst_mac

    # List
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name

    flags_list = [0, 15, 255]
    vni_list = [0, 15, 255, 4095, 65535, 1048575, 16777215]

    outer_eth, ip, udp, vxlan, inner_eth = (
        flow2.packet.ethernet().ipv4().udp().vxlan().ethernet()
    )

    outer_eth.src.value = outer_src_mac
    outer_eth.dst.value = outer_dst_mac
    outer_eth.ether_type.value = ether_type

    ip.src.value = src_ip
    ip.dst.value = dst_ip

    udp.src_port.value = src_port
    udp.dst_port.value = dst_port

    vxlan.flags.values = flags_list
    vxlan.vni.values = vni_list

    inner_eth.src.value = inner_src_mac
    inner_eth.dst.value = inner_dst_mac

    # Counter
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name

    outer_eth, ip, udp, vxlan, inner_eth = (
        flow3.packet.ethernet().ipv4().udp().vxlan().ethernet()
    )

    outer_eth.src.value = outer_src_mac
    outer_eth.dst.value = outer_dst_mac
    outer_eth.ether_type.value = ether_type

    ip.src.value = src_ip
    ip.dst.value = dst_ip

    udp.src_port.value = src_port
    udp.dst_port.value = dst_port

    vxlan.flags.increment.start = 0
    vxlan.flags.increment.step = 1
    vxlan.flags.increment.count = 256

    vxlan.vni.increment.start = 0
    vxlan.vni.increment.step = 1
    vxlan.vni.increment.count = 16777216

    inner_eth.src.value = inner_src_mac
    inner_eth.dst.value = inner_dst_mac

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "Flags": format(flags, "x"),
        "VNI": str(vni),
    }
    utils.validate_config(api, "f1", "vxlan", **f1_attrs)

    # list validation
    f2_attrs = {
        "Flags": [format(f, "x") for f in flags_list],
        "VNI": [str(v) for v in vni_list],
    }
    utils.validate_config(api, "f2", "vxlan", **f2_attrs)

    # counter validation
    f3_attrs = {
        "Flags": (
            format(vxlan.flags.increment.start, "x"),
            str(vxlan.flags.increment.step),
            str(vxlan.flags.increment.count),
        ),
        "VNI": (
            str(vxlan.vni.increment.start),
            str(vxlan.vni.increment.step),
            str(vxlan.vni.increment.count),
        ),
    }
    utils.validate_config(api, "f3", "vxlan", **f3_attrs)
