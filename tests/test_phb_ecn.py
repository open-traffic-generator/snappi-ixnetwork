import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import Config


def test_phb_ecn(serializer, api, tx_port, rx_port):
    """
    This will test that phb and ecn are set on an ipv4 header
    """
    port_endpoint = PortTxRx(tx_port_name=tx_port.name, 
        rx_port_names=[rx_port.name])
    dscp = Dscp(phb=Pattern([Dscp.PHB_CS2, Dscp.PHB_CS1, Dscp.PHB_CS5]), 
        ecn=Pattern(Dscp.ECN_CAPABLE_TRANSPORT_1))
    priority = Priority(dscp)
    ipv4 = Ipv4(priority=priority)
    flow = Flow(name='Ipv4 with Phb and Ecn',
        tx_rx=TxRx(port_endpoint),
        packet=[Header(Ethernet()), Header(ipv4)])
    config = Config(ports=[tx_port, rx_port], flows=[flow])
    print(serializer.json(config))
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
