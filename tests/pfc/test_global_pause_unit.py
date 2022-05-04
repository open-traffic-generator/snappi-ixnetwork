def test_global_pause(api, b2b_raw_config_vports, utils):
    """
    Configure three flows with raw IPv4,
    - fixed src and dst IPv4 address
    - list src and dst IPv4 address
    - counter src and dst IPv4 address
    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    eth = flow1.packet.ethernetpause()[-1]
    eth.dst.value = "01:80:c2:00:00:01"
    eth.src.value = "00:AB:BC:AB:BC:AB"
    eth.control_op_code.value = 1
    eth.time.value = 65535
    api.set_config(b2b_raw_config_vports)

    attrs = {
        "Destination MAC Address": "01:80:c2:00:00:01",
        "Source MAC Address": "00:ab:bc:ab:bc:ab",
        "Ethernet-Type": "8808",
    }
    new_attrs = {
        "Destination address": "01:80:c2:00:00:01",
        "Source address": "00:ab:bc:ab:bc:ab",
        "Ethertype": "8808",
        "Control opcode": "1",
        "PAUSE Quanta": "ffff",
    }
    try:
        utils.validate_config(api, "f1", 0, **attrs)
    except KeyError:
        utils.validate_config(api, "f1", 0, **new_attrs)

    eth.dst.increment.start = "01:80:c2:00:00:01"
    eth.dst.increment.step = "00:00:00:01:00:00"
    eth.dst.increment.count = 10
    eth.src.increment.start = "00:AB:BC:AB:BC:AB"
    eth.src.increment.step = "00:00:00:01:00:00"
    eth.src.increment.count = 10

    api.set_config(b2b_raw_config_vports)

    attrs = {
        "Destination MAC Address": (
            "01:80:c2:00:00:01",
            "00:00:00:01:00:00",
            "10",
        ),
        "Source MAC Address": ("00:ab:bc:ab:bc:ab", "00:00:00:01:00:00", "10"),
        "Ethernet-Type": "8808",
        "PFC Queue": "0",
    }
    new_attrs = {
        "Destination address": (
            "01:80:c2:00:00:01",
            "00:00:00:01:00:00",
            "10",
        ),
        "Source address": ("00:ab:bc:ab:bc:ab", "00:00:00:01:00:00", "10"),
        "Ethertype": "8808",
        "Control opcode": "1",
        "PAUSE Quanta": "ffff",
    }
    try:
        utils.validate_config(api, "f1", 0, **attrs)
    except KeyError:
        utils.validate_config(api, "f1", 0, **new_attrs)
