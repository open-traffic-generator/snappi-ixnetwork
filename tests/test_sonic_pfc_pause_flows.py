import pytest


def test_sonic_pfc_pause_flows(serializer, tx_port, rx_port, b2b_ipv4_device_groups, api):
    from abstract_open_traffic_generator.flow import Flow, Endpoint, DeviceEndpoint, PortEndpoint
    from abstract_open_traffic_generator.flow import Header, Ethernet, Vlan, Ipv4, PfcPause, Pattern
    from abstract_open_traffic_generator.flow import Size, Duration, Rate, Fixed
    from abstract_open_traffic_generator.flow_ipv4 import Priority, Dscp
    from abstract_open_traffic_generator.config import Config
    
    data_endpoint = DeviceEndpoint(tx_devices=[b2b_ipv4_device_groups[0].name],
        rx_devices=[b2b_ipv4_device_groups[1].name],
        packet_encap='ipv4',
        src_dst_mesh='',
        route_host_mesh='',
        bi_directional=False,
        allow_self_destined=False)

    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7)))
    test_flow = Flow(name='Test Data',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(Ethernet()), 
            Header(Vlan()), 
            Header(Ipv4(priority=test_dscp))
        ],
        size=Size(128),
        rate=Rate('line', 50),
        duration=Duration(Fixed(packets=0)))

    background_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS1)))
    background_flow = Flow(name='Background Data',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(Ethernet()), 
            Header(Vlan()), 
            Header(Ipv4(priority=background_dscp))
        ],
        size=Size(128),
        rate=Rate('line', 50),
        duration=Duration(Fixed(packets=0)))

    pause_endpoint = PortEndpoint(tx_port=tx_port.name)
    pause = Header(PfcPause(
        dst=Pattern('01:80:C2:00:00:01'),
        class_enable_vector=Pattern('1'),
        pause_class_0=Pattern('1')
    ))
    pause_flow = Flow(name='Pause Storm',
        endpoint=Endpoint(pause_endpoint),
        packet=[pause],
        size=Size(64),
        rate=Rate('line', value=100),
        duration=Duration(Fixed(packets=0)))

    config = Config(
        ports=[
            tx_port, 
            rx_port
        ], 
        device_groups=b2b_ipv4_device_groups,
        flows = [
            test_flow,
            background_flow,
            pause_flow
        ]
    )
    print(serializer.json(config))

    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
