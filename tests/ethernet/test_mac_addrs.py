import pytest


def test_mac_addrs(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw ethernet flows with ,
    - fixed pattern for src and dst MAC address and ether type
    - list pattern for src and dst MAC address and ether type
    - counter pattern for src and dst MAC address and ether type
    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    flow1.packet.ethernet()
    eth = flow1.packet[-1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    # counter
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    count = 10
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"
    flow2_step = "00:00:00:00:01:00"
    eth_type = 33024
    eth_step = 2

    flow2.packet.ethernet()
    eth = flow2.packet[-1]
    eth.src.increment.start = src
    eth.src.increment.step = flow2_step
    eth.src.increment.count = count
    eth.dst.decrement.start = dst
    eth.dst.decrement.step = flow2_step
    eth.dst.decrement.count = count
    eth.ether_type.increment.start = eth_type
    eth.ether_type.increment.step = eth_step
    eth.ether_type.increment.count = count

    # list
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    count = 10
    flow3_step = "05:00:00:02:01:00"
    src_list = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0c:29:e3:53:ea", flow3_step, count, True
    )
    dst_list = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0c:29:e3:53:f4", flow3_step, count, True
    )
    eth_type_list = ["8100", "88a8", "9100", "9200"]

    flow3.packet.ethernet()
    flow3_eth = flow3.packet[-1]
    flow3_eth.src.values = src_list
    flow3_eth.dst.values = dst_list
    flow3_eth.ether_type.values = [int(x, 16) for x in eth_type_list]

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "Destination MAC Address": destination.lower(),
        "Source MAC Address": source.lower(),
        "Ethernet-Type": "{:x}".format(ether_type),
    }
    utils.validate_config(api, "f1", "ethernet", **f1_attrs)

    # counter validation
    f2_attrs = {
        "Destination MAC Address": (dst.lower(), flow2_step, str(count)),
        "Source MAC Address": (src.lower(), flow2_step, str(count)),
        "Ethernet-Type": ("{:x}".format(eth_type), str(eth_step), str(count)),
    }
    utils.validate_config(api, "f2", "ethernet", **f2_attrs)

    # list validation
    f3_attrs = {
        "Destination MAC Address": dst_list,
        "Source MAC Address": src_list,
        "Ethernet-Type": eth_type_list,
    }
    utils.validate_config(api, "f3", "ethernet", **f3_attrs)


if __name__ == "__main__":
    pytest.main(["-s", __file__])
