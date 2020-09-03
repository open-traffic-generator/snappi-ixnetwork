from abstract_open_traffic_generator.port import Port, OneHundredGbe, Layer1
from abstract_open_traffic_generator.device import DeviceGroup, Device
from abstract_open_traffic_generator.device import Ethernet, Vlan, Ipv4
from abstract_open_traffic_generator.device import Pattern
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.flow import DeviceEndpoint, Endpoint, Flow, Header, Size, Rate,\
    Duration, Fixed, PortEndpoint, PfcPause, Counter, Random

################################################################################
# COMMENTS
# 1. Some classes defined "abstract_open_traffic_generator.device" and
#    "abstract_open_traffic_generator.flow" has the same name. Like Ipv4, Vlan,
#    Ethernet, Pattern. Different name required.
################################################################################
from abstract_open_traffic_generator.flow import Pattern as PATTERN
from abstract_open_traffic_generator.flow import Ipv4 as IPV4
from abstract_open_traffic_generator.flow import Vlan as VLAN
from abstract_open_traffic_generator.flow import Ethernet as ETHERNET
from abstract_open_traffic_generator.flow_ipv4 import Priority, Dscp

from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi


TX_LOCATION = '10.36.78.53;9;1'
RX_LOCATION = '10.36.78.53;9;2'
API_SERVER  = '10.36.78.242'
PORT        = '443'

