import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.layer1 import *
from abstract_open_traffic_generator.control import *


def test_layer1_fcoe(serializer, api, tx_port, rx_port):
    """Test that layer1 fcoe configuration settings are being applied correctly.
    """
    pfc = Ieee8021qbb(pfc_delay=3, pfc_class_0=1, pfc_class_1=0, pfc_class_4=7)
    flowctl = FlowControl(directed_address='0180C2000001', choice=pfc)
    fcoe_layer1 = Layer1(name='fcoe settings',
                         port_names=[rx_port.name],
                         auto_negotiate=True,
                         flow_control=flowctl)

    disabled_pfc_delay = Ieee8021qbb(pfc_delay=0)
    flowctl = FlowControl(directed_address='0180C2000001',
                          choice=disabled_pfc_delay)
    eth_layer1 = Layer1(name='non fcoe settings',
                        port_names=[tx_port.name],
                        auto_negotiate=True,
                        speed='speed_1_gbps',
                        flow_control=flowctl)

    config = Config(ports=[tx_port, rx_port], layer1=[fcoe_layer1, eth_layer1])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
