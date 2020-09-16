"""
Sonic test structure based on the open-traffic-generator models

Tests using the open-traffic-generator models should use fixtures as much as 
possible to populate configurations.  The configurations can then be used in 
test logic.

The following code demonstrates a modular approach to the pfc lossy test
- fixture port_layer1_device_configs
- fixture pfc_pause_configs
- test_pfc_pause_lossy_traffic

NOTE: There is no need to add an import for parameters that are part of fixtures
or methods. 
"""
import logging
import time
import pytest
import json
from tests.common.reboot import logger
from tests.common.helpers.assertions import pytest_assert
from tests.common.ixia.ixia_helpers import IxiaFanoutManager, get_location
from tests.common.ixia.common_helpers import get_vlan_subnet, get_addrs_in_subnet


@pytest.fixture
def port_layer1_device_configs(fanout_graph_facts, conn_graph_facts, duthost):
    """port_layer1_device_configs fixture
    
    - Common port, layer1, device configuration should be in one fixture
    - To reduce import conflicts move them into the fixture
    - Don't import things that are not needed
    - Don't add parameters to the method that are not needed
     
    Returns
    -------
    - list(Config): A list of Config objects
    """
    from abstract_open_traffic_generator.config import Config, Options
    from abstract_open_traffic_generator.port import Port, PortOptions
    from abstract_open_traffic_generator.layer1 import Layer1, OneHundredGbe, FlowControl, Ieee8021qbb
    from abstract_open_traffic_generator.device import DeviceGroup, Device, Ethernet, Ipv4

    fanout_devices = IxiaFanoutManager(fanout_graph_facts)
    fanout_devices.get_fanout_device_details(device_number=0)
    device_conn = conn_graph_facts['device_conn']

    configs = []
    for i in range(len(available_phy_port)):
        rx_id = i
        tx_id = (i + 1) % len(available_phy_port)
        tx_location = get_location(available_phy_port[tx_id])
        rx_location = get_location(available_phy_port[rx_id])
        tx_speed = available_phy_port[tx_id]['speed']
        rx_speed = available_phy_port[rx_id]['speed']
        pytest_assert(tx_speed == rx_speed,
            "Tx bandwidth must be equal to Rx bandwidth") 
        vlan_subnet = get_vlan_subnet(duthost)
        pytest_assert(vlan_subnet is not None,
                      "Fail to get Vlan subnet information")
        vlan_ip_addrs = get_addrs_in_subnet(vlan_subnet, 2)
        gw_addr = vlan_subnet.split('/')[0]
        interface_ip_addr = vlan_ip_addrs[0]
        
        tx = Port(name='Tx', location=tx_location)
        rx = Port(name='Rx', location=rx_location)
        pfc = Ieee8021qbb(pfc_delay=1,
                    pfc_class_0=0,
                    pfc_class_1=1,
                    pfc_class_2=2,
                    pfc_class_3=3,
                    pfc_class_4=4,
                    pfc_class_5=5,
                    pfc_class_6=6,
                    pfc_class_7=7)
        flow_ctl = FlowControl(choice=pfc)
        l1_oneHundredGbe = OneHundredGbe(link_training=True,
                                     ieee_media_defaults=False,
                                     auto_negotiate=False,
                                     speed='one_hundred_gbps',
                                     flow_control=flow_ctl,
                                     rs_fec=True)
        layer1 = Layer1(name='common L1 config',
                              choice=l1_oneHundredGbe,
                              port_names=[tx.name, rx.name])
        tx_ipv4 = Ipv4(name='Tx Ipv4',
                    address=Pattern(vlan_ip_addrs[1]),
                    prefix=Pattern('24'),
                    gateway=Pattern(gw_addr))
        tx_ethernet = Ethernet(name='Tx Ethernet', ipv4=tx_ipv4)
        tx_device = Device(name='Tx Device',
                        devices_per_port=1,
                        ethernets=[tx_ethernet])
        tx_device_group = DeviceGroup(name='Tx Device Group',
                                    port_names=[tx.name],
                                    devices=[tx_device])
        rx_ipv4 = Ipv4(name='Rx Ipv4',
                    address=Pattern(vlan_ip_addrs[0]),
                    prefix=Pattern('24'),
                    gateway=Pattern(gw_addr))
        rx_ethernet = Ethernet(name='Rx Ethernet', ipv4=rx_ipv4)
        rx_device = Device(name='Rx Device',
                        devices_per_port=1,
                        ethernets=[rx_ethernet])
        rx_device_group = DeviceGroup(name='Rx Device Group',
                                    port_names=[rx.name],
                                    devices=[rx_device])
        config = Config(ports=[tx, rx], 
            layer1=[layer1], 
            device_groups=[tx_device_group, rx_device_group],
            options=Options(PortOptions(location_preemption=True)))
        configs.append(config)
    return configs


