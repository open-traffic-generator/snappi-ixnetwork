import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import FlowTransmit
from abstract_open_traffic_generator.result import FlowRequest


def test_flow_results(serializer, api, options, tx_port, rx_port, b2b_ipv4_device_groups):
    """Demonstrates how to retrieve flow results
    """
    device_endpoint = DeviceEndpoint(tx_device_names=[b2b_ipv4_device_groups[0].name],
        rx_device_names=[b2b_ipv4_device_groups[1].name],
        packet_encap='ipv4')

    flow1 = Flow(name='B2B Flow 1',
        endpoint=Endpoint(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 10000),
        duration=Duration(Fixed(packets=0)))
    flow2 = Flow(name='B2B Flow 2',
        endpoint=Endpoint(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 100),
        duration=Duration(Fixed(packets=0)))

    import time
    start = time.time()
    config = Config(ports=[tx_port, rx_port], 
        device_groups=b2b_ipv4_device_groups, 
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
