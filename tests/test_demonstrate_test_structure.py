import pytest



@pytest.fixture
def base_configs(test_bed, conn_graph_facts, dut_host, api, lossless_prio_dscp_map):
    """This fixture should not be in a test and should be made generic 
    enough to accomodate a wide range of tests using the input parameters.
    
    Use this fixture to create a list of per test config objects 
    that are currently created inside of tests.

    base_configs would typically be populated by this logic:

    fanout_devices = IxiaFanoutManager(fanout_graph_facts)
    fanout_devices.get_fanout_device_details(device_number=0)
    device_conn = conn_graph_facts['device_conn']

    # The number of ports should be at least two for this test
    available_phy_port = fanout_devices.get_ports()
    pytest_assert(len(available_phy_port) > 2,
                  "Number of physical ports must be at least 2")

    # Get interface speed of peer port
    for intf in available_phy_port:
        peer_port = intf['peer_port']
        intf['speed'] = int(device_conn[peer_port]['speed'])


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

        bg_dscp_list = [prio for prio in lossless_prio_dscp_map]
        test_dscp_list = [x for x in range(64) if x not in bg_dscp_list]    
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.port import Port
    from abstract_open_traffic_generator.layer1 import Layer1

    configs = []
    for i in range(len(available_phy_port)):
        # ports
        tx = Port(name='Tx', location=phy_tx_port)
        rx = Port(name='Rx', location=phy_rx_port)
        # layer1
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
            choice=one_hundred_gbe,
            port_names=[tx.name, rx.name])
        # config
        config = Config(ports=[tx, rx], layer1=[layer1])
        configs.append(config)
    return configs

def test_pfc_lossy(base_configs, api):
    """Iterate through base_configs using each base_config to run a test.
    """
    import json
    for base_config in base_configs:
        # fill in the remainder of the base_config
        #    the remainder of the test config should be kept in the same file as the test
        #    which makes it easier to read
        #    things like specific flow headers, rate, duration etc 
        # api.set_config(base_config)
        # api.set_flow_transmit()
        # api.get_flow_results()
        pass

if __name__ == '__main__':
    pytest.main(['-s', __file__])