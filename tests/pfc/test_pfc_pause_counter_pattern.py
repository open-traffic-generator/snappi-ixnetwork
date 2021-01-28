import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_counter_pfc_pause(api, b2b_raw_config, utils):
    """
    Configure a pfc pause header fields,
    - with counter pattern

    Validate,
    - Fetch the pfc pause header config via restpy and validate
    against expected
    """
    f = b2b_raw_config.flows[0]
    f.name = 'pfcpause'
    f.size = flow.Size(100)
    src = flow.Counter(
        start='00:AB:BC:AB:BC:AB',
        step='00:01:00:00:01:00',
        count=10
    )
    dst = flow.Counter(
        start='00:AB:BC:AB:BC:AB',
        step='00:01:00:00:01:00',
        count=10
    )
    ether_type = flow.Counter(
        start='8100',
        step='1',
        count=10
    )
    enable_vec = flow.Counter(
        start='FF',
        step='1',
        count=10
    )
    cl = flow.Counter(
        start='FFFF',
        step='1',
        count=10
    )

    f.packet = [
        flow.Header(
            flow.PfcPause(
                src=flow.Pattern(src),
                dst=flow.Pattern(dst),
                ether_type=flow.Pattern(ether_type),
                class_enable_vector=flow.Pattern(enable_vec),
                control_op_code=flow.Pattern('101'),
                pause_class_0=flow.Pattern(cl),
                pause_class_1=flow.Pattern(cl),
                pause_class_2=flow.Pattern(cl),
                pause_class_3=flow.Pattern(cl),
                pause_class_4=flow.Pattern(cl),
                pause_class_5=flow.Pattern(cl),
                pause_class_6=flow.Pattern(cl),
                pause_class_7=flow.Pattern(cl)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)

    attrs = {
        'Destination address': (
            dst.start.lower(), dst.step, str(dst.count)
        ),
        'Source address': (
            src.start.lower(), src.step, str(src.count)
        ),
        'Ethertype': (
            ether_type.start, ether_type.step, str(ether_type.count)
        ),
        'Control opcode': '101',
        'priority_enable_vector': (
            enable_vec.start.lower(), enable_vec.step, str(enable_vec.count)
        ),
        'PFC Queue 0': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 1': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 2': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 3': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 4': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 5': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 6': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
        'PFC Queue 7': (
            cl.start.lower(), cl.step, str(cl.count)
        ),
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

    f.packet[0].pfcpause.pause_class_7 = flow.Pattern(cl)

    utils.apply_config(api, b2b_raw_config)

    attrs['PFC Queue 7'] = (
        cl.start.lower(), cl.step, str(cl.count)
    )
    utils.validate_config(api, 0, **attrs)
