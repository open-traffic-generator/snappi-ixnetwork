import pytest


def test_device_stacking(serializer, tx_port):
    """Test the stacking of ngpf devices
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.device import Ethernet, Vlan, Ipv4, Device, DeviceGroup
    from abstract_open_traffic_generator.device import Pattern, Protocol

    eth1 = Ethernet(name='Eth1')
    vlan1 = Vlan(name='Vlan1')
    vlan2 = Vlan(name='Vlan2')
    vlan3 = Vlan(name='Vlan3')
    ipv41 = Ipv4(name='Ipv41')
    ipv42 = Ipv4(name='Ipv42')
    device = Device(name='Devices1',
        parent='DeviceGroup1',
        protocols=[
            Protocol(parent='Devices1', choice=eth1), 
            Protocol(parent=eth1.name, choice=vlan1), 
            Protocol(parent=vlan1.name, choice=vlan2), 
            Protocol(parent=vlan2.name, choice=vlan3), 
            Protocol(parent=vlan3.name, choice=ipv41),
            Protocol(parent=eth1.name, choice=ipv42)
        ]
    )
    device_group = DeviceGroup(name='DeviceGroup1', 
        ports=[tx_port.name],
        devices=[device])

    config = Config(
        devices=[device_group],
    )
    print(serializer.json(config))

    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
    # set the ixnetwork connection parameters
    api = IxNetworkApi('10.36.66.49', port=11009)
    # set the configuration on ixnetwork
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
