import pytest
from abstract_open_traffic_generator.device import *
from abstract_open_traffic_generator.config import Config


def test_device_ipv4_fixed(serializer, api):
    """Test the creation of ngpf vlan device properties
    """
    ipv4 = Ipv4(name='ipv4',
        address=Pattern('1.1.1.1'), 
        prefix=Pattern('24'),
        gateway=Pattern('1.1.2.1'))
    eth = Ethernet(name='eth',
                   mac=Pattern('00:00:fa:ce:fa:ce'),
                   mtu=Pattern('1200'),
                   ipv4=ipv4)
    device = Device(name='device', devices_per_port=10, ethernets=[eth])
    device_group = DeviceGroup(name='devicegroup', devices=[device])
    config = Config(device_groups=[device_group])
    api.set_config(config)


def test_device_ipv4value_list(serializer, api):
    """Test the creation of ngpf vlan device properties
    """
    ipv4 = Ipv4(name='ipv4',
        address=Pattern(['1.1.1.1', '1.1.1.6', '1.1.1.7']), 
        prefix=Pattern(['24', '32', '16']),
        gateway=Pattern(['1.1.2.1', '1.1.2.6', '1.1.2.7']))
    eth = Ethernet(name='eth',
                   mac=Pattern(['00:00:aa:aa:aa:aa', '00:00:bb:bb:bb:bb']),
                   mtu=Pattern(['1200', '1201', '1202']),
                   ipv4=ipv4)
    device = Device(name='device', devices_per_port=10, ethernets=[eth])
    device_group = DeviceGroup(name='devicegroup', devices=[device])
    config = Config(device_groups=[device_group])
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
