def test_vlan_double_tag(api, b2b_raw_config_vports, utils):
    """
    Configure a raw traffic with two vlan headers
    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """

    f = b2b_raw_config_vports.flows[0]
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    # Vlan fields config
    priority = 7
    cfi = 1
    vlan_id = 1

    f.packet.ethernet().vlan().vlan()
    eth, vlan, vlan1 = f.packet[0], f.packet[1], f.packet[2]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.value = priority

    vlan.cfi.value = cfi

    vlan.id.value = vlan_id

    vlan1.priority.value = priority

    vlan1.cfi.value = cfi

    vlan1.id.value = vlan_id

    api.set_config(b2b_raw_config_vports)

    attrs = {
        "VLAN Priority": str(priority),
        "Canonical Format Indicator": str(cfi),
        "VLAN-ID": str(vlan_id),
    }
    utils.validate_config(api, "f1", 1, **attrs)
    utils.validate_config(api, "f1", 2, **attrs)