def run_pfc_pause_lossy_traffic_test(serializer,
                                     api,
                                     phy_tx_port,
                                     phy_rx_port,
                                     port_speed,
                                     tx_port_ip='0.0.0.0',
                                     rx_port_ip='0.0.0.0',
                                     tx_gateway_ip='0.0.0.0',
                                     rx_gateway_ip='0.0.0.',
                                     tx_ip_incr='0.0.0.0',
                                     rx_ip_incr='0.0.0.0',
                                     tx_gateway_incr='0.0.0.0',
                                     rx_gateway_incr='0.0.0.0'):
    ########################################################################### 
    # TX port 
    ########################################################################### 
    tx = Port(name='Tx', location=phy_tx_port, link='up')

    ########################################################################### 
    # RX port  
    ########################################################################### 
    rx = Port(name='Rx', location=phy_rx_port, link='up')

    ########################################################################### 
    # Tx + Rx port commom L1 config
    # COMMENT --> This is not comming up
    # auto_negotiate=False --> is not working.
    # ieee_media_defaults=False is now working --> issue resolved 
    ########################################################################### 
    l1_oneHundredGbe = OneHundredGbe(link_training=True,
                                     ieee_media_defaults=False,
                                     auto_negotiate=False,
                                     speed='one_hundred_gbps',
                                     rs_fec=True)

    common_l1_config = Layer1(name='common L1 config',
                              choice=l1_oneHundredGbe,
                              ports=[tx.name, rx.name])

    ########################################################################### 
    # Create TX stack configuration
    ########################################################################### 
    tx_ipv4 = Ipv4(name='Tx Ipv4',
                   address=Pattern(tx_port_ip),
                   prefix=Pattern('24'),
                   gateway=Pattern(tx_gateway_ip))

    tx_ethernet = Ethernet(name='Tx Ethernet', ipv4=tx_ipv4)

    tx_device = Device(name='Tx Device',
                       devices_per_port=1,
                       ethernets=[tx_ethernet])

    tx_device_group = DeviceGroup(name='Tx Device Group',
                                  ports=[tx.name],
                                  devices=[tx_device])

    ########################################################################### 
    # Create RX stack configuration
    ########################################################################### 
    rx_ipv4 = Ipv4(name='Rx Ipv4',
                   address=Pattern(rx_port_ip),
                   prefix=Pattern('24'),
                   gateway=Pattern(rx_gateway_ip))

    rx_ethernet = Ethernet(name='Rx Ethernet', ipv4=rx_ipv4)

    rx_device = Device(name='Rx Device',
                       devices_per_port=1,
                       ethernets=[rx_ethernet])

    rx_device_group = DeviceGroup(name='Rx Device Group',
                                  ports=[rx.name],
                                  devices=[rx_device])

    ########################################################################### 
    # Traffic configuration Test data
    # COMMENT --> DSCP values are not getting set
    ########################################################################### 
    data_endpoint = DeviceEndpoint(
        tx_devices=[tx_device.name],
        rx_devices=[rx_device.name],
        packet_encap='ipv4',
        src_dst_mesh='',
        route_host_mesh='',
        bi_directional=False,
        allow_self_destined=False
    )

    test_dscp = Priority(Dscp(phb=PATTERN([0, 1, 2, 5, 6, 7])))

    test_flow = Flow(
        name='Test Data',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(choice=ETHERNET()),
            Header(choice=VLAN()),
            Header(choice=IPV4(priority=test_dscp))
        ],
        size=Size(128),
        rate=Rate('line', 50),
        duration=Duration(Fixed(packets=0))
    )

    ########################################################################### 
    # Traffic configuration Background data
    # COMMENT --> DSCP values are not getting set
    ########################################################################### 
    background_dscp = Priority(Dscp(phb=PATTERN([3, 4])))
    background_flow = Flow(
        name='Background Data',
        endpoint=Endpoint(data_endpoint),
        packet=[
            Header(choice=ETHERNET()),
            Header(choice=VLAN()),
            Header(choice=IPV4(priority=background_dscp))
        ],
        size=Size(128),
        rate=Rate('line', 50),
       duration=Duration(Fixed(packets=0))
    )

    ########################################################################### 
    # Traffic configuration Pause
    # COMMENT --> Throwing an error. 
    # ../ixnetwork_open_traffic_generator/trafficitem.py:92: AttributeError 
    # AttributeError: 'Header' object has no attribute 'name'
    ########################################################################### 
    if (0) :
        pause_endpoint = PortEndpoint(tx_port=rx.name)
        pause = Header(
            choice=PfcPause(
            dst=PATTERN('01:80:C2:00:00:01'),
            src=PATTERN('00:00:fa:ce:fa:ce'),
            class_enable_vector=PATTERN([0, 0, 0, 1, 1, 0, 0, 0]),
            pause_class_3=PATTERN('3'),
            pause_class_4=PATTERN('4'),
        ))

        pause_flow = Flow(
            name='Pause Storm',
            endpoint=Endpoint(pause_endpoint),
            packet=[pause],
            size=Size(64),
            rate=Rate('line', value=100),
            duration=Duration(Fixed(packets=0))
        )
        flows = [test_flow, background_flow, pause]
    else :
       flows = [test_flow, background_flow]

    ########################################################################### 
    # Set config 
    # COMMENT: Forced ownership is required. I found that forced ownership
    #          is not happening.
    #
    # COMMENT: I tried to set only L1 config --> auto_negotiate=False
    # But it seems that there is no way to do that. 
    ########################################################################### 
    config = Config(
        ports=[
            tx,
            rx
        ],
        layer1=[common_l1_config],
        device_groups=[tx_device_group, rx_device_group],
        flows=flows
    )
    print(serializer.json(config))
    api.set_config(config)


def test_start_lossy(serializer) :
    tx_location = TX_LOCATION
    rx_location = RX_LOCATION
    tx_speed = 100000
    vlan_ip_addrs = ['192.168.1.2', '192.168.1.3']
    gw_addr = '192.168.1.1'

    api = IxNetworkApi(API_SERVER, port=PORT)
    api.set_config(None)
    config = run_pfc_pause_lossy_traffic_test(
                serializer=serializer,
                api = api,
                phy_tx_port=tx_location,
                phy_rx_port=rx_location,
                port_speed=tx_speed,
                tx_port_ip=vlan_ip_addrs[1],
                rx_port_ip=vlan_ip_addrs[0],
                tx_gateway_ip=gw_addr,
                rx_gateway_ip=gw_addr,
                tx_ip_incr='0.0.0.0',
                rx_ip_incr='0.0.0.0',
                tx_gateway_incr='0.0.0.0',
                rx_gateway_incr='0.0.0.0')

