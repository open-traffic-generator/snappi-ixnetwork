from abstract_open_traffic_generator import flow


def test_list_mac_addrs(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - list pattern for src and dst MAC address

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    f = b2b_raw_config.flows[0]
    count = 10
    step = '05:00:00:02:01:00'
    src = utils.mac_or_ip_addr_from_counter_pattern(
        '00:0c:29:e3:53:ea', step, count, True
    )
    dst = utils.mac_or_ip_addr_from_counter_pattern(
        '00:0c:29:e3:53:f4', step, count, True
    )
    eth_type = ['8100', '88a8', '9100', '9200']

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(src),
                dst=flow.Pattern(dst),
                ether_type=flow.Pattern(eth_type)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'Destination MAC Address': dst,
        'Source MAC Address': src,
        'Ethernet-Type': eth_type,
    }
    utils.validate_config(api, 'ethernet', **attrs)
