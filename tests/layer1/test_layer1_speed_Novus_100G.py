import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.layer1 import *
from abstract_open_traffic_generator.control import *


@pytest.mark.e2e
def test_layer1(api, options, utils):
    """Test that layer1 configuration settings are being applied correctly
    A user should be able to configure ports with/without locations.
    The expectation should be if a location is configured the user wants to
    connect but debug should allow for config creation without location.
    Ports with no location should not generate an error message.
    Ports with location should generate an error message if unable to connect.

    Validation: Validate the layer1 properties applied using Restpy
    """
    speed_type = {'speed_10_gbps': '10000',
                  'speed_25_gbps': '25000',
                  'speed_40_gbps': '40000',
                  'speed_100_gbps': '100000'}
    port1 = Port(name='port1', location=utils.settings.ports[0])
    port2 = Port(name='port2', location=utils.settings.ports[1])
    speed = utils.settings.speed
    auto_negotiate = True
    ieee_media_defaults = False
    link_training = False
    rs_fec = True
    if speed in ['speed_10_gbps', 'speed_25_gbps', 'speed_100_gbps']:
        auto_negotiate = False
    port1_l1 = Layer1(name='port1 settings',
                      port_names=[port1.name],
                      speed=speed,
                      auto_negotiate=auto_negotiate,
                      ieee_media_defaults=ieee_media_defaults,
                      auto_negotiation=AutoNegotiation(
                          link_training=link_training,
                          rs_fec=rs_fec))
    port2_l1 = Layer1(name='port2 settings',
                      port_names=[port2.name],
                      speed=speed,
                      auto_negotiate=auto_negotiate,
                      ieee_media_defaults=ieee_media_defaults)

    config = Config(ports=[port1, port2], layer1=[port1_l1, port2_l1],
                    options=options)
    api.set_state(State(ConfigState(config=config, state='set')))
    validate_layer1_config(api, utils.settings.ports, speed_type, speed,
                           auto_negotiate, ieee_media_defaults,
                           link_training, rs_fec)


def validate_layer1_config(api,
                           ports,
                           speed_type,
                           speed,
                           auto_negotiate,
                           ieee_media_defaults,
                           link_training,
                           rs_fec):
    """
    Validate Layer1 Configs using Restpy
    """
    ixnetwork = api._ixnetwork
    port1 = ixnetwork.Vport.find()[0]
    port2 = ixnetwork.Vport.find()[1]
    type = (port1.Type)[0].upper() + (port1.Type)[1:]
    ports_assigned = [vport.Location for vport in ixnetwork.Vport.find()]
    assert (all([vport.ActualSpeed == int(speed_type[speed])
                for vport in ixnetwork.Vport.find()]))
    assert ports_assigned == ports
    assert getattr(port1.L1Config, type).EnableAutoNegotiation \
        == auto_negotiate
    assert getattr(port2.L1Config, type).EnableAutoNegotiation \
        == auto_negotiate
    assert getattr(port1.L1Config, type).IeeeL1Defaults \
        == ieee_media_defaults
    assert getattr(port2.L1Config, type).IeeeL1Defaults \
        == ieee_media_defaults
    if speed == 'speed_100_gbps':
        assert getattr(port1.L1Config, type).EnableRsFec \
            == rs_fec
        assert getattr(port1.L1Config, type).LinkTraining \
            == link_training

