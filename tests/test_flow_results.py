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

    flow = Flow(name='B2B Flow',
        endpoint=Endpoint(device_endpoint),
        size=Size(128),
        rate=Rate('pps', 10000),
        duration=Duration(Fixed(packets=0)))

    import time
    start = time.time()
    config = Config(ports=[tx_port, rx_port], 
        device_groups=b2b_ipv4_device_groups, 
        flows=[flow], 
        options=options)
    api.set_config(config)
    print('set_config %s' % str(time.time() - start))

    start = time.time()
    transmit = FlowTransmit(state='start')
    api.set_flow_transmit(transmit)
    print('set_flow_transmit %s' % str(time.time() - start))

    start = time.time()
    request = FlowRequest()
    results = api.get_flow_results(request)
    print(results['columns'])
    for row in results['rows']:
        print(row)
    print('get_flow_results %s' % str(time.time() - start))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
