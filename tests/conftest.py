import pytest


@pytest.fixture(scope='module')
def serializer(request):
    class Serializer(object):
        def __init__(self, request):
            self.request = request
            self.test_name = getattr(request.node, "name")

        def json(self, obj):
            import json
            json_str = json.dumps(obj, indent=2, default=lambda x: x.__dict__)
            return '\n[%s] %s: %s\n' % (self.test_name, obj.__class__.__name__, json_str)
        
        def yaml(self, obj):
            import yaml
            yaml_str = yaml.dump(obj, indent=2)
            return '\n[%s] %s: %s\n' % (self.test_name, obj.__class__.__name__, yaml_str)

    return Serializer(request)            


@pytest.fixture(scope='module')
def tx_port():
    from abstract_open_traffic_generator.port import Port
    return Port(name='Tx Port', 
        location='10.36.74.17;2;1', 
        link_state='up',
        capture_state='stopped')


@pytest.fixture(scope='module')
def rx_port():
    from abstract_open_traffic_generator.port import Port
    return Port(name='Rx Port', 
        location='10.36.74.17;2;2',
        link_state='up',
        capture_state='stopped')


@pytest.fixture(scope='module')
def b2b_ipv4_device_groups(tx_port, rx_port):
    """Returns a B2B tuple of tx devices to rx devices
    Protocol stack is eth + vlan + ipv4
    Number of devices is 1
    """
    from abstract_open_traffic_generator.device import Ethernet, Vlan, Ipv4, Device, DeviceGroup
    from abstract_open_traffic_generator.device import Pattern, Protocol
    ethernet = Ethernet(name='Tx Ethernet')
    vlan = Vlan(name='Tx Vlan', 
        id=Pattern('1'))
    ipv4 = Ipv4(name='Tx Ipv4',
        address=Pattern('1.1.1.1'),
        prefix=Pattern('24'),
        gateway=Pattern('1.1.2.1'))
    device = Device(name='Tx Devices',
        devices_per_port=1,
        parent=None,
        protocols=[
            Protocol(parent=None, choice=ethernet), 
            Protocol(parent=ethernet.name, choice=vlan), 
            Protocol(parent=vlan.name, choice=ipv4)
        ]
    )
    tx_device_group = DeviceGroup(name='Tx Device Group', 
        ports=[tx_port.name],
        devices=[device])
    
    ethernet = Ethernet(name='Rx Ethernet')
    vlan = Vlan(name='Rx Vlan', 
        id=Pattern('1'))
    ipv4 = Ipv4(name='Rx Ipv4',
        address=Pattern('1.1.2.1'),
        prefix=Pattern('24'),
        gateway=Pattern('1.1.1.1'))
    device = Device(name='Rx Devices',
        devices_per_port=1,
        parent=None,
        protocols=[
            Protocol(parent=None, choice=ethernet), 
            Protocol(parent=ethernet.name, choice=vlan), 
            Protocol(parent=vlan.name, choice=ipv4)
        ]
    )
    rx_device_group = DeviceGroup(name='Rx Device Group', 
        ports=[rx_port.name],
        devices=[device])

    return [tx_device_group, rx_device_group]
