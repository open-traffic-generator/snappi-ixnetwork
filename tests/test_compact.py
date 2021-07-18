def test_compact(api, utils):
    """
    1. Configure 4 similar devices contain Ether>IPv4>BGPv4>BGP route in two ports
    2. Create one traffic with two device endpoint from two different ports
    3. Enable compact logic.
    4. Concrete class should compact 4 device to single IxNet DeviceGroup.
    5. Validate all values through RestPy
    """
    config_values = {
        "device": [
            {
                "name": "Tx Device 1",
                "multiplier": 4,
                "ether": {
                    "name": "Tx eth 1",
                    "mac": [
                        "00:11:01:00:00:01",
                        "00:11:01:00:00:02",
                        "00:11:01:00:00:03",
                        "00:11:01:00:00:04",
                    ],
                    "ip": {
                        "name": "Tx IP 1",
                        "address": [
                            "10.1.1.1",
                            "10.1.2.1",
                            "10.1.3.1",
                            "10.1.4.1",
                        ],
                        "gateway": [
                            "10.1.1.2",
                            "10.1.2.2",
                            "10.1.3.2",
                            "10.1.4.2",
                        ],
                        "prefix": ["24", "24", "24", "24"],
                        "bgp": {
                            "name": "Tx Bgp 1",
                            "dut_address": [
                                "10.1.1.2",
                                "10.1.2.2",
                                "10.1.3.2",
                                "10.1.4.2",
                            ],
                            "route": {
                                "name": "Tx RR 1",
                                "multiplier": 2,
                                "address": [
                                    "200.1.0.0",
                                    "201.1.0.0",
                                    "200.2.0.0",
                                    "201.2.0.0",
                                    "200.3.0.0",
                                    "201.3.0.0",
                                    "200.4.0.0",
                                    "201.4.0.0",
                                ],
                                "count": [
                                    "20",
                                    "10",
                                    "20",
                                    "10",
                                    "20",
                                    "10",
                                    "20",
                                    "10",
                                ],
                            },
                        },
                    },
                },
            },
            {},
        ]
    }

    config = api.config()
    tx_port, rx_port = config.ports.port(name="Tx Port", location=None).port(
        name="Rx Port", location=None
    )

    dev_count = 1
    max_dev_count = 4
    while dev_count <= max_dev_count:
        tx_device = config.devices.device()[-1]
        tx_device.name = "Tx Device {0}".format(dev_count)
        tx_device.container_name = tx_port.name
        tx_eth = tx_device.ethernet
        tx_eth.name = "Tx eth {0}".format(dev_count)
        tx_eth.mac = "00:11:01:00:00:0{0}".format(dev_count)
        tx_ip = tx_eth.ipv4
        tx_ip.name = "Tx IP {0}".format(dev_count)
        tx_ip.address = "10.1.{0}.1".format(dev_count)
        tx_ip.gateway = "10.1.{0}.2".format(dev_count)
        tx_ip.prefix = 24

        tx_bgp = tx_ip.bgpv4
        tx_bgp.name = "Tx Bgp {0}".format(dev_count)
        tx_bgp.dut_address = "10.1.{0}.2".format(dev_count)
        tx_bgp.local_address = "10.1.{0}.1".format(dev_count)
        tx_bgp.as_number = 65200
        tx_bgp.as_type = "ebgp"

        rx_rr = tx_bgp.bgpv4_routes.bgpv4route(
            name="Tx RR {0}".format(dev_count)
        )[-1]
        rx_rr.addresses.bgpv4routeaddress(
            count=20, address="200.{0}.0.0".format(dev_count), prefix=32
        )
        rx_rr.addresses.bgpv4routeaddress(
            count=10, address="201.{0}.0.0".format(dev_count), prefix=24
        )
        rx_rr.next_hop_address = "4.4.4.{0}".format(dev_count)
        dev_count += 1

    dev_count = 1
    while dev_count <= max_dev_count:
        tx_device = config.devices.device()[-1]
        tx_device.name = "Rx Device {0}".format(dev_count)
        tx_device.container_name = rx_port.name
        tx_eth = tx_device.ethernet
        tx_eth.name = "Rx eth {0}".format(dev_count)
        tx_eth.mac = "00:12:01:00:00:0{0}".format(dev_count)
        tx_ip = tx_eth.ipv4
        tx_ip.name = "Rx IP {0}".format(dev_count)
        tx_ip.address = "10.1.{0}.2".format(dev_count)
        tx_ip.gateway = "10.1.{0}.1".format(dev_count)
        tx_ip.prefix = 24

        tx_bgp = tx_ip.bgpv4
        tx_bgp.name = "Rx Bgp {0}".format(dev_count)
        tx_bgp.dut_address = "10.1.{0}.1".format(dev_count)
        tx_bgp.local_address = "10.1.{0}.2".format(dev_count)
        tx_bgp.as_number = 65200
        tx_bgp.as_type = "ebgp"

        rx_rr = tx_bgp.bgpv4_routes.bgpv4route(
            name="Rx RR {0}".format(dev_count)
        )[-1]
        rx_rr.addresses.bgpv4routeaddress(
            count=1000, address="200.{0}.0.0".format(dev_count), prefix=32
        )
        dev_count += 1

    flow_name = "Device Flow"
    flow = config.flows.flow(name=flow_name)[0]
    flow.tx_rx.device.tx_names = ["Tx RR 2", "Tx RR 4"]
    flow.tx_rx.device.rx_names = ["Rx RR 2", "Rx RR 4"]
    eth, ip, tcp = flow.packet.ethernet().ipv4().tcp()
    tcp.src_port.value = 555
    tcp.dst_port.value = 666
    flow.size.fixed = 128
    flow.duration.burst.packets = 4

    api.set_config(config)
    validate_compact_config(api, config_values, flow_name)
    #
    # route_state = api.route_state()
    # route_state.state = route_state.WITHDRAW
    # route_state.names = ["tx1_rr_1", "tx1_rr_2"]
    # api.set_route_state(route_state)


