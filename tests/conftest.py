import pytest
import json
import yaml


API_SERVER='10.36.66.49'
API_SERVER_PORT=11009
TX_PORT_LOCATION=None #'10.36.74.26;02;13'
RX_PORT_LOCATION=None #'10.36.74.26;02;14'


@pytest.fixture(scope='session')
def serializer(request):
    """Popular serialization methods
    """
    class Serializer(object):
        def json(self, obj):
            """Return a json string serialization of obj
            """
            import json
            return json.dumps(obj, indent=2, default=lambda x: x.__dict__)

        def yaml(self, obj):
            """Return a yaml string serialization of obj
            """
            return yaml.dump(obj, indent=2)

        def json_to_dict(self, json_string):
            """Return a dict from a json string serialization
            """
            return json.loads(json_string)

        def yaml_to_dict(self, yaml_string):
            """Return a dict from a yaml string serialization
            """
            return yaml.load(yaml_string)
    return Serializer()


@pytest.fixture(scope='session')
def api():
    """Change this to the ip address and rest port of the 
    IxNetwork API Server to use for the api test fixture
    """
    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
    ixnetwork_api = IxNetworkApi(API_SERVER, port=API_SERVER_PORT)
    yield ixnetwork_api
    ixnetwork_api.assistant.Session.remove()


@pytest.fixture
def options():
    """Returns global options
    """
    from abstract_open_traffic_generator.config import Options
    from abstract_open_traffic_generator.port import Options as PortOptions
    return Options(PortOptions(location_preemption=True))


@pytest.fixture
def tx_port():
    """Returns a transmit port
    """
    from abstract_open_traffic_generator.port import Port
    return Port(name='Tx Port', location=TX_PORT_LOCATION)


@pytest.fixture
def rx_port():
    """Returns a receive port
    """
    from abstract_open_traffic_generator.port import Port
    return Port(name='Rx Port', location=RX_PORT_LOCATION)


@pytest.fixture
def b2b_devices(tx_port, rx_port):
    """Returns a B2B tuple of tx port and rx port each with distinct device 
    groups of ethernet, ipv4, ipv6 and bgpv4 devices
    """
    from abstract_open_traffic_generator.device import Device, Ethernet, Vlan
    from abstract_open_traffic_generator.device import Ipv4, Ipv6, Bgpv4
    from abstract_open_traffic_generator.device import Pattern

    tx_port.devices = [
        Device(name='Tx Devices Eth',
            device_count=1,
            choice=Ethernet(name='Tx Eth', vlans=[Vlan(name='Tx Eth Vlan')])
        ),
        Device(name='Tx Devices Ipv4',
            device_count=2,
            choice=Ipv4(name='Tx Ipv4',
                address=Pattern('1.1.1.1'),
                prefix=Pattern('24'),
                gateway=Pattern('1.1.2.1'),
                ethernet=Ethernet(name='Tx Ipv4 Eth', vlans=[Vlan(name='Tx Ipv4 Vlan')])
            )
        ),
        Device(name='Tx Devices Ipv6',
            device_count=3,
            choice=Ipv6(name='Tx Ipv6',
                ethernet=Ethernet(name='Tx Ipv6 Eth', vlans=[Vlan(name='Tx Ipv6 Vlan')])
            )
        ),
        Device(name='Tx Devices Bgpv4',
            device_count=10,
            choice=Bgpv4(name='Tx Bgpv4', 
                ipv4= Ipv4(name='Tx Bgpv4 Ipv4',
                    ethernet=Ethernet(name='Tx Bgpv4 Eth', vlans=[Vlan(name='Tx Bgpv4 Vlan')])
                )
            )
        )
    ]
    rx_port.devices = [
        Device(name='Rx Devices Eth',
            device_count=1,
            choice=Ethernet(name='Rx Eth', vlans=[Vlan(name='Rx Eth Vlan')])
        ),
        Device(name='Rx Devices Ipv4',
            device_count=2,
            choice=Ipv4(name='Rx Ipv4',
                address=Pattern('1.1.1.1'),
                prefix=Pattern('24'),
                gateway=Pattern('1.1.2.1'),
                ethernet=Ethernet(name='Rx Ipv4 Eth', vlans=[Vlan(name='Rx Ipv4 Vlan')])
            )
        ),
        Device(name='Rx Devices Ipv6',
            device_count=3,
            choice=Ipv6(name='Rx Ipv6',
                ethernet=Ethernet(name='Rx Ipv6 Eth', vlans=[Vlan(name='Rx Ipv6 Vlan')])
            )
        ),
        Device(name='Rx Devices Bgpv4',
            device_count=10,
            choice=Bgpv4(name='Rx Bgpv4', 
                ipv4= Ipv4(name='Rx Bgpv4 Ipv4',
                    ethernet=Ethernet(name='Rx Bgpv4 Eth', vlans=[Vlan(name='Rx Bgpv4 Vlan')])
                )
            )
        )
    ]
    return [tx_port, rx_port]


@pytest.fixture
def b2b_simple_device(tx_port, rx_port):
    """Returns a B2B tuple of tx port and rx port each with distinct device
        groups of ethernet and ipv4 devices
        """
    from abstract_open_traffic_generator.device import Device, Ethernet, Vlan, Ipv4
    from abstract_open_traffic_generator.device import Pattern

    tx_port.devices = [
        Device(name='Tx Devices Ipv4',
               device_count=1,
               choice=Ipv4(name='Tx Ipv4',
                           address=Pattern('1.1.1.1'),
                           prefix=Pattern('24'),
                           gateway=Pattern('1.1.2.1'),
                           ethernet=Ethernet(name='Tx Ipv4 Eth', vlans=[Vlan(name='Tx Ipv4 Vlan')])
                           )
               )
    ]
    rx_port.devices = [
        Device(name='Rx Devices Ipv4',
               device_count=1,
               choice=Ipv4(name='Rx Ipv4',
                           address=Pattern('1.1.1.1'),
                           prefix=Pattern('24'),
                           gateway=Pattern('1.1.2.1'),
                           ethernet=Ethernet(name='Rx Ipv4 Eth', vlans=[Vlan(name='Rx Ipv4 Vlan')])
                           )
               ),
    ]
    return [tx_port, rx_port]