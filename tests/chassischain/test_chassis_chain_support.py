import pytest


@pytest.mark.skip("chassis chain is not supported in ci")
def test_chassis_chain_support(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):


    # Chassischain configuration
    ixnconfig = api.ixnet_specific_config
    chassis_chain1 = ixnconfig.chassis_chains.add()
    chassis_chain1.primary = "10.36.78.236"
    chassis_chain1.topology = chassis_chain1.STAR
    secondary1 = chassis_chain1.secondary.add()
    secondary1.location = "10.36.78.141"
    secondary1.sequence_id = "2"
    secondary1.cable_length = "6"
    # secondary2 = chassis_chain1.secondary.add()
    # secondary2.location = "10.39.32.161"
    # secondary2.sequence_id = "3"
    # secondary2.cable_length = "3"
    # chassis_chain2 = ixnconfig.chassis_chains.add()
    # chassis_chain2.primary = "10.39.32.151"
    # chassis_chain2.topology = chassis_chain2.DAISY
    # secondary3 = chassis_chain2.secondary.add()
    # secondary3.location = "10.39.32.162"
    # secondary3.sequence_id = "4"
    # secondary3.cable_length = "3"
    # secondary4 = chassis_chain2.secondary.add()
    # secondary4.location = "10.39.32.163"
    # secondary4.sequence_id = "5"
    # secondary4.cable_length = "3"

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

    chassis = api._ixnetwork.AvailableHardware.Chassis
    chassis.find(Hostname="^%s$" % chassis_chain1.primary)
    assert len(chassis) == 1
    assert chassis[0].ChainTopology == chassis_chain1.STAR

    chassis.find(Hostname="^%s$" % secondary1.location)
    assert len(chassis) == 1
    assert chassis[0].SequenceId == secondary1.sequence_id
    assert chassis[0].CableLength == secondary1.cable_length
