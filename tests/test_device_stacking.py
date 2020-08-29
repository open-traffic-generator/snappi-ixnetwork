import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.device import *


def test_device_stacking(serializer, tx_port):
    """Test the stacking of ngpf devices
    """
    bgpv4 = Bgpv4(name='bgpv4')
    ipv4 = Ipv4(name='ipv4', 
        bgpv4=bgpv4)
    ipv61 = Ipv6(name='ipv6')
    vlan1 = Vlan(name='vlan1')
    vlan2 = Vlan(name='vlan2')
    vlan3 = Vlan(name='vlan3')
    eth1 = Ethernet(name='eth1', 
        vlans=[vlan1, vlan2, vlan3], 
        ipv4=ipv4, 
        ipv6=ipv61)
    ipv62 = Ipv6(name='ipv62')
    eth2 = Ethernet(name='eth2', ipv6=ipv62)
    device = Device(name='devices', 
        devices_per_port=1, 
        ethernets=[eth1, eth2])
    device_group = DeviceGroup(name='devicegroup', 
        ports=[tx_port.name],
        devices=[device])
    config = Config(
        ports=[tx_port],
        devices=[device_group]
    )
    print(serializer.json(config))

    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
    # set the ixnetwork connection parameters
    api = IxNetworkApi('10.36.66.49', port=11009)
    # set the configuration on ixnetwork
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
