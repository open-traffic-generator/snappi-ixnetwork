import pytest
import time


def test_append_flows(api, utils):
    """
    This test is to validate append_config API
    1. Initial configuration has multiple flows [f1,f2]
    2. Append one flow [f3] from the configuration.
    3. Validate:
        - Validate flow name [f3] is not being part of existing configuration
        - Fetch config, newly added flow is part of fetched configuration
    """
    config = api.config()
    p1, p2 = config.ports.port(name="tx", location=utils.settings.ports[0]).port(
        name="rx", location=utils.settings.ports[1]
    )

    config.layer1.layer1(
        name="layer1",
        port_names=[p.name for p in config.ports],
        speed=utils.settings.speed,
        media=utils.settings.media,
    )

    # configure flow1 properties
    flw1, flw2 = config.flows.flow(name="flw1").flow(name="flw2")
    flw1.tx_rx.port.tx_name = p1.name
    flw1.tx_rx.port.rx_name = p2.name
    flw1.metrics.enable = True
    flw1.size.fixed = 128
    flw1.rate.pps = 1000
    flw1.duration.fixed_packets.packets = 10000
    flw1.packet.ethernet().vlan().ipv4().tcp()

    # configure flow2 properties
    flw2.tx_rx.port.tx_name = p1.name
    flw2.tx_rx.port.rx_name = p2.name
    flw2.metrics.enable = True
    flw2.size.fixed = 128
    flw2.rate.pps = 1000
    flw2.duration.fixed_packets.packets = 10000
    flw2.packet.ethernet().ipv4()

    # push configuration
    api.set_config(config)
    # start transmitting configured flows
    control_state = api.control_state()
    control_state.choice = control_state.TRAFFIC
    control_state.traffic.choice = control_state.traffic.FLOW_TRANSMIT
    control_state.traffic.flow_transmit.state = control_state.traffic.flow_transmit.START  # noqa
    res = api.set_control_state(control_state)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    time.sleep(5)

    control_state.traffic.flow_transmit.state = control_state.traffic.flow_transmit.STOP  # noqa
    res = api.set_control_state(control_state)
    utils.get_all_stats(api)

    ca = api.config_append()
    caf = ca.config_append_list.add().flows
    flw3 = caf.add()
    flw3.metrics.enable = True
    flw3.metrics.loss = True
    flw3.size.fixed = 256
    flw3.rate.pps = 2000
    flw3.name = "flw3"
    flw3.packet.ethernet().ipv4()
    flw3.tx_rx.port.tx_name = p1.name
    flw3.tx_rx.port.rx_name = p2.name

    flw4 = caf.add()
    flw4.metrics.enable = True
    flw4.metrics.loss = True
    flw4.size.fixed = 512
    flw4.rate.pps = 3000
    flw4.name = "flw4"
    flw4.packet.ethernet().ipv4()
    flw4.tx_rx.port.tx_name = p2.name
    flw4.tx_rx.port.rx_name = p1.name

    api.append_config(ca)

    # Start traffic
    control_state = api.control_state()
    control_state.choice = control_state.TRAFFIC
    control_state.traffic.choice = control_state.traffic.FLOW_TRANSMIT
    control_state.traffic.flow_transmit.state = control_state.traffic.flow_transmit.START  # noqa
    api.set_control_state(control_state)
    time.sleep(5)

    utils.get_all_stats(api)

    # Validate appended flows are part of configuration
    config = api.get_config()
    flow_list = []
    for flow in config.flows:
        flow_list.append(flow.name)
        
    flows_appended = ["flw3","flw4"]
    for flow in flows_appended:
        assert flow in flow_list

    cd = api.config_delete()
    cd.config_delete_list.add().flows = ["flw2"]
    print("Deletion request for the flows", cd)
    api.delete_config(cd)

    # Validate deleted flows are not part of fetched configuration
    config = api.get_config()
    flow_list = []
    for flow in config.flows:
        flow_list.append(flow.name)
        
    flows_deleted = ["flw2"]
    for flow in flows_deleted:
        assert flow not in flow_list
    
if __name__ == "__main__":
    pytest.main(["-s", __file__])