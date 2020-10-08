import pytest
from abstract_open_traffic_generator.control import State, ConfigState, FlowTransmitState
from abstract_open_traffic_generator.result import FlowRequest


def test_flow_results(serializer, api, b2b_ipv4_flow_config):
    """Demonstrates the following:
    - Retrieving a subset of flow results
    - Use pandas to display the results in a table format
    - Use pandas to end the script when a condition is met
    """
    state = State(ConfigState(config=b2b_ipv4_flow_config, state='set'))
    print(serializer.json(state))
    api.set_state(state)
    state = State(FlowTransmitState(state='start'))
    api.set_state(state)

    from pandas import DataFrame
    request = FlowRequest(column_names=['name', 'transmit', 'frames_tx', 'frames_rx'])
    while True:
        results = api.get_flow_results(request)
        df = DataFrame.from_dict(results)
        print(df)
        if df.frames_tx.sum() >= b2b_ipv4_flow_config.flows[0].duration.packets.packets:
            break


if __name__ == '__main__':
    pytest.main(['-s', __file__])
