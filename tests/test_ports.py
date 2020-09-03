import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.port import *


def test_ports(serializer, api):
    ports = [
        Port(name='port1', location='10.36.74.26;01;01'),
        Port(name='port2', location='10.36.77.102;12;03'),
        Port(name='port no location')
    ]
    config = Config(ports=ports)
    api.set_config(None)
    api.set_config(config)
    results = api.get_results()
    for result in results.port:
        print(result)

if __name__ == '__main__':
    pytest.main(['-s', __file__])
