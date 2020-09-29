import pytest
import time
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import *


def test_staggered_flow_start(serializer, api, tx_port, rx_port):
    """Demonstrates how to incrementally start transmit on flows
    """
    # configure flows
    tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    config = Config(ports=[tx_port, rx_port], 
        flows=[
            Flow(name='flow1', tx_rx=TxRx(tx_rx), rate=Rate('pps', value=1000), duration=Duration(FixedPackets(packets=0))),
            Flow(name='flow2', tx_rx=TxRx(tx_rx), rate=Rate('pps', value=1000), duration=Duration(FixedPackets(packets=0))),
            Flow(name='flow3', tx_rx=TxRx(tx_rx), rate=Rate('pps', value=1000), duration=Duration(FixedPackets(packets=0)))
        ]
    )
    api.set_config(config)

    # start flow1 transmit
    api.set_flow_transmit(FlowTransmit(flow_names=[config.flows[0].name], state='start'))
    time.sleep(5)

    # start flow2 transmit
    api.set_flow_transmit(FlowTransmit(flow_names=[config.flows[1].name], state='start'))
    time.sleep(5)

    # start flow3 transmit
    api.set_flow_transmit(FlowTransmit(flow_names=[config.flows[2].name], state='start'))
    time.sleep(5)

    # stop all flows
    api.set_flow_transmit(FlowTransmit(state='stop'))


if __name__ == '__main__':
    pytest.main(['-s', __file__])