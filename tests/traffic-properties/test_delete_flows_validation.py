import pytest
import time


def test_delete_flows(api, b2b_raw_config, utils):
    """
    This test is to validate delete_config API
    1. Initial configuration has multiple flows [flow1,flow2]
    2. Delete one flow [flow3] which is not part of the existing configuration.
    3. Validate:
        - Throw error showing flow name is not part of existing configuration.
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
    cd = api.config_delete()
    cd.config_delete_list.add().flows = ["tx_flow3"]
    try:
        api.delete_flows(cd)
        assert False
    except Exception as e:
        print(e)


if __name__ == "__main__":
    pytest.main(["-s", __file__])