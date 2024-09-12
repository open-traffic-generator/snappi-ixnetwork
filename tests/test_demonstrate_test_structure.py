import pytest

@pytest.mark.skip(reason="CI failure")
# @pytest.fixture
def port_configs(api, utils):
    """This fixture demonstrates setting up configurations that consist
    only of port, layer1 and device settings.
    """
    configs = []
    for c in range(2):
        config = api.config()
        ports = config.ports.port(
            name="Port 1", location=utils.settings.ports[0]
        ).port(name="Port 2", location=utils.settings.ports[1])
        config.options.port_options.location_preemption = True
        config.layer1.layer1().layer1()
        devices = config.devices.device().device()
        for i, l1 in enumerate(config.layer1):
            l1.name = "L1 Settings %s" % (i)
            l1.port_names = [ports[i].name]
            l1.speed = utils.settings.speed
            l1.flow_control.ieee_802_1qbb.pfc_delay = 1
            l1.flow_control.ieee_802_1qbb.pfc_class_0 = 0
            l1.flow_control.ieee_802_1qbb.pfc_class_1 = 1
            l1.flow_control.ieee_802_1qbb.pfc_class_2 = 2
            l1.flow_control.ieee_802_1qbb.pfc_class_3 = 3
            l1.flow_control.ieee_802_1qbb.pfc_class_4 = 4
            l1.flow_control.ieee_802_1qbb.pfc_class_5 = 5
            l1.flow_control.ieee_802_1qbb.pfc_class_6 = 6
            l1.flow_control.ieee_802_1qbb.pfc_class_7 = 7
            devices[i].name = "Device %s" % (i)
            eth = devices[i].ethernets.add()
            eth.connection.port_name = ports[i].name
            eth.name = "Ethernet %s" % (i)
            eth.mac = "00:00:00:00:00:{:02x}".format(i)
            ip = eth.ipv4_addresses.add()
            ip.name = "Ipv4 %s" % (i)
            ip.gateway = "1.1.1.2"
            ip.address = "1.1.1.1"
        configs.append(config)
    return configs

@pytest.mark.skip(reason="CI failure")
# @pytest.fixture
def flow_configs(port_configs):
    """This fixture demonstrates adding flows to port configurations."""

    for config in port_configs:
        f = config.flows.flow()[-1]
        f.tx_rx.device.tx_names = [config.devices[0].name]
        f.tx_rx.device.rx_names = [config.devices[1].name]
        f.name = "%s --> %s" % (config.ports[0].name, config.ports[1].name)
        f.size.fixed = 128
        f.duration.fixed_packets.packets = 10000000
    return port_configs

@pytest.mark.skip(reason="CI failure")
def test_fixtures(flow_configs, api):
    """Iterate through the flow configs using each config to run a test."""
    for config in flow_configs:
        api.set_config(config)
