import pytest


@pytest.mark.l1_manual
@pytest.mark.parametrize('speed', ['speed_50_gbps', 'speed_100_gbps',
                                   'speed_200_gbps', 'speed_400_gbps'])
def test_layer1(api, utils, speed):
    """Test that layer1 configuration settings are being applied correctly
    A user should be able to configure ports with/without locations.
    The expectation should be if a location is configured the user wants to
    connect but debug should allow for config creation without location.
    Ports with no location should not generate an error message.
    Ports with location should generate an error message if unable to connect.

    Validation: Validate the layer1 properties applied using Restpy
    """
    speed_type = {'speed_50_gbps': '50000',
                  'speed_100_gbps': '100000',
                  'speed_200_gbps': '200000',
                  'speed_400_gbps': '400000'}
    port_locations = get_port_locations(utils.settings.ports[0])
    location = port_locations[speed]
    config = api.config()
    port = config.ports.port(name='port1',
                             location=location)[-1]
    auto_negotiate = True
    ieee_media_defaults = False
    link_training = False
    if speed in ['speed_50_gbps', 'speed_200_gbps']:
        auto_negotiate = False
    if speed in ['speed_100_gbps', 'speed_400_gbps']:
        link_training = True
    port_l1 = config.layer1.layer1()[-1]
    port_l1.name = 'port1 settings'
    port_l1.port_names = [port.name]
    port_l1.speed = speed
    port_l1.media = utils.settings.media
    port_l1.auto_negotiate = auto_negotiate
    port_l1.ieee_media_defaults = ieee_media_defaults
    port_l1.auto_negotiation.link_training = link_training
    api.set_config(config)
    validate_layer1_config(api, port_locations[speed], speed_type, speed,
                           auto_negotiate, ieee_media_defaults,
                           link_training)


def get_port_locations(location):
    """
    Takes input port location given by the user and returns a dictionary with
    speed mapped to port location as per RG
    Ex: get_port_location_for_speed("10.36.87.215;1;57")
    output:
    {'speed_50_gbps': '10.36.87.215;1;57',
     'speed_100_gbps': '10.36.87.215;1;25',
     'speed_200_gbps': '10.36.87.215;1;9',
     'speed_400_gbps': '10.36.87.215;1;1'}
    """
    port_400g = ""
    port_200g = ""
    port_100g = ""
    port_50g = ""
    port_location = {}
    port_num = int(location.split(";")[2])

    rg_fanout200g = {}
    rg_fanout200g_starting_port = 9
    rg_fanout100g = {}
    rg_fanout100g_starting_port = 25
    rg_fanout50g = {}
    rg_fanout50_starting_port = 57

    for rg in range(1, 9):
        rg_fanout200g[rg] = list(range(rg_fanout200g_starting_port,
                                       rg_fanout200g_starting_port + 2))
        rg_fanout200g_starting_port += 2

    for rg in range(1, 9):
        rg_fanout100g[rg] = list(range(rg_fanout100g_starting_port,
                                       rg_fanout100g_starting_port + 4))
        rg_fanout100g_starting_port += 4

    for rg in range(1, 9):
        rg_fanout50g[rg] = list(range(rg_fanout50_starting_port,
                                      rg_fanout50_starting_port + 2))
        rg_fanout50_starting_port += 2

    if port_num < 9:
        port_400g = port_num
        port_200g = rg_fanout200g[port_num][0]
        port_100g = rg_fanout100g[port_num][0]
        port_50g = rg_fanout50g[port_num][0]
    elif port_num > 8 and port_num < 25:
        port_200g = port_num
        port_400g = next(key for key in rg_fanout200g
                         if port_num in rg_fanout200g[key])
        port_100g = rg_fanout100g[port_400g][0]
        port_50g = rg_fanout50g[port_400g][0]
    elif port_num > 24 and port_num < 57:
        port_100g = port_num
        port_400g = next(key for key in rg_fanout100g
                         if port_num in rg_fanout100g[key])
        port_200g = rg_fanout200g[port_400g][0]
        port_50g = rg_fanout50g[port_400g][0]
    elif port_num > 56 and port_num < 73:
        port_50g = port_num
        port_400g = next(key for key in rg_fanout50g
                         if port_num in rg_fanout50g[key])
        port_200g = rg_fanout200g[port_400g][0]
        port_100g = rg_fanout100g[port_400g][0]

    port_400g = ";".join(location.split(";")[0:2]) + \
        ";" + str(port_400g)
    port_200g = ";".join(location.split(";")[0:2]) + ";" + str(port_200g)
    port_100g = ";".join(location.split(";")[0:2]) + ";" + str(port_100g)
    port_50g = ";".join(location.split(";")[0:2]) + ";" + str(port_50g)
    port_location['speed_400_gbps'] = port_400g
    port_location['speed_200_gbps'] = port_200g
    port_location['speed_100_gbps'] = port_100g
    port_location['speed_50_gbps'] = port_50g
    return port_location


def validate_layer1_config(api,
                           port_location,
                           speed_type,
                           speed,
                           auto_negotiate,
                           ieee_media_defaults,
                           link_training):
    """
    Validate Layer1 Configs using Restpy
    """
    ixnetwork = api._ixnetwork
    port = ixnetwork.Vport.find()[0]
    type = (port.Type)[0].upper() + (port.Type)[1:]
    assert port.Location == port_location
    assert port.ActualSpeed == int(speed_type[speed])
    assert getattr(port.L1Config, type).EnableAutoNegotiation \
        == auto_negotiate
    assert getattr(port.L1Config, type).IeeeL1Defaults \
        == ieee_media_defaults
    assert getattr(port.L1Config, type).LinkTraining \
        == link_training
