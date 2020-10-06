import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.result import FlowRequest
from abstract_open_traffic_generator.control import *


def test_flow_results(serializer, api, options, b2b_simple_device):
    """Demonstrates how to retrieve flow results
    """
    device_endpoint = DeviceTxRx(tx_device_names=[b2b_simple_device[0].devices[0].name],
        rx_device_names=[b2b_simple_device[1].devices[0].name])

    flow1 = Flow(name='B2B Flow 1',
        tx_rx=TxRx(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 10000),
        duration=Duration(FixedPackets(packets=1000)))
    flow2 = Flow(name='B2B Flow 2',
        tx_rx=TxRx(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 100),
        duration=Duration(FixedPackets(packets=1000)))

    import time
    start = time.time()
    config = Config(ports=b2b_simple_device, 
        flows=[flow1, flow2], 
        options=options)
    api.set_state(State(ConfigState(config=config, state='set')))
    print('set_config %0.2fs' % (time.time() - start))

    start = time.time()
    api.set_state(State(FlowTransmitState(state='start')))
    print('set_flow_transmit %0.2fs' % (time.time() - start))

    # test all flow_names, first flow only, second flow only
    start = time.time()
    for names in [[], [flow1.name], [flow2.name]]:
        for row in api.get_flow_results(FlowRequest(flow_names=names)):
            print(row)
    print('get_flow_results %0.2fs' % (time.time() - start))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
