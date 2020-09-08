import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *


def test_sonic_pfc_pause_flows(serializer, tx_port, rx_port, b2b_ipv4_device_groups, api):
    """
    A unique name that can be used to drill down into flow results.
    The name will appears as one of the group_by options in requesting flow results and as a property in a flow result
    group_by will configure through Pattern. This test will covered following group_by within traffic items
        -Test Data:
            VLAN - priority (priority=Pattern(choice='1', group_by='VLAN priority'))
            Ipv4 - src (src=Pattern(group_by='IPv4 src'))
        - Pause Storm
            PfcPause - src (src=Pattern('00:00:fa:ce:fa:ce', group_by='PfcPause src'))
    """
    data_endpoint = DeviceEndpoint(tx_device_names=[b2b_ipv4_device_groups[0].name],
        rx_device_names=[b2b_ipv4_device_groups[1].name],
        packet_encap='ipv4',
        src_dst_mesh='',
        route_host_mesh='',
        bi_directional=False,
        allow_self_destined=False)

    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7)))
    test_flow = Flow(name='Test Data',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(Ethernet()),
            Header(Vlan(priority=Pattern(choice='1', group_by='VLAN priority'))),
            Header(Ipv4(src=Pattern(group_by='IPv4 src'),priority=test_dscp))
        ],
        size=Size(128),
        rate=Rate('line', 50),
        duration=Duration(Fixed(packets=0)))

    pause_endpoint = PortEndpoint(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    pause = Header(PfcPause(
        dst=Pattern('01:80:C2:00:00:01'),
        src=Pattern('00:00:fa:ce:fa:ce', group_by='PfcPause src'),
        class_enable_vector=Pattern('1'),
        pause_class_0=Pattern('3'),
        pause_class_1=Pattern(Counter(start='2', step='6', count=99)),
        pause_class_2=Pattern(Counter(start='1', step='6', count=99, up=False)),
        pause_class_3=Pattern(['6', '9', '2', '39']),
        pause_class_4=Pattern(Random(min='11', max='33', step=1, seed='4', count=10))
    ))
    pause_flow = Flow(name='Pause Storm',
        endpoint=Endpoint(pause_endpoint),
        packet=[pause],
        size=Size(64),
        rate=Rate('line', value=100),
        duration=Duration(Fixed(packets=0)))

    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        device_groups=b2b_ipv4_device_groups,
        flows = [
            test_flow,
            pause_flow
        ]
    )
    print(serializer.json(config))

    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
