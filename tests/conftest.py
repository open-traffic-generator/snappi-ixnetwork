import pytest
import json
import yaml

import utils as utl


def pytest_exception_interact(node, call, report):
    # end all pytests on first exception that is encountered
    pytest.exit(call.excinfo.traceback[0])


def pytest_addoption(parser):
    # called before running tests to register command line options for pytest
    utl.settings.register_pytest_command_line_options(parser)


def pytest_configure(config):
    # callled before running (configuring) tests to load global settings with
    # values provided over command line
    utl.settings.load_from_pytest_command_line(config)


@pytest.fixture(scope='session')
def settings():
    # global settings
    return utl.settings


@pytest.fixture(scope='session')
def api():
    # handle to make API calls
    api = utl.get_api_client()
    yield api
    if api.assistant is not None:
        api.assistant.Session.remove()


@pytest.fixture(scope='session')
def b2b_raw_config():
    return utl.get_b2b_raw_config()


@pytest.fixture(scope='session')
def b2b_raw_config_two_flows():
    return utl.get_b2b_raw_config_two_flows()


@pytest.fixture(scope='session')
def utils():
    return utl


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
    return Port(name='Tx Port', location=utl.settings.ports[0])


@pytest.fixture(scope='session')
def rx_port():
    """Returns a receive port
    """
    from abstract_open_traffic_generator.port import Port
    return Port(name='Rx Port', location=utl.settings.ports[1])


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

    names = [device.name for device in b2b_ipv4_devices]
    tx_rx_devices = DeviceTxRx(tx_device_names=names, rx_device_names=names)
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


@pytest.fixture(scope='session')
def b2b_ipv4_flows_config(options, tx_port, rx_port, b2b_ipv4_devices):
    """Returns a configuration with multiple ipv4 flows.
    The flow uses a DeviceTxRx endpoint.
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.flow import Flow, TxRx, DeviceTxRx, \
        Size, Rate, Duration, FixedPackets, Header, Ethernet, Vlan, Ipv4

    names = [device.name for device in b2b_ipv4_devices]
    tx_rx_devices = DeviceTxRx(tx_device_names=names, rx_device_names=names)
    flow1 = Flow(name='Ipv4 Flow 1',
                 tx_rx=TxRx(tx_rx_devices),
                 packet=[Header(Ethernet()),
                         Header(Vlan()),
                         Header(Ipv4())],
                 size=Size(512),
                 rate=Rate(unit='pps', value=1000),
                 duration=Duration(FixedPackets(10000)))

    flow2 = Flow(name='Ipv4 Flow 2',
                 tx_rx=TxRx(tx_rx_devices),
                 packet=[Header(Ethernet()),
                         Header(Vlan()),
                         Header(Ipv4())],
                 size=Size(512),
                 rate=Rate(unit='pps', value=1000),
                 duration=Duration(FixedPackets(10000)))
    return Config(ports=[tx_port, rx_port],
                  devices=b2b_ipv4_devices,
                  flows=[flow1, flow2],
                  options=options)
