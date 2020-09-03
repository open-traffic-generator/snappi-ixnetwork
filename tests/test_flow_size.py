import pytest


def test_sonic_pfc_pause_flows(serializer, tx_port, rx_port, b2b_ipv4_device_groups):
    """
    This will test supported Flow Size
            'float': 'fixed',
            'int': 'fixed',
            'SizeIncrement': 'increment',
            'SizeRandom': 'random',
    """
    
    from abstract_open_traffic_generator.flow import Flow, Endpoint, DeviceEndpoint, PortEndpoint
    from abstract_open_traffic_generator.flow import Header, PfcPause, Pattern
    from abstract_open_traffic_generator.flow import Duration, Rate, Fixed
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.flow import Size, SizeIncrement, SizeRandom
    
    port_endpoint = PortEndpoint(tx_port=tx_port.name, rx_ports=[rx_port.name])
    pause = Header(PfcPause(
        dst=Pattern('01:80:C2:00:00:01'),
        class_enable_vector=Pattern('1'),
        pause_class_0=Pattern('1')
    ))
    fixed_size = Flow(name='Fixed Size',
                      endpoint=Endpoint(port_endpoint),
                      packet=[pause],
                      size=Size(44),
                      rate=Rate('line', value=100),
                      duration=Duration(Fixed(packets=0)))
    
    increment = SizeIncrement(start=100, end=1200, step=10)
    increment_size = Flow(name='Increment Size',
                      endpoint=Endpoint(port_endpoint),
                      packet=[pause],
                      size=Size(increment),
                      rate=Rate('line', value=100),
                      duration=Duration(Fixed(packets=0)))
    
    random = SizeRandom()
    random_size = Flow(name='Random Size',
                      endpoint=Endpoint(port_endpoint),
                      packet=[pause],
                      size=Size(random),
                      rate=Rate('line', value=100),
                      duration=Duration(Fixed(packets=0)))
    
    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        flows=[
            fixed_size,
            increment_size,
            random_size
        ]
    )
    print(serializer.json(config))
    
    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
    # set the ixnetwork connection parameters
    api = IxNetworkApi('10.15.82.252', port=11009)
    # clear the configuration on ixnetwork by passing in None
    api.set_config(None)
    # set the configuration on ixnetwork
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
