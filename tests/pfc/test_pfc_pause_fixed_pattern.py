import pytest


@pytest.mark.skip("skip until migrated to snappi")
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
    f.size = flow.Size(100)
    f.packet = [
        flow.Header(
            flow.PfcPause(
                src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                dst=flow.Pattern('00:AB:BC:AB:BC:AB'),
                ether_type=flow.Pattern('8100'),
                class_enable_vector=flow.Pattern('FF'),
                control_op_code=flow.Pattern('0101'),
                pause_class_0=flow.Pattern('FFFF'),
                pause_class_1=flow.Pattern('FFFF'),
                pause_class_2=flow.Pattern('FFFF'),
                pause_class_3=flow.Pattern('FFFF'),
                pause_class_4=flow.Pattern('FFFF'),
                pause_class_5=flow.Pattern('FFFF'),
                pause_class_6=flow.Pattern('FFFF'),
                pause_class_7=flow.Pattern('FFFF')
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)

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
    utils.validate_config(api, 0, **attrs)

    f.packet = [
        flow.Header(
            flow.PfcPause(
                src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                dst=flow.Pattern('00:AB:BC:AB:BC:AB'),
                ether_type=flow.Pattern('8100'),
                class_enable_vector=flow.Pattern('FF'),
                control_op_code=flow.Pattern('0101'),
                pause_class_0=flow.Pattern('0000'),
                pause_class_6=flow.Pattern('FFFF'),
            )
        )
    ]
    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'Destination address': '00:ab:bc:ab:bc:ab',
        'Source address': '00:ab:bc:ab:bc:ab',
        'Ethertype': '8100',
        'Control opcode': '101',
        'priority_enable_vector': 'ff',
        'PFC Queue 0': '0',
        'PFC Queue 1': '0',
        'PFC Queue 2': '0',
        'PFC Queue 3': '0',
        'PFC Queue 4': '0',
        'PFC Queue 5': '0',
        'PFC Queue 6': 'ffff',
        'PFC Queue 7': '0'
    }
    utils.validate_config(api, 0, **attrs)

    f.packet[0].pfcpause.pause_class_7 = flow.Pattern('3333')

    utils.apply_config(api, b2b_raw_config)

    attrs['PFC Queue 7'] = '3333'

    utils.validate_config(api, 0, **attrs)
