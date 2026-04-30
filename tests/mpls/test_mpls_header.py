def test_mpls_header(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw MPLS flows with ethernet + mpls + ipv4 stack:
    - f1: fixed label, traffic_class, bottom_of_stack, time_to_live
    - f2: list pattern for label and time_to_live
    - f3: increment pattern for label, decrement pattern for time_to_live

    Validate each flow's MPLS header attributes via restpy.
    """
    # ------------------------------------------------------------------
    # Flow 1 – fixed values
    # ------------------------------------------------------------------
    label_fixed = 100
    tc_fixed = 5
    bos_fixed = 1
    ttl_fixed = 64

    flow1 = b2b_raw_config_vports.flows[0]
    flow1.size.fixed = 128
    flow1.duration.fixed_packets.packets = 100
    flow1.rate.percentage = 10

    eth1, mpls1, ip1 = flow1.packet.ethernet().mpls().ipv4()
    eth1.src.value = "00:11:22:33:44:01"
    eth1.dst.value = "00:11:22:33:44:02"
    mpls1.label.value = label_fixed
    mpls1.traffic_class.value = tc_fixed
    mpls1.bottom_of_stack.value = bos_fixed
    mpls1.time_to_live.value = ttl_fixed
    ip1.src.value = "10.0.0.1"
    ip1.dst.value = "10.0.0.2"

    # ------------------------------------------------------------------
    # Flow 2 – list pattern
    # ------------------------------------------------------------------
    label_list = [200, 201, 202]
    ttl_list = [32, 48, 64]

    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_names = [rx_vport.name]
    flow2.size.fixed = 128
    flow2.duration.fixed_packets.packets = 100
    flow2.rate.percentage = 10

    eth2, mpls2, ip2 = flow2.packet.ethernet().mpls().ipv4()
    eth2.src.value = "00:11:22:33:44:01"
    eth2.dst.value = "00:11:22:33:44:02"
    mpls2.label.values = label_list
    mpls2.traffic_class.value = 0
    mpls2.bottom_of_stack.value = 1
    mpls2.time_to_live.values = ttl_list
    ip2.src.value = "10.0.0.1"
    ip2.dst.value = "10.0.0.2"

    # ------------------------------------------------------------------
    # Flow 3 – increment / decrement counters
    # ------------------------------------------------------------------
    label_cnt = (300, 1, 10)   # start, step, count
    ttl_cnt = (128, 2, 10)     # start, step, count

    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_names = [rx_vport.name]
    flow3.size.fixed = 128
    flow3.duration.fixed_packets.packets = 100
    flow3.rate.percentage = 10

    eth3, mpls3, ip3 = flow3.packet.ethernet().mpls().ipv4()
    eth3.src.value = "00:11:22:33:44:01"
    eth3.dst.value = "00:11:22:33:44:02"
    mpls3.label.increment.start = label_cnt[0]
    mpls3.label.increment.step = label_cnt[1]
    mpls3.label.increment.count = label_cnt[2]
    mpls3.traffic_class.value = 0
    mpls3.bottom_of_stack.value = 1
    mpls3.time_to_live.decrement.start = ttl_cnt[0]
    mpls3.time_to_live.decrement.step = ttl_cnt[1]
    mpls3.time_to_live.decrement.count = ttl_cnt[2]
    ip3.src.value = "10.0.0.1"
    ip3.dst.value = "10.0.0.2"

    # ------------------------------------------------------------------
    # Flow 4 – multiple stacked MPLS labels (outer / middle / inner)
    # ------------------------------------------------------------------
    # Stack: ethernet + mpls_outer + mpls_mid + mpls_inner + ipv4
    # Indices:    0          1           2           3         4
    outer_label, mid_label, inner_label = 100, 200, 300
    outer_tc, mid_tc, inner_tc = 3, 5, 7
    outer_ttl, mid_ttl, inner_ttl = 60, 55, 50

    flow4 = b2b_raw_config_vports.flows.flow(name="f4")[-1]
    flow4.tx_rx.port.tx_name = tx_vport.name
    flow4.tx_rx.port.rx_names = [rx_vport.name]
    flow4.size.fixed = 128
    flow4.duration.fixed_packets.packets = 100
    flow4.rate.percentage = 10

    eth4, mpls4a, mpls4b, mpls4c, ip4 = (
        flow4.packet.ethernet().mpls().mpls().mpls().ipv4()
    )
    eth4.src.value = "00:11:22:33:44:01"
    eth4.dst.value = "00:11:22:33:44:02"

    mpls4a.label.value = outer_label
    mpls4a.traffic_class.value = outer_tc
    mpls4a.bottom_of_stack.value = 0
    mpls4a.time_to_live.value = outer_ttl

    mpls4b.label.value = mid_label
    mpls4b.traffic_class.value = mid_tc
    mpls4b.bottom_of_stack.value = 0
    mpls4b.time_to_live.value = mid_ttl

    mpls4c.label.value = inner_label
    mpls4c.traffic_class.value = inner_tc
    mpls4c.bottom_of_stack.value = 1
    mpls4c.time_to_live.value = inner_ttl

    ip4.src.value = "10.0.0.1"
    ip4.dst.value = "10.0.0.2"

    # ------------------------------------------------------------------
    # Push config
    # ------------------------------------------------------------------
    api.set_config(b2b_raw_config_vports)

    # ------------------------------------------------------------------
    # Validate – fixed
    # ------------------------------------------------------------------
    f1_attrs = {
        "Label Value": str(label_fixed),
        "MPLS Exp": str(tc_fixed),
        "Bottom of Stack Bit": str(bos_fixed),
        "Time To Live": str(ttl_fixed),
    }
    utils.validate_config(api, "f1", "mpls", **f1_attrs)

    # ------------------------------------------------------------------
    # Validate – list
    # ------------------------------------------------------------------
    f2_attrs = {
        "Label Value": [str(l) for l in label_list],
        "Time To Live": [str(t) for t in ttl_list],
    }
    utils.validate_config(api, "f2", "mpls", **f2_attrs)

    # ------------------------------------------------------------------
    # Validate – increment / decrement
    # ------------------------------------------------------------------
    f3_attrs = {
        "Label Value": tuple(map(str, label_cnt)),
        "Time To Live": tuple(map(str, ttl_cnt)),
    }
    utils.validate_config(api, "f3", "mpls", **f3_attrs)

    # ------------------------------------------------------------------
    # Validate – multiple stacked MPLS labels (by stack index)
    # Stack layout: ethernet(0) + mpls_outer(1) + mpls_mid(2) + mpls_inner(3) + ipv4(4)
    # ------------------------------------------------------------------
    outer_attrs = {
        "Label Value": str(outer_label),
        "MPLS Exp": str(outer_tc),
        "Bottom of Stack Bit": "0",
        "Time To Live": str(outer_ttl),
    }
    utils.validate_config(api, "f4", 1, **outer_attrs)

    mid_attrs = {
        "Label Value": str(mid_label),
        "MPLS Exp": str(mid_tc),
        "Bottom of Stack Bit": "0",
        "Time To Live": str(mid_ttl),
    }
    utils.validate_config(api, "f4", 2, **mid_attrs)

    inner_attrs = {
        "Label Value": str(inner_label),
        "MPLS Exp": str(inner_tc),
        "Bottom of Stack Bit": "1",
        "Time To Live": str(inner_ttl),
    }
    utils.validate_config(api, "f4", 3, **inner_attrs)
