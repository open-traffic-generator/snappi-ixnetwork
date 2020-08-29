import pytest
from abstract_open_traffic_generator.device import Ethernet, Pattern


def test_device_ethernet_fixed(serializer, api, tx_config):
    """Test the creation of ngpf ethernet device properties
    """
    eth = Ethernet(name='eth1',
                   mac=Pattern('00:00:fa:ce:fa:ce'),
                   mtu=Pattern('1200'))
    tx_config.device_groups[0].devices[0].ethernets = [eth]
    print(serializer.json(tx_config))
    api.set_config(tx_config)


def test_device_ethernet_value_list(serializer, api, tx_config):
    """Test the creation of ngpf ethernet device properties
    """
    eth = Ethernet(name='eth1',
                   mac=Pattern(['00:00:aa:aa:aa:aa', '00:00:bb:bb:bb:bb']),
                   mtu=Pattern(['1200', '1201', '1202']))
    tx_config.device_groups[0].devices[0].ethernets = [eth]
    print(serializer.json(tx_config))
    api.set_config(tx_config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
