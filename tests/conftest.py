import pytest
import snappi
import logging
import utils as utl


def pytest_addoption(parser):
    # called before running tests to register command line options for pytest
    utl.settings.register_pytest_command_line_options(parser)


def pytest_configure(config):
    # callled before running (configuring) tests to load global settings with
    # values provided over command line
    utl.settings.load_from_pytest_command_line(config)


def pytest_collection_modifyitems(items):
    """Called after collection has been performed. May filter or re-order
    the items in-place.

    :param List[pytest.Item] items: List of item objects.
    """
    try:
        pretest_index = [
            index
            for index, item in enumerate(items)
            if item.name == "test_pretest"
        ][0]

        items[0], items[pretest_index] = items[pretest_index], items[0]

        test_flow_tracking_index = [
            index
            for index, item in enumerate(items)
            if item.name == "test_flow_tracking_stats"
        ][0]

        test_device_connection = [
            index
            for index, item in enumerate(items)
            if item.name == "test_device_connection"
        ][0]

        items[-2], items[test_device_connection] = (
            items[test_device_connection],
            items[-2],
        )

        items[-1], items[test_flow_tracking_index] = (
            items[test_flow_tracking_index],
            items[-1],
        )
    except:
        print("skipping pretest as test_pretest is not part of the batch run")


@pytest.fixture
def settings():
    # global settings
    return utl.settings


@pytest.fixture(scope="session")
def api():
    # handle to make API calls
    api = snappi.api(location=utl.settings.location, ext=utl.settings.ext)
    utl.configure_credentials(api, utl.settings.username, utl.settings.psd)
    yield api
    if getattr(api, "assistant", None) is not None:
        api.assistant.Session.remove()


@pytest.fixture
def b2b_raw_config(api):
    """
    back to back raw config
    """
    config = api.config()

    tx, rx = config.ports.port(name="tx", location=utl.settings.ports[0]).port(
        name="rx", location=utl.settings.ports[1]
    )

    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.port_names = [rx.name, tx.name]
    l1.media = utl.settings.media
    l1.speed = utl.settings.speed

    flow = config.flows.flow(name="f1")[-1]
    flow.tx_rx.port.tx_name = tx.name
    flow.tx_rx.port.rx_name = rx.name

    # this will allow us to take over ports that may already be in use
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="c1")[-1]
    cap.port_names = [rx.name]
    cap.format = cap.PCAPNG

    return config


@pytest.fixture
def b2b_raw_config_4port(api):
    """
    back to back raw config 4 ports
    """
    config = api.config()

    tx1, rx1, tx2, rx2 = config.ports.port(
        name="tx1", location=utl.settings.ports[0]).port(
        name="rx1", location=utl.settings.ports[1]).port(
        name="tx2", location=utl.settings.ports[2]).port(
        name="rx2", location=utl.settings.ports[3])

    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.port_names = [rx1.name, tx1.name, rx2.name, tx2.name]
    l1.media = utl.settings.media
    l1.speed = utl.settings.speed

    flow1 = config.flows.flow(name="f1")[-1]
    flow1.tx_rx.port.tx_name = tx1.name
    flow1.tx_rx.port.rx_name = rx1.name

    flow2 = config.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx2.name
    flow2.tx_rx.port.rx_name = rx2.name

    # this will allow us to take over ports that may already be in use
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="c1")[-1]
    cap.port_names = [rx1.name]
    cap.format = cap.PCAPNG

    return config


@pytest.fixture
def utils():
    return utl


@pytest.fixture
def tx_port(b2b_raw_config):
    """Returns a transmit port"""
    return b2b_raw_config.ports[0]


@pytest.fixture
def rx_port(b2b_raw_config):
    """Returns a receive port"""
    return b2b_raw_config.ports[1]


@pytest.fixture
def b2b_raw_config_vports(api):
    """
    back to back raw config with virtual ports
    """
    config = api.config()

    tx, rx = config.ports.port(name="tx").port(name="rx")

    flow = config.flows.flow(name="f1")[-1]
    flow.tx_rx.port.tx_name = tx.name
    flow.tx_rx.port.rx_name = rx.name

    return config


@pytest.fixture
def tx_vport(b2b_raw_config_vports):
    """Returns a transmit vport"""
    return b2b_raw_config_vports.ports[0]


@pytest.fixture
def rx_vport(b2b_raw_config_vports):
    """Returns a receive vport"""
    return b2b_raw_config_vports.ports[1]


@pytest.fixture
def b2b_ipv4_devices(b2b_raw_config, tx_port, rx_port):
    """Returns a list of ipv4 tx device and rx device objects
    Each device object is ipv4, ethernet and vlan
    """
    tx_device, rx_device = b2b_raw_config.devices.device().device()
    tx_device.name, rx_device.name = "Tx Devices Ipv4", "Rx Devices Ipv4"
    tx_device.container_name, rx_device.container_name = (
        tx_port.name,
        rx_port.name,
    )
    tx_device.device_count, rx_device.device_count = 1, 1
    tx_eth, rx_eth = tx_device.ethernet, rx_device.ethernet
    tx_eth.name, rx_eth.name = "Tx eth", "Rx eth"
    tx_ip, rx_ip = tx_eth.ipv4, rx_eth.ipv4
    tx_ip.name, rx_ip.name = "Tx Ip", "Rx Ip"
    tx_ip.address.value, rx_ip.address.value = "1.1.1.1", "1.1.2.1"
    tx_ip.gateway.value, rx_ip.gateway.value = "1.1.2.1", "1.1.1.1"
    tx_ip.prefix.value, rx_ip.gateway.value = 24, 24

    return [tx_device, rx_device]


@pytest.fixture
def options(b2b_raw_config):
    """Returns global options"""
    b2b_raw_config.options.port_options.location_preemption = True
    return b2b_raw_config.options
