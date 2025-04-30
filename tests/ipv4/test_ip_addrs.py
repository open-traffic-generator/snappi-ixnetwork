@pytest.mark.skip(
    reason="CI-Testing"
)
def test_ip_addrs(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three flows with raw IPv4 ,
    - fixed src and dst IPv4 address
    - list src and dst IPv4 address
    - counter src and dst IPv4 address
    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"
    flow1.packet.ethernet().ipv4()
    eth = flow1.packet[0]
    ipv4 = flow1.packet[1]
    eth.src.value = src
    eth.dst.value = dst
    ipv4.src.value = src_ip
    ipv4.dst.value = dst_ip

    # list
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    step = "05:00:00:02:01:00"
    src_lst = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:EA", step, 5, True
    )
    dst_lst = utils.mac_or_ip_addr_from_counter_pattern(
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
    flow2.packet.ethernet().ipv4()
    eth = flow2.packet[0]
    ipv4 = flow2.packet[1]
    eth.src.values = src_lst
    eth.dst.values = dst_lst
    ipv4.src.values = src_ip_list
    ipv4.dst.values = dst_ip_list

    # counter
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    count = 10
    step = "05:00:00:02:01:00"
    src_cnt = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:EA", step, count, True
    )
    dst_cnt = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0C:29:E3:53:F4", step, count, True
    )

    step = "0.0.1.0"
    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"

    flow3.packet.ethernet().ipv4()
    eth = flow3.packet[0]
    ipv4 = flow3.packet[1]
    eth.src.values = src_cnt
    eth.dst.values = dst_cnt

    ipv4.src.increment.start = src_ip
    ipv4.src.increment.step = step
    ipv4.src.increment.count = count
    ipv4.dst.decrement.start = dst_ip
    ipv4.dst.decrement.step = step
    ipv4.dst.decrement.count = count

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "Destination Address": dst_ip,
        "Source Address": src_ip,
    }
    utils.validate_config(api, "f1", "ipv4", **f1_attrs)

    # list validation
    f2_attrs = {
        "Destination Address": dst_ip_list,
        "Source Address": src_ip_list,
    }
    utils.validate_config(api, "f2", "ipv4", **f2_attrs)

    # counter validation
    f3_attrs = {
        "Destination Address": (dst_ip, step, str(count)),
        "Source Address": (src_ip, step, str(count)),
    }
    utils.validate_config(api, "f3", "ipv4", **f3_attrs)
