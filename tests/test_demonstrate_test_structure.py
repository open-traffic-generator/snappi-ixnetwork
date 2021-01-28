import copy
import pytest


@pytest.fixture
def port_configs():
    """This fixture demonstrates setting up configurations that consist 
    only of port, layer1 and device settings.
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.device import Device, Ethernet, Ipv4
    from abstract_open_traffic_generator.layer1 import FlowControl, Ieee8021qbb, Layer1
    from abstract_open_traffic_generator.port import Port

    port1 = Port(name='Port 1')
    port2 = Port(name='Port 2')
    configs = []
    for ports in [[port1, port2], [copy.deepcopy(port2),
                                   copy.deepcopy(port1)]]:
        pfc = Ieee8021qbb(pfc_delay=1,
                          pfc_class_0=0,
                          pfc_class_1=1,
                          pfc_class_2=2,
                          pfc_class_3=3,
                          pfc_class_4=4,
                          pfc_class_5=5,
                          pfc_class_6=6,
                          pfc_class_7=7)
        flow_ctl = FlowControl(choice=pfc)
        layer1 = Layer1(name='Layer1 settings',
                        port_names=[ports[0].name, ports[1].name],
                        speed='speed_100_gbps',
                        auto_negotiate=True)
        device1 = Device('Tx Devices',
                         container_name=ports[0].name,
                         choice=Ipv4(name='Tx Ipv4',
                                     ethernet=Ethernet(name='Tx Ethernet')))
        device2 = Device('Rx Devices',
                         container_name=ports[1].name,
                         choice=Ipv4(name='Rx Ipv4',
                                     ethernet=Ethernet(name='Rx Ethernet')))
        config = Config(ports=ports,
                        layer1=[layer1],
                        devices=[device1, device2])
        configs.append(config)
    return configs


@pytest.fixture
def flow_configs(port_configs):
    """This fixture demonstrates adding flows to port configurations.
    """
    from abstract_open_traffic_generator.flow import DeviceTxRx, Duration, FixedPackets, Flow, Rate, Size, TxRx

    for config in port_configs:
        device_tx_rx = DeviceTxRx(tx_device_names=[config.devices[0].name],
                                  rx_device_names=[config.devices[1].name])
        config.flows.append(
            Flow(name='%s --> %s' %
                 (config.ports[0].name, config.ports[1].name),
                 tx_rx=TxRx(device_tx_rx),
                 size=Size(128),
                 rate=Rate(unit='pps', value=50000),
                 duration=Duration(FixedPackets(packets=10000000))))
    return port_configs

@pytest.mark.skip("skip until migrated to snappi")
def test_fixtures(flow_configs, api):
    """Iterate through the flow configs using each config to run a test.
    """
    for config in flow_configs:
        api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
