import pytest
import json
import yaml
import os
import collections
import sys
if sys.version_info[0] >= 3:
    unicode = str

IXNETWORK_OTG_PYTEST_CONF = {
    'api_server': '127.0.0.1',
    'api_server_port': 11009,
    'api_log_level': 'info',
    'license_servers': [],
    'tx_port_location': None,
    'rx_port_location': None
}


def pytest_addoption(parser):
    """Add command line options
    """
    for name, value in IXNETWORK_OTG_PYTEST_CONF.items():
        parser.addoption('--%s' % name,
                         action="store",
                         type=str,
                         default=value,
                         help=str(value))


def byteify(input):
    if isinstance(input, dict):
        return {key: byteify(value) for key, value in input.items()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode) and sys.version_info[0] == 2:
        return input.encode('utf-8')
    else:
        return input


def pytest_configure(config):
    """Process command line options
    Process IXNETWORK_OTG_PYTEST_CONF file if one exists
    """
    for key in IXNETWORK_OTG_PYTEST_CONF:
        IXNETWORK_OTG_PYTEST_CONF[key] = config.getoption(key)
    data = json.dumps(IXNETWORK_OTG_PYTEST_CONF)
    d = json.loads(data, object_hook=byteify)
    pytest.otg_conf = collections.namedtuple('otg', d.keys())(*d.values())
    conf_filename = os.environ.get('IXNETWORK_OTG_PYTEST_CONF', None)
    if conf_filename is not None:
        try:
            with open(conf_filename) as fid:
                data = json.dumps(yaml.safe_load(fid))
                d = json.loads(data, object_hook=byteify)
                otg_conf = collections.namedtuple('otg', d.keys())(*d.values())
                for key, value in otg_conf.items():
                    setattr(pytest.otg_conf, key, value)
        except Exception as e:
            print(e)
    print(
        'Using global IxNetwork open traffic generator pytest configuration options:'
    )
    print(pytest.otg_conf)


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
    api = IxNetworkApi(pytest.otg_conf.api_server,
                       port=pytest.otg_conf.api_server_port,
                       license_servers=pytest.otg_conf.license_servers,
                       log_level=pytest.otg_conf.api_log_level)
    yield api
    if api.assistant is not None:
        api.assistant.Session.remove()


@pytest.fixture(scope='session')
def options():
    """Returns global options
    """
    from abstract_open_traffic_generator.config import Options
    from abstract_open_traffic_generator.port import Options as PortOptions
    return Options(PortOptions(location_preemption=True))


@pytest.fixture(scope='session')
def tx_port():
    """Returns a transmit port
    """
    from abstract_open_traffic_generator.port import Port
    return Port(name='Tx Port', location=pytest.otg_conf.tx_port_location)


@pytest.fixture(scope='session')
def rx_port():
    """Returns a receive port
    """
    from abstract_open_traffic_generator.port import Port
    return Port(name='Rx Port', location=pytest.otg_conf.rx_port_location)


@pytest.fixture(scope='session')
def b2b_devices(tx_port, rx_port):
    """Returns a B2B tuple of tx devices and rx devices each with distinct device
    groups of ethernet, ipv4, ipv6 and bgpv4 devices
    """
    from abstract_open_traffic_generator.device import Device, Ethernet, Vlan
    from abstract_open_traffic_generator.device import Ipv4, Ipv6, Bgpv4
    from abstract_open_traffic_generator.device import Pattern

    devices = [
        Device(name='Tx Devices Eth',
               container_name=tx_port.name,
               device_count=1,
               choice=Ethernet(name='Tx Eth',
                               vlans=[Vlan(name='Tx Eth Vlan')])),
        Device(name='Tx Devices Ipv4',
               container_name=tx_port.name,
               device_count=2,
               choice=Ipv4(name='Tx Ipv4',
                           address=Pattern('1.1.1.1'),
                           prefix=Pattern('24'),
                           gateway=Pattern('1.1.2.1'),
                           ethernet=Ethernet(name='Tx Ipv4 Eth',
                                             vlans=[Vlan(name='Tx Ipv4 Vlan')
                                                    ]))),
        Device(name='Tx Devices Ipv6',
               container_name=tx_port.name,
               device_count=3,
               choice=Ipv6(name='Tx Ipv6',
                           ethernet=Ethernet(name='Tx Ipv6 Eth',
                                             vlans=[Vlan(name='Tx Ipv6 Vlan')
                                                    ]))),
        Device(name='Tx Devices Bgpv4',
               container_name=tx_port.name,
               device_count=10,
               choice=Bgpv4(name='Tx Bgpv4',
                            ipv4=Ipv4(name='Tx Bgpv4 Ipv4',
                                      ethernet=Ethernet(
                                          name='Tx Bgpv4 Eth',
                                          vlans=[Vlan(name='Tx Bgpv4 Vlan')
                                                 ])))),
        Device(name='Rx Devices Eth',
               container_name=rx_port.name,
               device_count=1,
               choice=Ethernet(name='Rx Eth',
                               vlans=[Vlan(name='Rx Eth Vlan')])),
        Device(name='Rx Devices Ipv4',
               container_name=rx_port.name,
               device_count=2,
               choice=Ipv4(name='Rx Ipv4',
                           address=Pattern('1.1.1.1'),
                           prefix=Pattern('24'),
                           gateway=Pattern('1.1.2.1'),
                           ethernet=Ethernet(name='Rx Ipv4 Eth',
                                             vlans=[Vlan(name='Rx Ipv4 Vlan')
                                                    ]))),
        Device(name='Rx Devices Ipv6',
               container_name=rx_port.name,
               device_count=3,
               choice=Ipv6(name='Rx Ipv6',
                           ethernet=Ethernet(name='Rx Ipv6 Eth',
                                             vlans=[Vlan(name='Rx Ipv6 Vlan')
                                                    ]))),
        Device(name='Rx Devices Bgpv4',
               container_name=rx_port.name,
               device_count=10,
               choice=Bgpv4(name='Rx Bgpv4',
                            ipv4=Ipv4(name='Rx Bgpv4 Ipv4',
                                      ethernet=Ethernet(
                                          name='Rx Bgpv4 Eth',
                                          vlans=[Vlan(name='Rx Bgpv4 Vlan')
                                                 ]))))
    ]
    return devices


