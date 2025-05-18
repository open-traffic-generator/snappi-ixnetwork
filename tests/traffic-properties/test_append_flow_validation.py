import pytest
import time


def test_append_flows_validation(api, b2b_raw_config, utils):
    """
    This test is to validate append_config API
    1. Initial configuration has multiple flows [f1,f2]
    2. Append one flow [f2] from the configuration.
    3. Validation:
        - Throw error since this is already part of the configuration
    """

    ports = b2b_raw_config.ports
    flow1 = b2b_raw_config.flows[0]
    flow1.name = "tx_flow1"
    flow1.packet.ethernet().ipv4()
    flow1.packet[0].src.value = "00:0c:29:1d:10:67"
    flow1.packet[0].dst.value = "00:0c:29:1d:10:71"
    flow1.packet[1].src.value = "10.10.10.1"
    flow1.packet[1].dst.value = "10.10.10.2"
    flow2 = b2b_raw_config.flows.flow()[-1]
    flow2.name = "tx_flow2"
    flow2.tx_rx.port.tx_name = ports[0].name
    flow2.tx_rx.port.rx_name = ports[1].name

    flow1.duration.fixed_packets.packets = 1000
    flow1.size.fixed = 1000
    flow1.duration.choice = flow1.duration.CONTINUOUS
    flow1.rate.pps = 1000

    flow2.duration.fixed_packets.packets = 1000
    flow2.size.fixed = 1000
    flow2.duration.choice = flow2.duration.CONTINUOUS
    flow2.rate.pps = 1000

    flow1.metrics.enable = True
    flow1.metrics.loss = True

    flow2.metrics.enable = True
    flow2.metrics.loss = True

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=False)

    time.sleep(10)
    utils.stop_traffic(api, b2b_raw_config)
    ca = api.config_append()
    caf = ca.config_append_list.add().flows
    flow3 = caf.add()
    flow3.metrics.enable = True
    flow3.metrics.loss = True
    flow3.rate.pps = 2000
    flow3.name = "tx_flow2"
    flow3.packet.ethernet().ipv4()
    flow3.tx_rx.port.tx_name = ports[0].name
    flow3.tx_rx.port.rx_name = ports[1].name

    try:
        api.append_config(ca)
        assert False
    except Exception as e:
        print(e)


if __name__ == "__main__":
    pytest.main(["-s", __file__])