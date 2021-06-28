import pytest


@pytest.mark.skip("ipv4 device tests are available")
def test_device_ipv4_fixed(api, utils):
    """Test the creation of ipv4 fixed properties"""
    port = utils.settings.ports[0]
    config = api.config()
    port1 = config.ports.port()[-1]
    port1.location = port
    port1.name = "port 1"
    dev = config.devices.device()[-1]
    dev.name = "device"
    dev.container_name = port1.name
    dev.device_count = 15
    eth = dev.ethernet
    eth.name = "eth"
    eth.mac.value = "00:00:fa:ce:fa:ce"
    eth.mtu.value = 1200
    ipv4 = eth.ipv4
    ipv4.address.value = "1.1.1.1"
    ipv4.prefix.value = 24
    ipv4.gateway.value = "1.1.2.1"
    api.set_config(config)


@pytest.mark.skip("ipv4 device tests are available")
def test_device_ipv4value_list(api, utils):
    """Test the creation of ipv4 value list properties"""
    port = utils.settings.ports[0]
    config = api.config()
    port1 = config.ports.port()[-1]
    port1.location = port
    port1.name = "port 1"
    dev = config.devices.device()[-1]
    dev.name = "device"
    dev.container_name = port1.name
    dev.device_count = 15
    eth = dev.ethernet
    eth.name = "eth"
    eth.mac.values = ["00:00:aa:aa:aa:aa", "00:00:bb:bb:bb:bb"]
    eth.mtu.values = [1200, 1201, 1202]
    ipv4 = eth.ipv4
    ipv4.address.values = ["1.1.1.1", "1.1.1.6", "1.1.1.7"]
    ipv4.prefix.values = [24, 32, 16]
    ipv4.gateway.values = ["1.1.2.1", "1.1.2.6", "1.1.2.7"]
    api.set_config(config)
