def test_fixed_vlan_fields(api, b2b_raw_config, utils):
    """
    Configure a raw vlan header fields with,
    - fixed pattern for all vlan fields

    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """

    f = b2b_raw_config.flows[0]
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    # Vlan fields config
    priority = 7
    cfi = 1
    vlan_id = 1

    f.packet.ethernet().vlan()
    eth, vlan = f.packet[0], f.packet[1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.value = priority

    vlan.cfi.value = cfi

    vlan.id.value = vlan_id

    vlan.tpid.value = vlan.tpid.X8100

    api.set_config(b2b_raw_config)

    attrs = {
        "VLAN Priority": str(priority),
        "Canonical Format Indicator": str(cfi),
        "VLAN-ID": str(vlan_id),
    }
    utils.validate_config(api, "vlan", **attrs)
