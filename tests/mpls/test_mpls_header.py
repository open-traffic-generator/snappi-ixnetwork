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
