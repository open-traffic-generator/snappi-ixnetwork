def test_fixed_mac_addrs(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - fixed src, dst MAC address and ether type

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    flow = b2b_raw_config.flows[0]
    source = '00:0C:29:E3:53:EA'
    destination = '00:0C:29:E3:53:F4'
    ether_type = '8100'

    # import snappi
    # flow = snappi.Api().config().flows.flow()[-1]
    flow.packet.ethernet()
    eth = flow.packet[-1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type
    api.set_config(b2b_raw_config)
    attrs = {
        'Destination MAC Address': destination.lower(),
        'Source MAC Address': source.lower(),
        'Ethernet-Type': ether_type.lower(),
    }
    utils.validate_config(api, 'ethernet', **attrs)
