def test_counter_vlan_fields(api, b2b_raw_config, utils):
    """
    Configure a raw vlan header fields with,
    - counter pattern for all vlan fields

    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """

    f = b2b_raw_config.flows[0]
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    f.packet.ethernet().vlan()
    eth, vlan = f.packet[0], f.packet[1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.increment.start = 0
    vlan.priority.increment.step = 1
    vlan.priority.increment.count = 8

    vlan.cfi.increment.start = 0
    vlan.cfi.increment.step = 1
    vlan.cfi.increment.count = 2

    vlan.id.increment.start = 1
    vlan.id.increment.step = 1
    vlan.id.increment.count = 4094

    attrs = {
        "VLAN Priority": (
            str(vlan.priority.increment.start),
            str(vlan.priority.increment.step),
            str(vlan.priority.increment.count),
        ),
        "Canonical Format Indicator": (
            str(vlan.cfi.increment.start),
            str(vlan.cfi.increment.step),
            str(vlan.cfi.increment.count),
        ),
        "VLAN-ID": (
            str(vlan.id.increment.start),
            str(vlan.id.increment.step),
            str(vlan.id.increment.count),
        ),
    }

    api.set_config(b2b_raw_config)
    utils.validate_config(api, "vlan", **attrs)
