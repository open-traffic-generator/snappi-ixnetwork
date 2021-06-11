def test_fixed_pfc_pause(api, b2b_raw_config, utils):
    """
    Configure a pfc pause header fields,
    - with fixed pattern

    Validate,
    - Fetch the pfc pause header config via restpy and validate
    against expected
    """
    f = b2b_raw_config.flows[0]
    f.name = 'pfcpause'
    f.size.fixed = 100
    f.packet.pfcpause()
    pfc = f.packet[0]
    pfc.src.value = '00:AB:BC:AB:BC:AB'
    pfc.dst.value = '00:AB:BC:AB:BC:AB'
    pfc.ether_type.value = '8100'
    pfc.class_enable_vector.value = 'FF'
    pfc.control_op_code.value = '0101'
    pfc.pause_class_0.value = 'FFFF'
    pfc.pause_class_1.value = 'FFFF'
    pfc.pause_class_2.value = 'FFFF'
    pfc.pause_class_3.value = 'FFFF'
    pfc.pause_class_4.value = 'FFFF'
    pfc.pause_class_5.value = 'FFFF'
    pfc.pause_class_6.value = 'FFFF'
    pfc.pause_class_7.value = 'FFFF'
    api.set_config(b2b_raw_config)
    attrs = {
        'Destination address': '00:ab:bc:ab:bc:ab',
        'Source address': '00:ab:bc:ab:bc:ab',
        'Ethertype': '8100',
        'Control opcode': '101',
        'priority_enable_vector': 'ff',
        'PFC Queue 0': 'ffff',
        'PFC Queue 1': 'ffff',
        'PFC Queue 2': 'ffff',
        'PFC Queue 3': 'ffff',
        'PFC Queue 4': 'ffff',
        'PFC Queue 5': 'ffff',
        'PFC Queue 6': 'ffff',
        'PFC Queue 7': 'ffff'
    }
    utils.validate_config(api, 'pfcpause', 0, **attrs)

    pfc.pause_class_7.value = '3333'

    api.set_config(b2b_raw_config)

    attrs['PFC Queue 7'] = '3333'

    utils.validate_config(api, 'pfcpause', 0, **attrs)
