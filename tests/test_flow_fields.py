import pytest
from abstract_open_traffic_generator.port import Port
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.control import *


def test_flow_fields(serializer, api):
    """
    This will test setting values for individual flow packet fields
    """
    port = Port(name='port')
    port_endpoint = PortEndpoint(tx_port_name=port.name)

    mac_counter = Counter(start='00:00:fa:ce:fa:ce',
        step='00:00:01:02:03:04',
        count=7)
    ethernet = Ethernet(dst=Pattern(mac_counter),
        src=Pattern(mac_counter),
    )
    vlan1 = Vlan(priority=Pattern('1'),
        id=Pattern(Counter(start='67', step='3', count=9)))
    vlan2 = Vlan(id=Pattern(Counter(start='34', step='2', count=5)))
    ipv4 = Ipv4()
    flow = Flow(name=__name__,
        endpoint=Endpoint(port_endpoint),
        packet=[
            Header(ethernet),
            Header(vlan1),
            Header(vlan2),
            Header(ipv4)
        ]
    )
    config = Config(ports=[port], flows=[flow])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])    
