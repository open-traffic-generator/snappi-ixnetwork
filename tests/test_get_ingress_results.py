import pytest


@pytest.mark.skip(reason="Not yet implemented")
def test_get_ingress_results(b2b_raw_config, options, tx_port, rx_port, api):
    """UDP Flow test traffic configuration"""
    import snappi

    b2b_raw_config = snappi.Api().config()
    b2b_raw_config.flows.clear()
    f = b2b_raw_config.flows.flow()[-1]
    f.name = "UDP Flow"
    f.packet.ethernet().vlan().ipv4().udp()
    f.tx_rx.port.tx_name = tx_port.name
    f.tx_rx.port.rx_name = rx_port.name
    f.size.fixed = 128
    f.rate.pps = 1000
    f.duration.fixed_packets.packets = 10000
    udp = f.packet[-1]
    udp.src_port.increment.start = 12001
    udp.dst_port.value = 20
    api.set_config(b2b_raw_config)
    # udp.ingress_result_name = 'UDP SRC PORT'
    transmit_state = api.transmit_state()
    transmit_state.state = "start"
    api.set_transmit_state(transmit_state)

    request = api.metrics_request()
    request.choice = request.FLOW
    request.flow.ingress_result_names = ["UDP SRC PORT"]
    while True:
        df = api.get_metrics(request).flow_metrics
        if df.frames_tx.sum() >= 10000 and df.frames_tx_rate.sum() == 0:
            break


if __name__ == "__main__":
    pytest.main(["-s", __file__])
