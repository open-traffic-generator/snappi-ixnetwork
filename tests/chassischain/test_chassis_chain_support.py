import pytest

# @pytest.mark.skip("chassis chain is not supported in ci")
def test_counter_ip_dscp(api, b2b_raw_config, utils):
    """
    Configure a Chassis Chain setup

    Validate,
    - Fetch the chassis chain config set via restpy and validate
      against expected
    """
    ixnconfig = api.ixnet_specific_config
    chassis_chain1 = ixnconfig.chassis_chains.add()
    chassis_chain1.primary = "10.36.78.236"
    chassis_chain1.topology = chassis_chain1.STAR
    secondary1 = chassis_chain1.secondary.add()
    secondary1.location = "10.36.78.141"
    secondary1.sequence_id = "2"
    secondary1.cable_length = "6"
    # secondary2 = chassis_chain1.secondary.add()
    # secondary2.location = "10.39.32.161"
    # secondary2.sequence_id = "3"
    # secondary2.cable_length = "3"
    # chassis_chain2 = ixnconfig.chassis_chains.add()
    # chassis_chain2.primary = "10.39.32.151"
    # chassis_chain2.topology = chassis_chain2.DAISY
    # secondary3 = chassis_chain2.secondary.add()
    # secondary3.location = "10.39.32.162"
    # secondary3.sequence_id = "4"
    # secondary3.cable_length = "3"
    # secondary4 = chassis_chain2.secondary.add()
    # secondary4.location = "10.39.32.163"
    # secondary4.sequence_id = "5"
    # secondary4.cable_length = "3"

    f = b2b_raw_config.flows[0]
    f.packet.ethernet().ipv4()
    ipv4 = f.packet[1]
    phb = (
        ["DEFAULT"]
        + ["CS%d" % i for i in range(1, 4)]
        + ["AF%d" % i for j in range(11, 51, 10) for i in range(j, j + 3)]
    )
    phb = phb + ["EF46"]
    af_ef = [
        "10",
        "12",
    ]
    for i, p in enumerate(phb):
        # https://github.com/open-traffic-generator/snappi/issues/25
        # currently assigning the choice as work around
        ipv4.priority.choice = ipv4.priority.DSCP
        ipv4.priority.dscp.phb.value = getattr(ipv4.priority.dscp.phb, p)
        ipv4.priority.dscp.ecn.value = 3
        api.set_config(b2b_raw_config)
        if i == 0:
            attrs = {"Default PHB": str(i)}
            attrs["ipv4.header.priority.ds.phb.defaultPHB.unused"] = "3"
        elif i > 0 and i < 8:
            attrs = {"Class selector PHB": str(i * 8)}
            attrs["ipv4.header.priority.ds.phb.classSelectorPHB.unused"] = "3"
        elif i > 7 and i < (len(phb) - 1):
            attrs = {"Assured forwarding PHB": af_ef[i - 8]}
            attrs[
                "ipv4.header.priority.ds.phb.assuredForwardingPHB.unused"
            ] = "3"
        else:
            attrs = {"Expedited forwarding PHB": af_ef[-1]}
            attrs[
                "ipv4.header.priority.ds.phb.expeditedForwardingPHB.unused"
            ] = "3"

        utils.validate_config(api, "f1", "ipv4", **attrs)

        chassis = api._ixnetwork.AvailableHardware.Chassis
        chassis.find(Hostname="^%s$" % chassis_chain1.primary)
        assert len(chassis) == 1
        assert chassis[0].ChainTopology == chassis_chain1.STAR

        chassis.find(Hostname="^%s$" % secondary1.location)
        assert len(chassis) == 1
        assert chassis[0].SequenceId == secondary1.sequence_id
        assert chassis[0].CableLength == secondary1.cable_length
