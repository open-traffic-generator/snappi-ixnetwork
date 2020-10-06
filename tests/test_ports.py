import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.control import *


def test_ports(serializer, api, options):
    ports = [
        Port(name='port1', location='10.36.74.26;01;01'),
        Port(name='port2', location='10.36.77.102;12;03'),
        Port(name='port no location')
    ]
    config = Config(ports=ports, options=options)
    api.set_state(State(ConfigState(config=config, state='set')))

if __name__ == '__main__':
    pytest.main(['-s', __file__])
