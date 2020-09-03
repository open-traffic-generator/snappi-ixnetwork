import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.port import *


def test_ports(serializer, api):
    port1 = Port(name='ethernet port 1',
        location='10.36.74.26;02;13',
        link_state='up')
    port2 = Port(name='ethernet port 2',
        location='10.36.74.26;02;14',
        link_state='up')
    layer1 = Layer1(name='layer1', 
        ports=[port1.name, port2.name],
        choice=Ethernet(media='copper', auto_negotiate=True))
    config = Config(ports=[port1, port2], layer1=[layer1])
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
