from abstract_open_traffic_generator.port import Port, OneHundredGbe, Layer1
from abstract_open_traffic_generator.device import DeviceGroup, Device
from abstract_open_traffic_generator.device import Ethernet, Vlan, Ipv4
from abstract_open_traffic_generator.device import Pattern
from abstract_open_traffic_generator.config import Config
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
    # TX port + L1
    tx = Port(name='Tx', location=phy_tx_port, link_state='up')

    tx_l1_oneHundredGbe = OneHundredGbe(link_training=True,
                                 ieee_media_defaults=False,
                                 auto_negotiate=False,
                                 speed='100g',
                                 rs_fec=False)

    tx_l1_config = Layer1(name='Tx l1',
                          choice=tx_l1_oneHundredGbe,
                          ports=[tx])

    # RX port + L1
    rx = Port(name='Rx', location=phy_tx_port, link_state='up')

    rx_l1_oneHundredGbe = OneHundredGbe(link_training=True,
                                 ieee_media_defaults=False,
                                 auto_negotiate=False,
                                 speed='100g',
                                 rs_fec=False)

    rx_l1_config = Layer1(name='Rx l1',
                          choice=rx_l1_oneHundredGbe,
                          ports=[rx])

    # Create TX stack configuration
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

    # Create RX stack configuration
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

    # Create the entire configuration Tx/Rx stack + flow
    config = Config(
        ports=[
            tx,
            rx
        ],
        layer1=[tx_l1_config, rx_l1_config],
        device_groups=[tx_device_group, rx_device_group]
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

