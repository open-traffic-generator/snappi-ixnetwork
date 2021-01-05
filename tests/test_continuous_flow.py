import pytest
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator import layer1


def test_continuous_flow(serializer, api, options, tx_port, rx_port, settings):
    """Demonstrates how to create and start a continuous flow
    """
    # configure flows
    tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_name=rx_port.name)
    l1 = [
        layer1.Layer1(
            name='l1', port_names=[tx_port.name, rx_port.name],
            speed=settings.speed, media=settings.media
        )
    ]
    config = Config(ports=[tx_port, rx_port], layer1=l1, options=options)
    flow = Flow(name='Continuous Flow',
                tx_rx=TxRx(tx_rx),
                rate=Rate('pps', value=1000),
                duration=Duration(Continuous()))
    config.flows.append(flow)
    api.set_state(State(ConfigState(config=config, state='set')))

    # start flows
    api.set_state(State(FlowTransmitState(state='start')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