@pytest.fixture
def pfc_pause_traffic_configs(port_layer1_device_configs, lossless_prio_dscp_map):
    """pfc pause traffic fixture

    Builds on the port_layer1_device_configs setup in another fixture

    Setting up pfc pause traffic seems to be common so setup a fixture for it
    to populate the existing configs with pfc pause flows
    - common pfc pause traffic setup should be in one fixture
    - To reduce import conflicts move them into the fixture
    - Don't import things that are not needed
    - Don't add parameters to the method that are not needed
    """
    from abstract_open_traffic_generator.flow import Flow, Ethernet, Ipv4, \
        Priority, Dscp, PfcPause, DeviceEndpoint, PortEndpoint

    bg_dscp_list = [prio for prio in lossless_prio_dscp_map]
    test_data_priority = [x for x in range(64) if x not in bg_dscp_list]

    for config in port_layer1_device_configs:
        test_dscp = Priority(Dscp(phb=PATTERN(choice=test_data_priority)))
        test_flow = Flow(
            name=test_flow_name,
            endpoint=Endpoint(data_endpoint),
            packet=[
                Header(choice=ETHERNET()),
                Header(choice=IPV4(priority=test_dscp))
            ],
            size=Size(1024),
            rate=Rate('line', test_line_rate),
            duration=Duration(Fixed(packets=0, delay=start_delay, delay_unit='nanoseconds'))
        )
        config.flows.append(test_flow)

        background_dscp = Priority(Dscp(phb=PATTERN(choice=background_data_priority)))
        background_flow = Flow(
            name=background_flow_name,
            endpoint=Endpoint(data_endpoint),
            packet=[
                Header(choice=ETHERNET()),
                Header(choice=IPV4(priority=background_dscp))
            ],
            size=Size(1024),
            rate=Rate('line', background_line_rate),
            duration=Duration(Fixed(packets=0, delay=start_delay, delay_unit='nanoseconds'))
        )
        cofig.flows.append(background_flow)

        pause_endpoint = PortEndpoint(tx_port_name=rx.name, rx_port_names=[rx.name])
        pause = Header(PfcPause(
            dst=PATTERN(choice='01:80:C2:00:00:01'),
            src=PATTERN(choice='00:00:fa:ce:fa:ce'),
            class_enable_vector=PATTERN(choice='E7'),
            pause_class_0=PATTERN(choice='ffff'),
            pause_class_1=PATTERN(choice='ffff'),
            pause_class_2=PATTERN(choice='ffff'),
            pause_class_3=PATTERN(choice='0'),
            pause_class_4=PATTERN(choice='0'),
            pause_class_5=PATTERN(choice='ffff'),
            pause_class_6=PATTERN(choice='ffff'),
            pause_class_7=PATTERN(choice='ffff'),
        ))
        pause_flow = Flow(
            name='Pause Storm',
            endpoint=Endpoint(pause_endpoint),
            packet=[pause],
            size=Size(64),
            rate=Rate('line', value=pause_line_rate),
            duration=Duration(Fixed(packets=0, delay=0, delay_unit='nanoseconds'))
        )
        config.flows.append(pause_flow)
    return port_layer_device_configs


def test_pfc_pause_lossy_traffic(api, pfc_pause_traffic_configs, duthost):
    """test_pfc_pause_lossy_traffic

    Uses the configs from the pfc_pause_traffic_configs fixture

    - To reduce import conflicts move them into the test
    - Don't import things that are not needed
    - Don't add parameters to the method that are not needed
    """
    from abstract_open_traffic_generator.control import FlowTransmit
    from abstract_open_traffic_generator.result import FlowRequest

    for config in pfc_pause_traffic_configs:
        api.set_config(config) 

        # start all flows
        api.set_flow_transmit(FlowTransmit('start'))

        exp_dur = START_DELAY + TRAFFIC_DURATION
        logger.info("Traffic is running for %s seconds" %(exp_dur))
        time.sleep(exp_dur)

        # stop all flows
        api.set_flow_transmit(FlowTransmit('stop'))

        # Get statistics
        test_stat = api.get_flow_results(FlowRequest())

        for rows in test_stat['rows'] :
            tx_frame_index = test_stat['columns'].index('frames_tx')
            rx_frame_index = test_stat['columns'].index('frames_rx')
            caption_index = test_stat['columns'].index('name')   
            if ((rows[caption_index] == 'Test Data') or
                (rows[caption_index] == 'Background Data')):
                if rows[tx_frame_index] != rows[rx_frame_index] :
                    pytest_assert(False,
                        "Not all %s reached Rx End" %(rows[caption_index]))
