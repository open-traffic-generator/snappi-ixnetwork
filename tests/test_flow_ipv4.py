import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *


def test_flow_ipv4(serializer, tx_port, rx_port, b2b_simple_device, api):
    """IPv4 Flow with different priority test traffic configuration
    """
    device_tx_rx = DeviceTxRx(tx_device_names=[b2b_simple_device[0].devices[0].name],
                              rx_device_names=[b2b_simple_device[1].devices[0].name])
    
    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    ip_dscp_flow = Flow(name='IPv4 DSCP',
                    tx_rx=TxRx(device_tx_rx),
                    packet=[
                        Header(Ethernet()),
                        Header(Vlan()),
                        Header(Ipv4(priority=test_dscp)),
                    ],
                    size=Size(128),
                    rate=Rate('line', 50),
                    duration=Duration(Fixed(packets=0)))
    
    # Probably Tos.HIGH rather than Tos.LOW
    test_tos = Priority(Tos(precedence=Pattern(Tos.PRE_FLASH_OVERRIDE, ingress_result_name='tos precedence'),
                            delay=Pattern(Tos.NORMAL),
                            throughput=Pattern(Tos.LOW),
                            reliability=Pattern(Tos.NORMAL),
                            monetary=Pattern(Tos.LOW),
                            unused=Pattern(Tos.LOW)))
    ip_tos_flow = Flow(name='IPv4 TOS',
                        tx_rx=TxRx(device_tx_rx),
                        packet=[
                            Header(Ethernet()),
                            Header(Vlan()),
                            Header(Ipv4(priority=test_tos)),
                        ],
                        size=Size(128),
                        rate=Rate('line', 50),
                        duration=Duration(Fixed(packets=0)))
    
    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        flows=[
            ip_dscp_flow,
            ip_tos_flow,
        ]
    )
    print(serializer.json(config))
    
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
