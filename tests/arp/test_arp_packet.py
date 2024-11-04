import pytest
import allure

@pytest.mark.runonly
def test_arp_packet(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    flow1 = b2b_raw_config_vports.flows[0]
    sender_hardware_addr = "00:0C:29:E3:53:EA"
    target_hardware_addr = "00:0C:29:E3:54:EA"
    sender_protocol_addr = "10.1.1.2"
    target_protocol_addr = "20.1.1.2"
    flow1.packet.ethernet().arp()
    flow1_arp = flow1.packet[-1]
    flow1_arp.sender_hardware_addr.value = sender_hardware_addr
    flow1_arp.sender_protocol_addr.value = sender_protocol_addr
    flow1_arp.target_hardware_addr.value = target_hardware_addr
    flow1_arp.target_protocol_addr.value = target_protocol_addr

    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    hardware_type = 2
    protocol_type = 801
    hardware_length = 7
    protocol_length = 5
    operation = 2
    mac_step = "00:00:00:00:01:00"
    ip_step = "0.0.0.1"
    count = 10
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    flow2.packet.ethernet().arp()
    flow2_arp = flow2.packet[-1]
    flow2_arp.hardware_type.value = hardware_type
    flow2_arp.protocol_type.value = protocol_type
    flow2_arp.hardware_length.value = hardware_length
    flow2_arp.protocol_length.value = protocol_length
    flow2_arp.operation.value = operation
    flow2_arp.sender_hardware_addr.increment.start = sender_hardware_addr
    flow2_arp.sender_hardware_addr.increment.step = mac_step
    flow2_arp.sender_hardware_addr.increment.count = count
    flow2_arp.sender_protocol_addr.increment.start = sender_protocol_addr
    flow2_arp.sender_protocol_addr.increment.step = ip_step
    flow2_arp.sender_protocol_addr.increment.count = count
    flow2_arp.target_hardware_addr.decrement.start = target_hardware_addr
    flow2_arp.target_hardware_addr.decrement.step = mac_step
    flow2_arp.target_hardware_addr.decrement.count = count
    flow2_arp.target_protocol_addr.decrement.start = target_protocol_addr
    flow2_arp.target_protocol_addr.decrement.step = ip_step
    flow2_arp.target_protocol_addr.decrement.count = count

    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3_count = 4
    flow3_step = "05:00:00:02:01:00"
    sender_hardware_addr_list = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0c:29:e3:53:ea", flow3_step, flow3_count, True
    )
    target_hardware_addr_list = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0c:29:e3:53:f4", flow3_step, flow3_count, True
    )
    sender_protocol_addr_list = ["10.10.0.1", "10.10.0.2", "10.10.0.3"]
    target_protocol_addr_list = ["20.20.0.1", "20.20.0.2", "20.20.0.3"]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    flow3.packet.ethernet().arp()
    flow3_arp = flow3.packet[-1]
    flow3_arp.sender_hardware_addr.values = sender_hardware_addr_list
    flow3_arp.sender_protocol_addr.values = sender_protocol_addr_list
    flow3_arp.target_hardware_addr.values = target_hardware_addr_list
    flow3_arp.target_protocol_addr.values = target_protocol_addr_list

    api.set_config(b2b_raw_config_vports)

    f1_attrs = {
        "ethernetARP.header.srcHardwareAddress": sender_hardware_addr.lower(),
        "ethernetARP.header.dstHardwareAddress": target_hardware_addr.lower(),
        "ethernetARP.header.srcIP": sender_protocol_addr,
        "ethernetARP.header.dstIP": target_protocol_addr,
    }
    utils.validate_config(api, "f1", "ethernetARP", **f1_attrs)

    f2_attrs = {
        "ethernetARP.header.hardwareType": "{:x}".format(int(hardware_type)),
        "ethernetARP.header.protocolType": "{:x}".format(int(protocol_type)),
        "ethernetARP.header.hardwareAddressLength": "{:x}".format(
            int(hardware_length)
        ),
        "ethernetARP.header.protocolAddressLength": "{:x}".format(
            int(protocol_length)
        ),
        "ethernetARP.header.opCode": str(operation),
        "ethernetARP.header.srcHardwareAddress": (
            sender_hardware_addr.lower(),
            mac_step,
            str(count),
        ),
        "ethernetARP.header.dstHardwareAddress": (
            target_hardware_addr.lower(),
            mac_step,
            str(count),
        ),
        "ethernetARP.header.srcIP": (
            sender_protocol_addr,
            ip_step,
            str(count),
        ),
        "ethernetARP.header.dstIP": (
            target_protocol_addr,
            ip_step,
            str(count),
        ),
    }
    utils.validate_config(api, "f2", "ethernetARP", **f2_attrs)

    f3_attrs = {
        "ethernetARP.header.srcHardwareAddress": sender_hardware_addr_list,
        "ethernetARP.header.dstHardwareAddress": target_hardware_addr_list,
        "ethernetARP.header.srcIP": sender_protocol_addr_list,
        "ethernetARP.header.dstIP": target_protocol_addr_list,
    }
    utils.validate_config(api, "f3", "ethernetARP", **f3_attrs)


if __name__ == "__main__":
    pytest.main(["-s", __file__])
