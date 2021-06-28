def test_counter_mac_addrs(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - counter pattern for src and dst MAC address and ether type

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    flow = b2b_raw_config.flows[0]
    count = 10
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"
    step = "00:00:00:00:01:00"
    eth_type = 33024
    eth_step = 2

    flow.packet.ethernet()
    eth = flow.packet[-1]
    eth.src.increment.start = src
    eth.src.increment.step = step
    eth.src.increment.count = count
    eth.dst.decrement.start = dst
    eth.dst.decrement.step = step
    eth.dst.decrement.count = count
    eth.ether_type.increment.start = eth_type
    eth.ether_type.increment.step = eth_step
    eth.ether_type.increment.count = count
    api.set_config(b2b_raw_config)

    attrs = {
        "Destination MAC Address": (dst.lower(), step, str(count)),
        "Source MAC Address": (src.lower(), step, str(count)),
        "Ethernet-Type": ("{:x}".format(eth_type), str(eth_step), str(count)),
    }
    utils.validate_config(api, "ethernet", **attrs)
