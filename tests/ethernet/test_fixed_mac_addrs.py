from abstract_open_traffic_generator import flow


def test_fixed_mac_addrs(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - fixed src, dst MAC address and ether type

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    f = b2b_raw_config.flows[0]
    source = '00:0C:29:E3:53:EA'
    destination = '00:0C:29:E3:53:F4'
    ether_type = '8100'

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(source),
                dst=flow.Pattern(destination),
                ether_type=flow.Pattern(ether_type)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'Destination MAC Address': destination.lower(),
        'Source MAC Address': source.lower(),
        'Ethernet-Type': ether_type.lower(),
    }
    utils.validate_config(api, 'ethernet', **attrs)
