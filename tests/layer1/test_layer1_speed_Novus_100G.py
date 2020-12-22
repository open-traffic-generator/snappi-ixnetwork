import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.layer1 import *
from abstract_open_traffic_generator.control import *


@pytest.mark.skip(reason="Waiting for PR #178")
def test_layer1(api, options, utils):
    """Test that layer1 configuration settings are being applied correctly
    A user should be able to configure ports with/without locations.
    The expectation should be if a location is configured the user wants to
    connect but debug should allow for config creation without location.
    Ports with no location should not generate an error message.
    Ports with location should generate an error message if unable to connect.

    Validation: Validate the layer1 properties applied using Restpy
    """

    speed_type = {'speed_40_gbps': '40000',
                  'speed_100_gbps': '100000'}

    port1 = Port(name='port1', location=utils.settings.ports[0])
    port2 = Port(name='port2', location=utils.settings.ports[1])
    auto_negotiate = True
    ieee_media_defaults = False

    for speed in speed_type.keys():
        port1_l1 = Layer1(name='port1 settings',
                          port_names=[port1.name],
                          speed=speed,
                          auto_negotiate=auto_negotiate,
                          ieee_media_defaults=ieee_media_defaults)
        port2_l1 = Layer1(name='port2 settings',
                          port_names=[port2.name],
                          speed=speed,
                          auto_negotiate=auto_negotiate,
                          ieee_media_defaults=ieee_media_defaults)

        config = Config(ports=[port1, port2], layer1=[port1_l1, port2_l1],
                        options=options)
        api.set_state(State(ConfigState(config=config, state='set')))
        validate_layer1_config(api, utils.settings.ports, speed_type, speed,
                               auto_negotiate, ieee_media_defaults)


def validate_layer1_config(api,
                           ports,
                           speed_type,
                           speed,
                           auto_negotiate,
                           ieee_media_defaults):
    """
    Validate Layer1 Configs using Restpy
    """
    ixnetwork = api._ixnetwork
    port1 = ixnetwork.Vport.find()[0]
    port2 = ixnetwork.Vport.find()[1]
    type = port1.Type
    type = type[0].upper() + type[1:]
    ports_assigned = [vport.Location for vport in ixnetwork.Vport.find()]
    assert (all([vport.ActualSpeed == int(speed_type[speed])
                for vport in ixnetwork.Vport.find()]))
    assert ports_assigned == ports
    assert (eval(
        'port1.L1Config.' + type + '.EnableAutoNegotiation')) == auto_negotiate
    assert (eval(
        'port2.L1Config.' + type + '.EnableAutoNegotiation')) == auto_negotiate
    assert (eval(
        'port1.L1Config.' + type + '.IeeeL1Defaults')) == ieee_media_defaults
    assert (eval(
        'port2.L1Config.' + type + '.IeeeL1Defaults')) == ieee_media_defaults
