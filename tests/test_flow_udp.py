import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *


def test_flow_udp(serializer, options, tx_port, rx_port, api):
    """UDP Flow test traffic configuration
    """
    udp_endpoint = PortTxRx(tx_port_name=tx_port.name,
                            rx_port_name=rx_port.name)
    test_dscp = Priority(
        Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    udp_header = Udp(src_port=Pattern(Counter(start="12001",
                                              step="2",
                                              count=100),
                                      ingress_result_name='UDP SRC PORT'),
                     dst_port=Pattern("20"))
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
                    duration=Duration(FixedPackets(packets=100000)))

    config = Config(ports=[tx_port, rx_port],
                    flows=[udp_flow],
                    options=options)
    state = State(ConfigState(config=config, state='set'))
    print(serializer.json(state))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
