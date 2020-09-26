import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *


def test_flow_udp(serializer, tx_port, rx_port, b2b_simple_device, api):
    """UDP Flow test traffic configuration
    """
    udp_endpoint = DeviceTxRx(tx_device_names=[b2b_simple_device[0].devices[0].name],
                              rx_device_names=[b2b_simple_device[1].devices[0].name])
    
    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    udp_header = Udp(src_port=Pattern(Counter(start="12001",step="2",count=100)),
                     dst_port=Pattern("20", ingress_result_name="UDP dst port"))
    udp_flow = Flow(name='UDP Flow',
                    tx_rx=TxRx(udp_endpoint),
                    packet=[
                        Header(Ethernet()),
                        Header(Vlan()),
                        Header(Ipv4(priority=test_dscp)),
                        Header(udp_header)
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
            udp_flow
        ]
    )
    print(serializer.json(config))
    
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
