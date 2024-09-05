def test_fixed_pfc_pause(api, b2b_raw_config, utils):
    """
    Configure a pfc pause header fields,
    - with fixed pattern

    Validate,
    - Fetch the pfc pause header config via restpy and validate
    against expected
    """
    f = b2b_raw_config.flows[0]
    f.name = "pfcpause"
    f.size.fixed = 100
    f.packet.pfcpause()
    pfc = f.packet[0]
    pfc.src.value = "00:AB:BC:AB:BC:AB"
    pfc.dst.value = "00:AB:BC:AB:BC:AB"
    pfc.ether_type.value = 3000
    pfc.class_enable_vector.value = 255
    pfc.control_op_code.value = 257
    pfc.pause_class_0.value = 65535
    pfc.pause_class_1.value = 65535
    pfc.pause_class_2.value = 65535
    pfc.pause_class_3.value = 65535
    pfc.pause_class_4.value = 65535
    pfc.pause_class_5.value = 65535
    pfc.pause_class_6.value = 65535
    pfc.pause_class_7.value = 65535
    api.set_config(b2b_raw_config)
    attrs = {
        "Destination address": "00:ab:bc:ab:bc:ab",
        "Source address": "00:ab:bc:ab:bc:ab",
        "Ethertype": "bb8",
        "Control opcode": "101",
        "priority_enable_vector": "ff",
        "PFC Queue 0": "ffff",
        "PFC Queue 1": "ffff",
        "PFC Queue 2": "ffff",
        "PFC Queue 3": "ffff",
        "PFC Queue 4": "ffff",
        "PFC Queue 5": "ffff",
        "PFC Queue 6": "ffff",
        "PFC Queue 7": "ffff",
    }
    utils.validate_config(api, "pfcpause", 0, **attrs)

    pfc.pause_class_7.value = 3333

    api.set_config(b2b_raw_config)

    attrs["PFC Queue 7"] = "d05"

    utils.validate_config(api, "pfcpause", 0, **attrs)
