import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *


def test_layer1_fcoe(serializer, api):
    """Test that layer1 fcoe configuration settings are being applied correctly.
    """
    port1 = Port(name='port1', location='10.36.74.26;01;01')
    fcoe = Fcoe(flow_control_type='ieee_802_1qbb',
        pfc_delay_quanta=3,
        pfc_class_0='zero',
        pfc_class_1='three',
        pfc_class_4='seven')
    ethernet = Layer1(name='ethernet settings', 
        port_names=[port1.name], 
        choice=Ethernet(media='copper',
            speed='one_thousand_mbps',
            auto_negotiate=True),
        fcoe=fcoe)
    config = Config(ports=[port1], layer1=[ethernet])
    serializer.json(config)
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
