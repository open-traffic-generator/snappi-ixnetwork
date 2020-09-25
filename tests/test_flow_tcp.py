import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import FlowTransmit
from abstract_open_traffic_generator.result import PortRequest, FlowRequest


def test_flow_tcp(serializer, tx_port, rx_port, b2b_simple_device, api):
    """Pfc pause lossless test traffic configuration
    """
    tcp_endpoint = DeviceTxRx(tx_device_names=[b2b_simple_device[0].devices[0].name],
                                   rx_device_names=[b2b_simple_device[1].devices[0].name])
    
    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    tcp_header = Tcp(src_port=Pattern("11102"),
                     dst_port=Pattern("443", ingress_result_name="Tcp Dst Port"),
                     ecn_ns=Pattern("1"),
                     ecn_cwr=Pattern("0"),
                     ecn_echo=Pattern("1"),
                     ctl_urg=Pattern("0"),
                     ctl_ack=Pattern("1"),
                     ctl_psh=Pattern("1"),
                     ctl_rst=Pattern("0"),
                     ctl_syn=Pattern("1"),
                     ctl_fin=Pattern("1"))
    tcp_flow = Flow(name='TCP Flow',
                    tx_rx=TxRx(tcp_endpoint),
                     packet=[
                         Header(Ethernet()),
                         Header(Vlan()),
                         Header(Ipv4(priority=test_dscp)),
                         Header(tcp_header)
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
            tcp_flow
        ]
    )
    print(serializer.json(config))
    
    api.set_config(None)
    api.set_config(config)

if __name__ == '__main__':
    pytest.main(['-s', __file__])
