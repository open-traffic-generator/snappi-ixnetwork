import pytest
import snappi
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


@pytest.fixture
def settings():
    # global settings
    return utl.settings


@pytest.fixture(scope='session')
def api():
    # handle to make API calls
    api = snappi.api(host=utl.settings.api_server, ext=utl.settings.ext)
    yield api
    if getattr(api, 'assistant', None) is not None:
        api.assistant.Session.remove()


@pytest.fixture
def b2b_raw_config(api):
    """
    back to back raw config
    """
    config = api.config()

    tx, rx = (
        config.ports
        .port(name='tx', location=utl.settings.ports[0])
        .port(name='rx', location=utl.settings.ports[1])
    )

    l1 = config.layer1.layer1()[0]
    l1.name = 'l1'
    l1.port_names = [rx.name, tx.name]
    l1.media = utl.settings.media
    l1.speed = utl.settings.speed

    flow = config.flows.flow(name='f1')[-1]
    flow.tx_rx.port.tx_name = tx.name
    flow.tx_rx.port.rx_name = rx.name

    # this will allow us to take over ports that may already be in use
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name='c1')[-1]
    cap.port_names = [rx.name]
    cap.format = cap.PCAP

    return config


@pytest.fixture
def utils():
    return utl


@pytest.fixture
def tx_port(b2b_raw_config):
    """Returns a transmit port
    """
    return b2b_raw_config.ports[0]


@pytest.fixture
def rx_port(b2b_raw_config):
    """Returns a receive port
    """
    return b2b_raw_config.ports[1]


@pytest.fixture
def b2b_ipv4_devices(b2b_raw_config, tx_port, rx_port):
    """Returns a list of ipv4 tx device and rx device objects
    Each device object is ipv4, ethernet and vlan
    """
    tx_device, rx_device = b2b_raw_config.devices.device().device()
    tx_device.name, rx_device.name = 'Tx Devices Ipv4', 'Rx Devices Ipv4'
    tx_device.container_name, rx_device.container_name = tx_port.name, \
        rx_port.name
    tx_device.device_count, rx_device.device_count = 1, 1
    tx_eth, rx_eth = tx_device.ethernet, rx_device.ethernet
    tx_eth.name, rx_eth.name = 'Tx eth', 'Rx eth'
    tx_ip, rx_ip = tx_eth.ipv4, rx_eth.ipv4
    tx_ip.name, rx_ip.name = 'Tx Ip', 'Rx Ip'
    tx_ip.address.value, rx_ip.address.value = '1.1.1.1', '1.1.2.1'
    tx_ip.gateway.value, rx_ip.gateway.value = '1.1.2.1', '1.1.1.1'
    tx_ip.prefix.value, rx_ip.gateway.value = 24, 24

    return [tx_device, rx_device]


@pytest.fixture
def options(b2b_raw_config):
    """Returns global options
    """
    b2b_raw_config.options.port_options.location_preemption = True
    return b2b_raw_config.options
