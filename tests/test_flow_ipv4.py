import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *


def test_flow_ipv4(serializer, tx_port, rx_port, api):
    """IPv4 Flow with different priority test traffic configuration
    """
    raw_tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    
    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    ip_dscp_flow = Flow(name='IPv4 DSCP',
                    tx_rx=TxRx(raw_tx_rx),
                    packet=[
                        Header(Ethernet()),
                        Header(Vlan()),
                        Header(Ipv4(priority=test_dscp)),
                    ],
                    size=Size(128),
                    rate=Rate('line', 50),
                    duration=Duration(Fixed(packets=0)))
    
    test_tos = Priority(Tos(precedence=Pattern('7'),
                            delay=Pattern('1'),
                            throughput=Pattern('1'),
                            reliability=Pattern('1'),
                            monetary=Pattern('1'),
                            unused=Pattern('1')))
    ip_tos_flow = Flow(name='IPv4 TOS',
                        tx_rx=TxRx(raw_tx_rx),
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
            ip_tos_flow,
            
        ]
    )
    print(serializer.json(config))
    
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
