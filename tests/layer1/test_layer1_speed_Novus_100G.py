import pytest


@pytest.mark.l1_manual
@pytest.mark.parametrize(
    "speed",
    ["speed_10_gbps", "speed_25_gbps", "speed_40_gbps", "speed_100_gbps"],
)
def test_layer1(api, utils, speed):
    """Test that layer1 configuration settings are being applied correctly
    A user should be able to configure ports with/without locations.
    The expectation should be if a location is configured the user wants to
    connect but debug should allow for config creation without location.
    Ports with no location should not generate an error message.
    Ports with location should generate an error message if unable to connect.

    Validation: Validate the layer1 properties applied using Restpy
    """
    speed_type = {
        "speed_10_gbps": "10000",
        "speed_25_gbps": "25000",
        "speed_40_gbps": "40000",
        "speed_50_gbps": "50000",
        "speed_100_gbps": "100000",
    }
    port_locations = get_port_locations(utils.settings.ports[0])
    location = port_locations[speed]
    config = api.config()
    port = config.ports.port(name="port1", location=location)[-1]
    auto_negotiate = True
    ieee_media_defaults = False
    link_training = False
    rs_fec = True
    if speed in ["speed_10_gbps", "speed_25_gbps", "speed_100_gbps"]:
        auto_negotiate = False
    port_l1 = config.layer1.layer1()[-1]
    port_l1.name = "port1 settings"
    port_l1.port_names = [port.name]
    port_l1.speed = speed
    port_l1.media = utils.settings.media
    port_l1.auto_negotiate = auto_negotiate
    port_l1.ieee_media_defaults = ieee_media_defaults
    port_l1.auto_negotiation.link_training = link_training
    port_l1.auto_negotiation.rs_fec = rs_fec
    api.set_config(config)
    validate_layer1_config(
        api,
        port_locations[speed],
        speed_type,
        speed,
        auto_negotiate,
        ieee_media_defaults,
        link_training,
        rs_fec,
    )


def get_port_locations(location):
    """
    Takes input port location given by the user and returns a dictionary with
    speed mapped to port location as per RG
    Ex: get_port_location_for_speed("10.36.87.215;1;53")
    output:
    {'speed_10_gbps': '10.36.87.215;1;33',
     'speed_25_gbps': '10.36.87.215;1;33',
     'speed_40_gbps': '10.36.87.215;1;7',
     'speed_100_gbps': '10.36.87.215;1;7',
     'speed_50_gbps': '10.36.87.215;1;53'}
    """
    port_40g_100g = ""
    port_10g_25g = ""
    port_50g = ""
    port_location = {}
    port_num = int(location.split(";")[2])

    rg_fanout4 = {}
    rg_fanout4_starting_port = 9
    rg_fanout2 = {}
    rg_fanout2_starting_port = 41

    for rg in range(1, 9):
        rg_fanout4[rg] = list(
            range(rg_fanout4_starting_port, rg_fanout4_starting_port + 4)
        )
        rg_fanout4_starting_port += 4

    for rg in range(1, 9):
        rg_fanout2[rg] = list(
            range(rg_fanout2_starting_port, rg_fanout2_starting_port + 2)
        )
        rg_fanout2_starting_port += 2

    if port_num < 9:
        port_40g_100g = port_num
        port_10g_25g = rg_fanout4[port_num][0]
        port_50g = rg_fanout2[port_num][0]
    elif port_num > 8 and port_num < 41:
        port_10g_25g = port_num
        port_40g_100g = next(
            key for key in rg_fanout4 if port_num in rg_fanout4[key]
        )
        port_50g = rg_fanout2[port_40g_100g][0]
    elif port_num > 40 and port_num < 57:
        port_40g_100g = next(
            key for key in rg_fanout2 if port_num in rg_fanout2[key]
        )
        port_10g_25g = rg_fanout4[port_40g_100g][0]
        port_50g = port_num

    port_40g_100g = (
        ";".join(location.split(";")[0:2]) + ";" + str(port_40g_100g)
    )
    port_10g_25g = ";".join(location.split(";")[0:2]) + ";" + str(port_10g_25g)
    port_50g = ";".join(location.split(";")[0:2]) + ";" + str(port_50g)
    port_location["speed_10_gbps"] = port_10g_25g
    port_location["speed_25_gbps"] = port_10g_25g
    port_location["speed_40_gbps"] = port_40g_100g
    port_location["speed_100_gbps"] = port_40g_100g
    port_location["speed_50_gbps"] = port_50g
    return port_location


def validate_layer1_config(
    api,
    port_location,
    speed_type,
    speed,
    auto_negotiate,
    ieee_media_defaults,
    link_training,
    rs_fec,
):
    """
    Validate Layer1 Configs using Restpy
    """
    ixnetwork = api._ixnetwork
    port = ixnetwork.Vport.find()[0]
    type = (port.Type)[0].upper() + (port.Type)[1:]
    assert port.Location == port_location
    assert port.ActualSpeed == int(speed_type[speed])
    assert getattr(port.L1Config, type).EnableAutoNegotiation == auto_negotiate
    assert getattr(port.L1Config, type).IeeeL1Defaults == ieee_media_defaults
    if speed == "speed_100_gbps":
        assert getattr(port.L1Config, type).EnableRsFec == rs_fec
        assert getattr(port.L1Config, type).LinkTraining == link_training
