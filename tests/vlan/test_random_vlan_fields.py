from abstract_open_traffic_generator import flow


def test_fixed_vlan_fields(api, b2b_raw_config, utils):
    """
    Configure a raw vlan header fields with,
    - fixed pattern for all vlan fields

    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """

    f = b2b_raw_config.flows[0]
    source = '00:0C:29:E3:53:EA'
    destination = '00:0C:29:E3:53:F4'
    ether_type = '8100'

    # Vlan fields config
    # - min (str): TBD
    # - max (str): TBD
    # - step (Union[float, int]): TBD
    # - seed (str): TBD
    # - count (Union[float, int]): TBD

    priority = flow.Random(
        min='0',
        max='7',
        step=1,
        seed='0',
        count=10
    )
    cfi = flow.Random(
        min='0',
        max='1',
        step=1,
        seed='1',
        count=10
    )
    vlan_id = flow.Random(
        min='1',
        max='100',
        step=1,
        seed='1',
        count=4094
    )
    protocol = flow.Random(
        min='0',
        max='100',
        step=1,
        seed='1',
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
            priority.min, priority.max, str(priority.step),
            priority.seed, str(priority.count)
        ),
        'Canonical Format Indicator': (
            cfi.min, cfi.max, str(cfi.step), cfi.seed, str(cfi.count)
        ),
        'VLAN-ID': (
            vlan_id.min, vlan_id.max, str(vlan_id.step),
            vlan_id.seed, str(vlan_id.count)
        ),
        'Protocol-ID': (
            protocol.min, protocol.max, str(protocol.step),
            protocol.seed, str(protocol.count)
        )
    }
    utils.validate_config(api, 'vlan', **attrs)
