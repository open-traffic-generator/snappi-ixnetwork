import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *


def test_flow_tcp(serializer, tx_port, rx_port, b2b_ipv4_devices, api):
    """TCP Flow test traffic configuration
    """
    tcp_endpoint = DeviceTxRx(tx_device_names=[b2b_ipv4_devices[0].name],
                              rx_device_names=[b2b_ipv4_devices[1].name])

    test_dscp = Priority(
        Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    tcp_header = Tcp(src_port=Pattern("11102"),
                     dst_port=Pattern("443",
                                      ingress_result_name="Tcp Dst Port"),
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
                    duration=Duration(FixedPackets(packets=0)))

    config = Config(ports=[tx_port, rx_port],
                    devices=b2b_ipv4_devices,
                    flows=[tcp_flow])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
