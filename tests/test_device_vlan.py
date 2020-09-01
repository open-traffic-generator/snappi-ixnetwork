import pytest
from abstract_open_traffic_generator.device import *
from abstract_open_traffic_generator.config import Config


def test_device_vlan_fixed(serializer, api):
    """Test the creation of ngpf vlan device properties
    """
    vlan = Vlan(name='vlan1',
        tpid=Pattern('9300'), 
        priority=Pattern('3'),
        id=Pattern('999'))
    eth = Ethernet(name='eth1',
                   mac=Pattern('00:00:fa:ce:fa:ce'),
                   mtu=Pattern('1200'),
                   vlans=[vlan])
    device = Device(name='device', devices_per_port=10, ethernets=[eth])
    device_group = DeviceGroup(name='devicegroup', devices=[device])
    config = Config(device_groups=[device_group])
    api.set_config(config)


def test_device_vlan_value_list(serializer, api):
    """Test the creation of ngpf vlan device properties
    """
    vlan = Vlan(name='vlan1',
        tpid=Pattern('9100'), 
        priority=Pattern(['0', '2', '1']),
        id=Pattern(['66', '777', '88']))
    eth = Ethernet(name='eth1',
                   mac=Pattern(['00:00:aa:aa:aa:aa', '00:00:bb:bb:bb:bb']),
                   mtu=Pattern(['1200', '1201', '1202']),
                   vlans=[vlan])
    device = Device(name='device', devices_per_port=10, ethernets=[eth])
    device_group = DeviceGroup(name='devicegroup', devices=[device])
    config = Config(device_groups=[device_group])
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
