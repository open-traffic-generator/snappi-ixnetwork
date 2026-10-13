import pytest


def test_flow_port_rx_names_e2e(api, utils):
    """
    One tx port and two rx ports configured through port.rx_names:
    - set_config must succeed
    - the flow must transmit and its metrics must report frames_tx
    Requires at least 3 ports in tests/settings.json.
    """
    if len(utils.settings.ports) < 3:
        pytest.skip("test needs 3 ports in settings")

    packets = 1000
    config = api.config()
    tx, rx1, rx2 = (
        config.ports.port(name="tx", location=utils.settings.ports[0])
        .port(name="rx1", location=utils.settings.ports[1])
        .port(name="rx2", location=utils.settings.ports[2])
    )

    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.port_names = [tx.name, rx1.name, rx2.name]
    l1.media = utils.settings.media
    l1.speed = utils.settings.speed

    config.options.port_options.location_preemption = True

    flow = config.flows.flow(name="f_multi_rx")[-1]
    flow.tx_rx.port.tx_name = tx.name
    flow.tx_rx.port.rx_names = [rx1.name, rx2.name]
    flow.size.fixed = 128
    flow.rate.pps = 1000
    flow.duration.fixed_packets.packets = packets
    flow.metrics.enable = True
    eth, ip, udp = flow.packet.ethernet().ipv4().udp()
    eth.src.value = "00:CD:DC:CD:DC:CD"
    eth.dst.value = "00:AB:BC:AB:BC:AB"
    ip.src.value = "1.1.1.1"
    ip.dst.value = "1.1.1.2"
    udp.src_port.value = 5000
    udp.dst_port.value = 6000

    utils.start_traffic(api, config, start_capture=False)

    def flow_completed():
        req = api.metrics_request()
        req.flow.flow_names = [flow.name]
        res = api.get_metrics(req).flow_metrics
        return len(res) > 0 and res[0].transmit == "stopped"

    try:
        utils.wait_for(flow_completed, "flow with multiple rx ports to finish")
        req = api.metrics_request()
        req.flow.flow_names = [flow.name]
        metrics = api.get_metrics(req).flow_metrics
        assert len(metrics) == 1
        assert metrics[0].frames_tx > 0
    finally:
        utils.stop_traffic(api, config, stop_capture=False)
