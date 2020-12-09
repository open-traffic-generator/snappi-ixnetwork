from abstract_open_traffic_generator import flow


def test_list_vlan_fields(api, b2b_raw_config, utils):
    """
    Configure a raw vlan header fields with,
    - list pattern for all vlan fields

    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """

    f = b2b_raw_config.flows[0]
    source = '00:0C:29:E3:53:EA'
    destination = '00:0C:29:E3:53:F4'
    ether_type = '8100'

    # Vlan fields config
    priority = [str(i) for i in range(7)]
    cfi = ['0', '1']
    vlan_id = [str(i) for i in range(4094)]
    protocol = ['8100', '9100', '8200']

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(source),
                dst=flow.Pattern(destination),
                ether_type=flow.Pattern(ether_type)
            )
        ),
        flow.Header(
            flow.Vlan(
                priority=flow.Pattern(priority),
                cfi=flow.Pattern(cfi),
                id=flow.Pattern(vlan_id),
                protocol=flow.Pattern(protocol)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)

    attrs = {
        'VLAN Priority': priority,
        'Canonical Format Indicator': cfi,
        'VLAN-ID': vlan_id,
        'Protocol-ID': protocol
    }
    utils.validate_config(api, 'vlan', **attrs)
