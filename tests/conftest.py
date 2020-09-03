import pytest
import json
from collections import namedtuple

API_SERVER='10.36.66.49'
API_SERVER_PORT=11009
TX_PORT_LOCATION=None # '10.36.74.26:02;13'
RX_PORT_LOCATION=None # '10.36.74.26:02;14'


@pytest.fixture(scope='session')
def api():
    """Change this to the ip address and rest port of the 
    IxNetwork API Server to use for the api test fixture
    """
    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
    return IxNetworkApi(API_SERVER, port=API_SERVER_PORT)


@pytest.fixture(scope='session')
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

        def obj(self, json_string): 
            a_dict = json.loads(json_string)
            return json.loads(json_string, object_hook=self._object_hook)
        
        def _object_hook(self, converted_dict): 
            return namedtuple('X', converted_dict.keys())(*converted_dict.values())

    return Serializer(request)


@pytest.fixture(scope='session')
def tx_port():
    from abstract_open_traffic_generator.port import Port
    return Port(name='Tx Port', location=TX_PORT_LOCATION)


@pytest.fixture(scope='session')
def rx_port():
    from abstract_open_traffic_generator.port import Port
    return Port(name='Rx Port', location=RX_PORT_LOCATION)


@pytest.fixture
def tx_config(tx_port):
    from abstract_open_traffic_generator.device import DeviceGroup, Device
    from abstract_open_traffic_generator.config import Config

    device = Device(name='tx devices',
                    devices_per_port=10)
    device_group = DeviceGroup(name='tx devicegroup',
                               port_names=[tx_port.name],
                               devices=[device])
    return Config(
        ports=[tx_port],
        device_groups=[device_group]
    )


@pytest.fixture(scope='module')
def b2b_ipv4_device_groups(tx_port, rx_port):
    """Returns a B2B tuple of tx devices to rx devices
    Protocol stack is eth + vlan + ipv4
    Number of devices is 1
    """
    from abstract_open_traffic_generator.device import DeviceGroup, Device
    from abstract_open_traffic_generator.device import Ethernet, Vlan, Ipv4
    from abstract_open_traffic_generator.device import Pattern

    ipv4 = Ipv4(name='Tx Ipv4',
                address=Pattern('1.1.1.1'),
                prefix=Pattern('24'),
                gateway=Pattern('1.1.2.1'))
    vlan = Vlan(name='Tx Vlan',
                id=Pattern('3'))
    ethernet = Ethernet(name='Tx Ethernet',
                        vlans=[vlan],
                        ipv4=ipv4)
    device = Device(name='Tx Devices',
                    devices_per_port=1,
                    ethernets=[ethernet])
    tx_device_group = DeviceGroup(name='Tx Device Group',
                                  port_names=[tx_port.name],
                                  devices=[device])

    ipv4 = Ipv4(name='Rx Ipv4',
                address=Pattern('1.1.2.1'),
                prefix=Pattern('24'),
                gateway=Pattern('1.1.1.1'))
    vlan = Vlan(name='Rx Vlan',
                id=Pattern('3'))
    ethernet = Ethernet(name='Rx Ethernet',
                        vlans=[vlan],
                        ipv4=ipv4)
    device = Device(name='Rx Devices',
                    devices_per_port=1,
                    ethernets=[ethernet])
    rx_device_group = DeviceGroup(name='Rx Device Group',
                                  port_names=[rx_port.name],
                                  devices=[device])

    return [tx_device_group, rx_device_group]
