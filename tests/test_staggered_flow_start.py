import pytest


@pytest.mark.skip(reason="Fix -breaks build - needs investigation")
def test_staggered_flow_start(api, utils):
    """Demonstrates how to individually start flows
    """
    # configure flows
    tx = utils.settings.ports[0]
    rx = utils.settings.ports[1]
    config = api.config()
    ptx, prx = config.ports.port(
        name='tx', location=tx
    ).port(
        name='rx', location=rx
    )
    flows = config.flows.flow().flow().flow()
    for i, f in enumerate(flows):
        f.name = 'flow{}'.format(i + 1)
        f.tx_rx.port.tx_name = ptx.name
        f.tx_rx.port.rx_name = prx.name
        f.rate.pps = 1000
        f.duration.fixed_packets.packets = 1000
    api.set_config(config)
    # start flows
    for flow in config.flows:
        tr_state = api.transmit_state()
        tr_state.flow_names = [flow.name]
        tr_state.state = 'start'
        api.set_transmit_state(tr_state)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )
