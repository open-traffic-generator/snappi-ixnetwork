import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator.result import PortRequest


def test_ports(serializer, api, options, tx_port, rx_port):
    """Demonstrates how to retrieve port results
    """
    endpoint = PortTxRx(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    flow = Flow(name='Port Flow',
                    tx_rx=TxRx(endpoint),
                    size=Size(128),
                    rate=Rate(unit='pps', value=1000),
                    duration=Duration(FixedPackets(packets=10000)))
    config = Config(ports=[tx_port, rx_port],
        flows=[flow],
        options=options
    )
    state = State(ConfigState(config=config, state='set'))
    print(serializer.json(state))
    api.set_state(state)
    state = State(FlowTransmitState(state='start'))
    api.set_state(state)

    from pandas import DataFrame
    request = PortRequest(column_names=['name', 'location', 'frames_tx', 'frames_rx'])
    while True:
        results = api.get_port_results(request)
        df = DataFrame.from_dict(results)
        print(df)
        if df.frames_tx.sum() >= 10000:
            break


if __name__ == '__main__':
    pytest.main(['-s', __file__])
