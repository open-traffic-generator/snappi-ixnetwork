import pytest


def test_sonic_pfc_pause_flows(serializer, tx_port, rx_port, b2b_ipv4_device_groups):
    """
    This will test supported Flow Rate
        - unit (Union[pps, bps, kbps, mbps, gbps, line]): The value is a unit of this
        - value (Union[float, int]): The actual rate
        - gap (Union[float, int]): The minimum gap in bytes between packets
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
    
    rate_line = Flow(name='Line Rate',
                      endpoint=Endpoint(port_endpoint),
                      packet=[pause],
                      size=Size(44),
                      rate=Rate('line', value=100),
                      duration=Duration(Fixed(packets=0)))

    rate_pps = Flow(name='pps Rate',
                     endpoint=Endpoint(port_endpoint),
                     packet=[pause],
                     size=Size(44),
                     rate=Rate('pps', value=2000),
                     duration=Duration(Fixed(packets=0)))

    rate_bps = Flow(name='bps Rate',
                    endpoint=Endpoint(port_endpoint),
                    packet=[pause],
                    size=Size(44),
                    rate=Rate('bps', value=700),
                    duration=Duration(Fixed(packets=0)))

    rate_kbps = Flow(name='kbps Rate',
                    endpoint=Endpoint(port_endpoint),
                    packet=[pause],
                    size=Size(44),
                    rate=Rate('kbps', value=800),
                    duration=Duration(Fixed(packets=0)))

    rate_gbps = Flow(name='gbps Rate',
                     endpoint=Endpoint(port_endpoint),
                     packet=[pause],
                     size=Size(44),
                     rate=Rate('gbps', value=800),
                     duration=Duration(Fixed(packets=0)))
    
    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        flows=[
            rate_line,
            rate_pps,
            rate_bps,
            rate_kbps,
            rate_gbps
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
