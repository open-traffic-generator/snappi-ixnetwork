import pytest
from abstract_open_traffic_generator.control import State, ConfigState, FlowTransmitState
from abstract_open_traffic_generator.result import PortRequest, Port


def test_ports(serializer, api, b2b_port_flow_config):
    """Demonstrates how to retrieve port results
    """
    state = State(ConfigState(config=b2b_port_flow_config, state='set'))
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
        if df.frames_tx.sum() >= b2b_port_flow_config.flows[0].duration.packets.packets:
            break


if __name__ == '__main__':
    pytest.main(['-s', __file__])
