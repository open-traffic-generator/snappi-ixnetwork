def test_short_duration_flow_results(api, utils, b2b_raw_config):
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
    f = b2b_raw_config.flows[-1]
    f.duration.fixed_seconds.seconds = 1
    api.set_config(b2b_raw_config)
    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )
    utils.get_all_stats(api)