@pytest.fixture(scope='session')
def b2b_ipv4_devices(tx_port, rx_port):
    """Returns a list of ipv4 tx device and rx device objects
    Each device object is ipv4, ethernet and vlan
    """
    from abstract_open_traffic_generator.device import Device, Ethernet, Vlan, Ipv4
    from abstract_open_traffic_generator.device import Pattern

    tx_device = Device(name='Tx Devices Ipv4',
                       container_name=tx_port.name,
                       device_count=1,
                       choice=Ipv4(name='Tx Ipv4',
                                   address=Pattern('1.1.1.1'),
                                   prefix=Pattern('24'),
                                   gateway=Pattern('1.1.2.1'),
                                   ethernet=Ethernet(
                                       name='Tx Ipv4 Eth',
                                       vlans=[Vlan(name='Tx Ipv4 Vlan')])))

    rx_device = Device(name='Rx Devices Ipv4',
                       container_name=rx_port.name,
                       device_count=1,
                       choice=Ipv4(name='Rx Ipv4',
                                   address=Pattern('1.1.2.1'),
                                   prefix=Pattern('24'),
                                   gateway=Pattern('1.1.1.1'),
                                   ethernet=Ethernet(
                                       name='Rx Ipv4 Eth',
                                       vlans=[Vlan(name='Rx Ipv4 Vlan')])))

    return [tx_device, rx_device]


@pytest.fixture(scope='session')
def b2b_port_flow_config(options, tx_port, rx_port):
    """Returns a configuration with an ethernet flow.
    The flow uses a PortTxRx endpoint.
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.flow import Flow, TxRx, PortTxRx, \
        Size, Rate, Duration, FixedPackets, Header, Ethernet

    endpoint = PortTxRx(tx_port_name=tx_port.name, rx_port_name=rx_port.name)
    flow = Flow(name='Port Flow',
                tx_rx=TxRx(endpoint),
                packet=[Header(Ethernet())],
                size=Size(128),
                rate=Rate(unit='pps', value=1000),
                duration=Duration(FixedPackets(packets=10000)))
    return Config(ports=[tx_port, rx_port], flows=[flow], options=options)


@pytest.fixture(scope='session')
def b2b_ipv4_flow_config(options, tx_port, rx_port, b2b_ipv4_devices):
    """Returns a configuration with an ipv4 flow.
    The flow uses a DeviceTxRx endpoint.
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.flow import Flow, TxRx, DeviceTxRx, \
        Size, Rate, Duration, FixedPackets, Header, Ethernet, Vlan, Ipv4

    tx_rx_devices = DeviceTxRx(tx_device_names=[b2b_ipv4_devices[0].name],
                               rx_device_names=[b2b_ipv4_devices[1].name])
    flow = Flow(name='Ipv4 Flow',
                tx_rx=TxRx(tx_rx_devices),
                packet=[Header(Ethernet()),
                        Header(Vlan()),
                        Header(Ipv4())],
                size=Size(512),
                rate=Rate(unit='pps', value=1000),
                duration=Duration(FixedPackets(10000)))
    return Config(ports=[tx_port, rx_port],
                  devices=b2b_ipv4_devices,
                  flows=[flow],
                  options=options)


@pytest.fixture(autouse=True)
def stop_transmit_state(api):
    """Stop all flows before every test
    """
    import abstract_open_traffic_generator.control as control
    print('\nset transmit state stopped...')
    api.set_state(control.State(control.FlowTransmitState(state='stop')))
