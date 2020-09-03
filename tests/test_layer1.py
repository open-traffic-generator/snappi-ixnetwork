import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *


def test_layer1(serializer, api):
    """Test that layer1 configuration settings are being applied correctly
    A user should be able to configure ports with/without locations.
    The expectation should be if a location is configured the user wants to 
    connect but debug should allow for config creation without location.
    Ports with no location should not generate an error message.
    Ports with location should generate an error message if unable to connect.
    """
    port1 = Port(name='port1', location='10.36.74.26;01;01')
    port2 = Port(name='port2', location='10.36.77.102;12;03')
    port3 = Port(name='port no location')
    ethernet = Layer1(name='ethernet settings', 
        port_names=[port1.name, port3.name], 
        choice=Ethernet(media='copper',
            speed='one_thousand_mbps',
            auto_negotiate=True))
    uhd = Layer1(name='uhd settings', 
        port_names=[port2.name], 
        choice=OneHundredGbe(ieee_media_defaults=False, 
            auto_negotiate=False,
            link_training=False,
            rs_fec=True,
            speed='one_hundred_gbps'))
    config = Config(ports=[port1, port2, port3], layer1=[ethernet, uhd])
    serializer.json(config)
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
