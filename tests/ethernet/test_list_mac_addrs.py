def test_list_mac_addrs(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - list pattern for src and dst MAC address

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    flow = b2b_raw_config.flows[0]
    count = 10
    step = "05:00:00:02:01:00"
    src = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0c:29:e3:53:ea", step, count, True
    )
    dst = utils.mac_or_ip_addr_from_counter_pattern(
        "00:0c:29:e3:53:f4", step, count, True
    )
    eth_type = ["8100", "88a8", "9100", "9200"]

    # import snappi
    # flow = snappi.Api().config().flows.flow()[-1]
    flow.packet.ethernet()
    eth = flow.packet[-1]
    eth.src.values = src
    eth.dst.values = dst
    eth.ether_type.values = [int(x, 16) for x in eth_type]
    api.set_config(b2b_raw_config)
    attrs = {
        "Destination MAC Address": dst,
        "Source MAC Address": src,
        "Ethernet-Type": eth_type,
    }
    utils.validate_config(api, "ethernet", **attrs)
