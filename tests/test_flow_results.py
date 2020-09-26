import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import FlowTransmit
from abstract_open_traffic_generator.result import FlowRequest


def test_flow_results(serializer, api, options, b2b_simple_device):
    """Demonstrates how to retrieve flow results
    """
    device_endpoint = DeviceTxRx(tx_device_names=[b2b_simple_device[0].devices[0].name],
        rx_device_names=[b2b_simple_device[1].devices[0].name])

    flow1 = Flow(name='B2B Flow 1',
        tx_rx=TxRx(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 10000),
        duration=Duration(Fixed(packets=0)))
    flow2 = Flow(name='B2B Flow 2',
        tx_rx=TxRx(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 100),
        duration=Duration(Fixed(packets=0)))

    import time
    start = time.time()
    config = Config(ports=b2b_simple_device, 
        flows=[flow1, flow2], 
        options=options)
    api.set_config(config)
    print('set_config %0.2fs' % (time.time() - start))

    start = time.time()
    transmit = FlowTransmit(state='start')
    api.set_flow_transmit(transmit)
    print('set_flow_transmit %0.2fs' % (time.time() - start))

    # test all flow_names, first flow only, second flow only
    start = time.time()
    for name in [[], [flow1.name], [flow2.name]]:
        request = FlowRequest(flow_names=name)
        results = api.get_flow_results(request)
        print(results['columns'])
        for row in results['rows']:
            print(row)
    print('get_flow_results %0.2fs' % (time.time() - start))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
