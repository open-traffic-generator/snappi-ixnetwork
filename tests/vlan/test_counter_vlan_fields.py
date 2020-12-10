from abstract_open_traffic_generator import flow


def test_counter_vlan_fields(api, b2b_raw_config, utils):
    """
    Configure a raw vlan header fields with,
    - counter pattern for all vlan fields

    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """

    f = b2b_raw_config.flows[0]
    source = '00:0C:29:E3:53:EA'
    destination = '00:0C:29:E3:53:F4'
    ether_type = '8100'

    # Vlan fields config
    priority = flow.Counter(
        start='0',
        step='1',
        count=8
    )

    cfi = flow.Counter(
        start='0',
        step='1',
        count=2
    )

    vlan_id = flow.Counter(
        start='1',
        step='1',
        count=4094,
    )

    protocol = flow.Counter(
        start='8100',
        step='1',
        count=10
    )

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
        'VLAN Priority': (
            priority.start, priority.step, str(priority.count)
        ),
        'Canonical Format Indicator': (
            cfi.start, cfi.step, str(cfi.count)
        ),
        'VLAN-ID': (
            vlan_id.start, vlan_id.step, str(vlan_id.count)
        ),
        'Protocol-ID': (
            protocol.start, protocol.step, str(protocol.count)
        )
    }
    utils.validate_config(api, 'vlan', **attrs)
