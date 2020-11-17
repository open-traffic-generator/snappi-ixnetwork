import pytest
import time
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import *


def test_staggered_flow_start(serializer, api, options, tx_port, rx_port):
    """Demonstrates how to incrementally start transmit on flows
    """
    # this is a temporary fix 
    # the line should be removed and needs to be debugged as to why it the test 
    # fails periodically when it is removed
    api.set_state(State(ConfigState(config=Config(), state='set')))

    # configure flows
    tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_name=rx_port.name)
    config = Config(ports=[tx_port, rx_port],
                    flows=[
                        Flow(name='flow1',
                             tx_rx=TxRx(tx_rx),
                             rate=Rate('pps', value=1000),
                             duration=Duration(FixedPackets())),
                        Flow(name='flow2',
                             tx_rx=TxRx(tx_rx),
                             rate=Rate('pps', value=1000),
                             duration=Duration(FixedPackets())),
                        Flow(name='flow3',
                             tx_rx=TxRx(tx_rx),
                             rate=Rate('pps', value=1000),
                             duration=Duration(FixedPackets()))
                    ],
                    options=options)
    api.set_state(State(ConfigState(config=config, state='set')))

    # start flow1 transmit
    api.set_state(
        State(
            FlowTransmitState(flow_names=[config.flows[0].name],
                              state='start')))
    # start flow2 transmit
    api.set_state(
        State(
            FlowTransmitState(flow_names=[config.flows[1].name],
                              state='start')))
    # start flow3 transmit
    api.set_state(
        State(
            FlowTransmitState(flow_names=[config.flows[2].name],
                              state='start')))
    # stop all flows
    api.set_state(State(FlowTransmitState(state='stop')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
