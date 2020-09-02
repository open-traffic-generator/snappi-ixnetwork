import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *


def test_layer1(serializer, api):
    """Test that layer1 configuration settings are being applied correctly
    """
    port1 = Port(name='port1')
    ethernet = Layer1(name='ethernet settings', 
        ports=[port1.name], 
        choice=Ethernet(media='fiber',
            speed='one_hundred_hd_mbps',
            auto_negotiate=False))
    port2 = Port(name='port2')
    uhd = Layer1(name='uhd settings', 
        ports=[port2.name], 
        choice=OneHundredGbe(ieee_media_defaults=True, 
            auto_negotiate=True,
            link_training=True,
            rs_fec=True,
            speed='one_hundred_gbps'))
    config = Config(ports=[port1, port2], layer1=[ethernet, uhd])
    serializer.json(config)
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
