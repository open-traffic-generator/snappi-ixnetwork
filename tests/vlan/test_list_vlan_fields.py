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
    ether_type = 33024

    # Vlan fields config
    priority = [i for i in range(7)]
    cfi = [0, 1]
    vlan_id = [i for i in range(4094)]

    f.packet.ethernet().vlan()
    eth, vlan = f.packet[0], f.packet[1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.values = priority

    vlan.cfi.values = cfi

    vlan.id.values = vlan_id

    api.set_config(b2b_raw_config)

    attrs = {
        'VLAN Priority': [str(p) for p in priority],
        'Canonical Format Indicator': [str(c) for c in cfi],
        'VLAN-ID': [str(v) for v in vlan_id],
    }
    utils.validate_config(api, 'vlan', **attrs)
