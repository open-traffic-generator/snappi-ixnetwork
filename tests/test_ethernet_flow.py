import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *


def test_ethernet_flow(api, tx_port, rx_port, options, b2b_ipv4_devices):
    """EthernetPause test traffic configuration
    """
    endpoint = PortTxRx(tx_port_name=tx_port.name, rx_port_name=rx_port.name)

    ethernet = Header(
        Ethernet(dst=Pattern('00:00:01:02:03:04'),
                 src=Pattern('00:00:04:03:02:01'),
                 pfc_queue=Pattern([1, 2, 3])))

    flow = Flow(name='Default Ethernet',
                tx_rx=TxRx(endpoint),
                packet=[ethernet])

    config = Config(ports=[tx_port, rx_port],
                    devices=b2b_ipv4_devices,
                    flows=[flow],
                    options=options)

    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
