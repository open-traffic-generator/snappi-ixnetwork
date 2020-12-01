import pytest
import abstract_open_traffic_generator.control as control
import abstract_open_traffic_generator.result as result
import abstract_open_traffic_generator.flow as flow


@pytest.mark.skip(reason="Fix - Do not use pandas")
def test_short_duration_flow_results(serializer, api, b2b_ipv4_flows_config):
    """Bug Fix Test - given a short duration flow the flow metrics
    are all 0 when flows are stopped

    To reproduce:
    - Update a configuration's flows with a short fixed duration
    - Start flows
    - Start polling flow metrics
    - End polling of flow metrics when flow metric transmit is stopped

    Fixed when:
    - flow metric frames_tx is not zero
    """
    duration = flow.Duration(flow.FixedSeconds(seconds=1))
    for config_flow in b2b_ipv4_flows_config.flows:
        config_flow.duration = duration
    state = control.State(
        control.ConfigState(config=b2b_ipv4_flows_config, state='set'))
    api.set_state(state)
    state = control.State(control.FlowTransmitState(state='start'))
    api.set_state(state)

    while True:
        results = api.get_flow_results(result.FlowRequest())
        df = pandas.DataFrame.from_dict(results)
        if df.transmit.str.match('^stopped$').sum() == len(df):
            break
    print(df)
    assert(df.frames_tx.sum() > 0)
    

if __name__ == '__main__':
    pytest.main(['-s', __file__])
