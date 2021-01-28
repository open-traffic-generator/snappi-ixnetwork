import pytest


@pytest.mark.skip("skip until migrated to snappi")
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
    priority = '7'
    cfi = '1'
    vlan_id = '1'
    protocol = '8100'

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
