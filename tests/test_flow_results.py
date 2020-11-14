import pytest
import abstract_open_traffic_generator.control as control
import abstract_open_traffic_generator.result as result
import pandas


def test_flow_results(serializer, api, b2b_ipv4_flow_config):
    """Demonstrates the following:
    - Retrieving a subset of flow results
    - Use pandas to display the results in a table format
    - Use pandas to end the script when a condition is met
    """
    state = control.State(
        control.ConfigState(config=b2b_ipv4_flow_config, state='set'))
    api.set_state(state)
    state = control.State(control.FlowTransmitState(state='start'))
    api.set_state(state)

    while True:
        results = api.get_flow_results(result.FlowRequest())
        df = pandas.DataFrame.from_dict(results)
        print(df)
        if df.frames_tx.sum() >= b2b_ipv4_flow_config.flows[0].duration.packets.packets:
            break


if __name__ == '__main__':
    pytest.main(['-s', __file__])
