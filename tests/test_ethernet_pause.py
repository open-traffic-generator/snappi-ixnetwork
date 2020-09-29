import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import FlowTransmit
from abstract_open_traffic_generator.result import PortRequest, FlowRequest


def test_ethernet_pause_flows(serializer, tx_port, rx_port, b2b_ipv4_device_groups, api):
    """EthernetPause test traffic configuration
    """
    pause_endpoint = PortEndpoint(tx_port_name=tx_port.name,
                                  rx_port_names=[rx_port.name])
    default_pause = Header(EthernetPause(
        dst=Pattern('01:80:C2:00:00:01'),
        src=Pattern('00:00:fa:ce:fa:ce')
    ))
    default_pause_flow = Flow(name='Default EthernetPause',
                      endpoint=Endpoint(pause_endpoint),
                      packet=[default_pause],
                      size=Size(64),
                      rate=Rate('line', value=100),
                      duration=Duration(FixedPackets(packets=100)))
    
    data_pause = Header(EthernetPause(
        dst=Pattern('01:80:C2:00:00:01'),
        src=Pattern('00:00:fa:ce:fa:ce'),
        control_op_code=Pattern('2'),
        time=Pattern('FF11')
    ))
    data_pause_flow = Flow(name='Data EthernetPause',
                      endpoint=Endpoint(pause_endpoint),
                      packet=[data_pause],
                      size=Size(64),
                      rate=Rate('line', value=100),
                      duration=Duration(FixedPackets(packets=100)))
    
    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        device_groups=b2b_ipv4_device_groups,
        flows=[
            default_pause_flow,
            data_pause_flow
        ]
    )
    print(serializer.json(config))
    
    api.set_config(None)
    api.set_config(config)

if __name__ == '__main__':
    pytest.main(['-s', __file__])
