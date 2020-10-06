import pytest
from abstract_open_traffic_generator.port import Port
from abstract_open_traffic_generator.device import *
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.control import *


def test_device_ipv4_fixed(serializer, api):
    """Test the creation of ipv4 fixed properties
    """
    port = Port('port 1')
    port.devices = [
        Device(name='device',
            device_count=15,
            choice=Ipv4(name='ipv4',
                address=Pattern('1.1.1.1'), 
                prefix=Pattern('24'),
                gateway=Pattern('1.1.2.1'),
                ethernet=Ethernet(name='eth',
                    mac=Pattern('00:00:fa:ce:fa:ce'),
                    mtu=Pattern('1200')
                )
            )
        )
    ]
    config = Config(ports=[port])
    api.set_state(State(ConfigState(config=config, state='set')))


def test_device_ipv4value_list(serializer, api):
    """Test the creation of ipv4 value list properties
    """
    port = Port('port 1')
    port.devices = [
        Device(name='device',
            device_count=20,
            choice=Ipv4(name='ipv4',
                address=Pattern(['1.1.1.1', '1.1.1.6', '1.1.1.7']), 
                prefix=Pattern(['24', '32', '16']),
                gateway=Pattern(['1.1.2.1', '1.1.2.6', '1.1.2.7']),
                ethernet=Ethernet(name='eth',
                    mac=Pattern(['00:00:aa:aa:aa:aa', '00:00:bb:bb:bb:bb']),
                    mtu=Pattern(['1200', '1201', '1202'])
                )
            )
        )
    ]
    config = ConfigState(ports=[port])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
