import pytest
import abstract_open_traffic_generator.control as control
import abstract_open_traffic_generator.result as result
import pandas


def test_port_results(serializer, api, b2b_port_flow_config):
    """Demonstrates the following:
    - Retrieving a subset of port results
    - Use pandas to display the results in a table format
    - Use pandas to end the script when a condition is met
    """
    config_state = control.ConfigState(
        config=b2b_port_flow_config,
        state='set')
    state = control.State(config_state)
    print(serializer.json(state))
    api.set_state(state)
    flow_transmit_state = control.FlowTransmitState(state='start')
    state = control.State(flow_transmit_state)
    api.set_state(state)

    request = result.PortRequest(
        column_names=['name', 'location', 'frames_tx', 'frames_rx'])
    while True:
        results = api.get_port_results(request)
        df = pandas.DataFrame.from_dict(results)
        print(df)
        if df.frames_tx.sum() >= b2b_port_flow_config.flows[0].duration.packets.packets:
            break


if __name__ == '__main__':
    pytest.main(['-s', __file__])