def validate_compact_config(api, config_values, flow_name):
    """
    Validate Compact attribute using RestPy
    """

    ixnetwork = api._ixnetwork
    cfg_dg = config_values["device"][0]
    ixn_dg = (
        ixnetwork.Topology.find()
        .DeviceGroup.find(Name = cfg_dg["name"])
    )
    assert len(ixn_dg) == 1
    assert ixn_dg.Multiplier == cfg_dg["multiplier"]
    
    cfg_ether = cfg_dg["ether"]
    ixn_ether = ixn_dg.Ethernet.find(Name=cfg_ether["name"])
    assert len(ixn_ether) == 1
    assert ixn_ether.Mac.Values == cfg_ether["mac"]
    
    cfg_ip = cfg_ether["ip"]
    ixn_ip = ixn_ether.Ipv4.find(Name=cfg_ip["name"])
    assert len(ixn_ip) == 1
    assert ixn_ip.Address.Values == cfg_ip["address"]
    assert ixn_ip.GatewayIp.Values == cfg_ip["gateway"]
    assert ixn_ip.Prefix.Values == cfg_ip["prefix"]

    cfg_bgp = cfg_ip["bgp"]
    ixn_bgp = ixn_ip.BgpIpv4Peer.find(Name=cfg_bgp["name"])
    assert len(ixn_bgp) == 1
    assert ixn_bgp.DutIp.Values == cfg_bgp["dut_address"]

    cfg_route = cfg_bgp["route"]
    ixn_ng = ixn_dg.NetworkGroup.find(Name=cfg_route["name"])
    assert len(ixn_ng) == 1
    assert ixn_ng.Multiplier == cfg_route["multiplier"]
    ixn_pool = ixn_ng.Ipv4PrefixPools.find()
    assert ixn_pool.NetworkAddress.Values == cfg_route["address"]
    assert ixn_pool.NumberOfAddressesAsy.Values == cfg_route["count"]

    ixn_traffic = ixnetwork.Traffic.TrafficItem.find(Name=flow_name)
    assert len(ixn_traffic) == 1
    ixn_endpoint = ixn_traffic.EndpointSet.find()
    assert ixn_endpoint.Sources == []
    cfg_endpoint = [
        {
            'arg1': ixn_pool.href,
            'arg2': 1,
            'arg3': 1,
            'arg4': 3,
            'arg5': 2
        },
        {
            'arg1': ixn_pool.href,
            'arg2': 1,
            'arg3': 1,
            'arg4': 7,
            'arg5': 2
        }
    ]
    assert ixn_endpoint.ScalableSources == cfg_endpoint
    
    