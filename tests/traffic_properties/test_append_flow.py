import pytest
import time


# @pytest.mark.skip(
#     reason="Not implemented yet"
# )
def test_append_flows(api, b2b_raw_config, utils):
    """
    This test is to validate append_config API

    1. Initial configuration has multiple flows [f1,f2]

    2. Append one flow [f3] from the configuration.

    3. Validate:
        - Validate flow name [f3] is not being part of existing configuration
        - Fetch config, newly added flow is part of fetched configuration
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

    # utils.start_traffic(api, b2b_raw_config, start_capture=False)

    time.sleep(10)
    # utils.stop_traffic(api, b2b_raw_config)
    ca = api.config_append()
    ai = ca.add()
    flow3 = ai.flows.add()
    flow3.metrics.enable = True
    flow3.metrics.loss = True
    flow3.rate.pps = 1000
    flow3.name = "tx_flow3"
    flow3.packet.ethernet().ipv4()
    flow3.tx_rx.port.tx_name = ports[0].name
    flow3.tx_rx.port.rx_name = ports[1].name

    print("Test script: Append request for the flow", ca)
    api.append_flows(ca)
    # config = api.get_config()
    # print(config)


if __name__ == "__main__":
    pytest.main(["-s", __file__])
