import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import FlowTransmit


def test_flow_duration(serializer, tx_port, rx_port, b2b_ipv4_device_groups, api):
    """
    This will test different transmit durations:
    [1] Fixed : A fixed number of packets will be transmitted after which the flow will stop
                If the number of packets is set to 0 the flow will not stop
        Args
        ----
        - packets (int): Stop transmit of the flow after this number of packets. A value of 0 means that the flow will not stop transmitting
        - gap (int): The minimum gap between packets expressed as bytes
        - delay (int): The delay before starting transmission of packets
        - delay_unit (Union[bytes, nanoseconds]): The delay expressed as a number of this value
    
    [2] Burst : A continuous burst of packets that will not automatically stop
        Args
        ----
        - packets (int): The number of packets transmitted per burst
        - gap (int): The minimum gap between packets expressed as bytes
        - inter_burst_gap (int): The gap between the transmission of each burst. A value of 0 means there is no gap between bursts
        - inter_burst_gap_unit (Union[bytes, nanoseconds]): The inter burst gap expressed as a number of this value
    """
    data_endpoint = DeviceEndpoint(tx_device_names=[b2b_ipv4_device_groups[0].name],
        rx_device_names=[b2b_ipv4_device_groups[1].name],
        packet_encap='ipv4',
        src_dst_mesh='',
        route_host_mesh='',
        bi_directional=False,
        allow_self_destined=False)

    # Test for Continuous Flow
    test_continuous_continuous = Flow(name='Continuous Duration',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(Ethernet()),
            Header(Vlan()),
            Header(Ipv4())
        ],
        duration=Duration(Fixed(packets=0, delay=22)))

    # Test for Fix Duration with Gap and Delay
    test_fixed_duration = Flow(name='Fixed Duration',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(Ethernet()),
            Header(Vlan()),
            Header(Ipv4())
        ],
        duration=Duration(Fixed(packets=800, gap=2, delay=8,delay_unit='bytes')))

    # Test for Burst Duration with Gap and inter burst gap
    test_burst_duration = Flow(name='Burst Duration',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(Ethernet()),
            Header(Vlan()),
            Header(Ipv4())
        ],
        duration=Duration(Burst(packets=700, gap=8, inter_burst_gap=4, inter_burst_gap_unit='nanoseconds')))

    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        device_groups=b2b_ipv4_device_groups,
        flows = [
            test_continuous_continuous,
            test_fixed_duration,
            test_burst_duration
        ]
    )
    print(serializer.json(config))

    api.set_config(None)
    api.set_config(config)

if __name__ == '__main__':
    pytest.main(['-s', __file__])
