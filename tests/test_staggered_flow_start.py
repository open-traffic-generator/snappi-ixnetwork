import pytest
import time
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import *


def test_staggered_flow_start(serializer, api, options, tx_port, rx_port):
    """Demonstrates how to individually start flows
    """
    # this is a temporary fix
    # the line should be removed and needs to be debugged as to why it the test
    # fails periodically when it is removed
    api.set_state(State(ConfigState(config=Config(), state='set')))

    # configure flows
    tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_name=rx_port.name)
    config = Config(ports=[tx_port, rx_port], options=options)
    for name in ['flow1', 'flow2', 'flow3']:
        flow = Flow(name=name,
                    tx_rx=TxRx(tx_rx),
                    rate=Rate('pps', value=1000),
                    duration=Duration(FixedPackets()))
        config.flows.append(flow)
    api.set_state(State(ConfigState(config=config, state='set')))

    # start flows
    for flow in config.flows:
        api.set_state(
            State(FlowTransmitState(flow_names=[flow.name], state='start')))
    
    # stop flows
    api.set_state(State(FlowTransmitState(state='stop')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
