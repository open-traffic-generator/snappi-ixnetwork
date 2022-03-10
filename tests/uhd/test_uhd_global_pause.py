import pytest


@pytest.mark.uhd
def test_uhd_global_pause(api, b2b_raw_config_vports, utils):
    """
    Configure Ethernet Pause flow and validate the snappi
    config is applied in UHD
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
    utils.validate_config(api, "f1", 0, **attrs)

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
    utils.validate_config(api, "f1", 0, **attrs)
