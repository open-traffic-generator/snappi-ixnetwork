import ipaddr


def get_macs(mac, count, offset=1):
    """
    Take mac as start mac returns the count of macs in a list
    """
    mac_list = list()
    for i in range(count):
        mac_address = "{:012X}".format(int(mac, 16) + offset * i)
        mac_address = ":".join(
            format(s, "02x") for s in bytearray.fromhex(mac_address)
        )
        mac_list.append(mac_address)
    return mac_list


def get_ip_addresses(ip, count):
    """
    Take ip as start ip returns the count of ips in a list
    """
    ip_list = list()
    for i in range(count):
        ipaddress = ipaddr.IPv4Address(ip)
        ipaddress = ipaddress + i
        value = ipaddress._string_from_ip_int(ipaddress._ip)
        ip_list.append(value)
    return ip_list


def stats_ok(api, packets, utils):
    """
    Returns true if stats are as expected, false otherwise.
    """
    _, flow_stats = utils.get_all_stats(api)

    flow_rx = sum([f.frames_rx for f in flow_stats])
    return flow_rx == packets


def test_compact(api, utils):
    """
    1. Configure 1000 similar devices contain Ether>IPv4>BGPv4
       route in two ports
    2. Create three traffic each traffic with diff set of endpoints
    3. Concrete class should compact the devices to IxNet DeviceGroup.
    4. Validate all through RestPy
    """
    SIZE = 1024
    PACKETS = 1000

    config_values = dict()
    num_of_devices = 1000
    num_of_routes = 1000
    config_values["d1_name"] = "Tx Device 1"
    config_values["d2_name"] = "Rx Device 1"
    config_values["d3_name"] = "Rx Device 3"
    config_values["Multiplier"] = num_of_devices
    rx_device_with_rr = 3

    config = api.config()
    api.enable_scaling(True)

    tx_port, rx_port = config.ports.port(
        name="Tx Port", location=utils.settings.ports[0]
    ).port(name="Rx Port", location=utils.settings.ports[1])

    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.port_names = [rx_port.name, tx_port.name]
    l1.media = utils.settings.media
    l1.speed = utils.settings.speed

    macs = get_macs("000000000011", 2 * num_of_devices)

    config_values["tx_macs"], config_values["rx_macs"] = macs[::2], macs[1::2]
    config_values["vlan_ids"] = [str(i) for i in range(1, num_of_devices + 1)]

    ip_adds = get_ip_addresses("10.10.2.1", 2 * num_of_devices)
    config_values["tx_adds"], config_values["rx_adds"] = (
        ip_adds[::2],
        ip_adds[1::2],
    )

    config_values["tx_rr_add1"] = get_ip_addresses("200.1.0.0", num_of_routes)
    config_values["tx_rr_add2"] = get_ip_addresses("201.1.0.0", num_of_routes)
    next_hop_addr = get_ip_addresses("4.4.4.1", num_of_routes)

    config_values["rx_rr_add1"] = "210.1.0.0"

    for i in range(1, num_of_devices + 1):
        tx_device = config.devices.device()[-1]
        tx_device.name = "Tx Device {0}".format(i)
        tx_device.container_name = tx_port.name
        tx_eth = tx_device.ethernet
        tx_eth.name = "Tx eth {0}".format(i)
        tx_eth.mac = config_values["tx_macs"][i - 1]
        tx_vlan = tx_eth.vlans.vlan()[-1]
        tx_vlan.name = "Tx vlan {0}".format(i)
        tx_vlan.id = int(config_values["vlan_ids"][i - 1])
        tx_ip = tx_eth.ipv4
        tx_ip.name = "Tx IP {0}".format(i)
        tx_ip.address = config_values["tx_adds"][i - 1]
        tx_ip.gateway = config_values["rx_adds"][i - 1]
        tx_ip.prefix = 24

        tx_bgp = tx_ip.bgpv4
        tx_bgp.name = "Tx Bgp {0}".format(i)
        tx_bgp.dut_address = config_values["rx_adds"][i - 1]
        tx_bgp.local_address = config_values["tx_adds"][i - 1]
        tx_bgp.as_number = 65200
        tx_bgp.as_type = "ibgp"

        tx_rr = tx_bgp.bgpv4_routes.bgpv4route(name="Tx RR {0}".format(i))[-1]
        tx_rr.addresses.bgpv4routeaddress(
            count=20, address=config_values["tx_rr_add1"][i - 1], prefix=32
        )
        tx_rr.addresses.bgpv4routeaddress(
            count=10, address=config_values["tx_rr_add2"][i - 1], prefix=24
        )
        tx_rr.next_hop_address = next_hop_addr[i - 1]

    for i in range(1, num_of_devices + 1):
        rx_device = config.devices.device()[-1]
        rx_device.name = "Rx Device {0}".format(i)
        rx_device.container_name = rx_port.name
        rx_eth = rx_device.ethernet
        rx_eth.name = "Rx eth {0}".format(i)
        rx_eth.mac = config_values["rx_macs"][i - 1]
        rx_vlan = rx_eth.vlans.vlan()[-1]
        rx_vlan.name = "Rx vlan {0}".format(i)
        rx_vlan.id = int(config_values["vlan_ids"][i - 1])
        rx_ip = rx_eth.ipv4
        rx_ip.name = "Rx IP {0}".format(i)
        rx_ip.address = config_values["rx_adds"][i - 1]
        rx_ip.gateway = config_values["tx_adds"][i - 1]
        rx_ip.prefix = 24

        rx_bgp = rx_ip.bgpv4
        rx_bgp.name = "Rx Bgp {0}".format(i)
        rx_bgp.dut_address = config_values["tx_adds"][i - 1]
        rx_bgp.local_address = config_values["rx_adds"][i - 1]
        rx_bgp.as_number = 65200
        rx_bgp.as_type = "ibgp"

        if i == rx_device_with_rr:
            rx_rr = rx_bgp.bgpv4_routes.bgpv4route(name="Rx RR {0}".format(i))[
                -1
            ]
            rx_rr.addresses.bgpv4routeaddress(
                count=1000,
                address=config_values["rx_rr_add1"],
                prefix=32,
            )

    config_values["f1_name"] = "f1"
    config_values["f2_name"] = "f2"
    config_values["f3_name"] = "f3"
    flow1, flow2, flow3 = (
        config.flows.flow(name=config_values["f1_name"])
        .flow(name=config_values["f2_name"])
        .flow(name=config_values["f3_name"])
    )

    # Route Range as endpoints
    flow1.tx_rx.device.tx_names = ["Tx RR 2", "Tx RR 4"]
    flow1.tx_rx.device.rx_names = ["Rx RR 3"]
    _, _, tcp = flow1.packet.ethernet().ipv4().tcp()
    tcp.src_port.value = 555
    tcp.dst_port.value = 666

    flow1.size.fixed = SIZE
    flow1.duration.fixed_packets.packets = PACKETS

    flow1.metrics.enable = True
    flow1.metrics.loss = True

    # Ethernet as endpoints
    flow2.tx_rx.device.tx_names = ["Tx eth 2"]
    flow2.tx_rx.device.rx_names = ["Rx eth 2"]

    flow2.size.fixed = SIZE
    flow2.duration.fixed_packets.packets = PACKETS

    flow2.metrics.enable = True
    flow2.metrics.loss = True

    # All Ipv4 as endpoints
    flow3.tx_rx.device.tx_names = [
        "Tx IP {0}".format(i) for i in range(1, num_of_devices + 1)
    ]
    flow3.tx_rx.device.rx_names = [
        "Rx IP {0}".format(i) for i in range(1, num_of_devices + 1)
    ]

    flow3.size.fixed = SIZE
    flow3.duration.fixed_packets.packets = PACKETS

    flow3.metrics.enable = True
    flow3.metrics.loss = True

    api.set_config(config)

    validate_compact_config(api, config_values, rx_device_with_rr)

    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: stats_ok(api, PACKETS * 3, utils), "stats to be as expected"
    )

    rs = api.route_state()
    rs.names = ["Tx RR 4", "Rx RR 3"]
    rs.state = rs.WITHDRAW
    api.set_route_state(rs)

    validate_route_withdraw(api, config_values)


def compare(actual, expected):
    return all([a == b for a, b in zip(actual, expected)])


def validate_compact_config(api, config_values, rx_device_with_rr):
    """
    Validate attributes using RestPy
    """
    ixnetwork = api._ixnetwork

    d1 = ixnetwork.Topology.find().DeviceGroup.find(
        Name=config_values["d1_name"]
    )
    d2 = ixnetwork.Topology.find().DeviceGroup.find(
        Name=config_values["d2_name"]
    )
    d3 = ixnetwork.Topology.find().DeviceGroup.find(
        Name=config_values["d3_name"]
    )

    assert d1.Multiplier == config_values["Multiplier"]
    # assert Macs
    d3_mac = config_values["rx_macs"].pop(rx_device_with_rr - 1)
    assert compare(d1.Ethernet.find().Mac.Values, config_values["tx_macs"])
    assert compare(d2.Ethernet.find().Mac.Values, config_values["rx_macs"])
    assert d3.Ethernet.find().Mac.Values[0] == d3_mac

    assert compare(
        d1.Ethernet.find().Vlan.find().VlanId.Values, config_values["vlan_ids"]
    )

    # Assert values for d1
    assert compare(
        d1.Ethernet.find().Ipv4.find().Address.Values, config_values["tx_adds"]
    )
    assert compare(
        d1.Ethernet.find().Ipv4.find().GatewayIp.Values,
        config_values["rx_adds"],
    )
    assert compare(
        d1.Ethernet.find().Ipv4.find().BgpIpv4Peer.find().DutIp.Values,
        config_values["rx_adds"],
    )

    # Assert values for d2
    d3_ip = config_values["rx_adds"].pop(rx_device_with_rr - 1)
    d3_gateway = config_values["tx_adds"].pop(rx_device_with_rr - 1)
    assert compare(
        d2.Ethernet.find().Ipv4.find().Address.Values, config_values["rx_adds"]
    )
    assert compare(
        d2.Ethernet.find().Ipv4.find().GatewayIp.Values,
        config_values["tx_adds"],
    )
    assert compare(
        d2.Ethernet.find().Ipv4.find().BgpIpv4Peer.find().DutIp.Values,
        config_values["tx_adds"],
    )

    # Assert values for d3
    assert d3.Ethernet.find().Ipv4.find().Address.Values[0] == d3_ip
    assert d3.Ethernet.find().Ipv4.find().GatewayIp.Values[0] == d3_gateway
    assert (
        d3.Ethernet.find().Ipv4.find().BgpIpv4Peer.find().DutIp.Values[0]
        == d3_gateway
    )

    # Assert Network Group
    assert compare(
        d1.NetworkGroup.find()
        .Ipv4PrefixPools.find()
        .NetworkAddress.Values[::2],
        config_values["tx_rr_add1"],
    )
    assert compare(
        d1.NetworkGroup.find()
        .Ipv4PrefixPools.find()
        .NetworkAddress.Values[1::2],
        config_values["tx_rr_add2"],
    )
    assert (
        d3.NetworkGroup.find().Ipv4PrefixPools.find().NetworkAddress.Values[0]
        == config_values["rx_rr_add1"]
    )

    # Assert traffic endpoint for f1
    d1_ixn_pool = d1.NetworkGroup.find().Ipv4PrefixPools.find()
    f1_ixn_traffic = ixnetwork.Traffic.TrafficItem.find(
        Name=config_values["f1_name"]
    )
    assert len(f1_ixn_traffic) == 1
    f1_ixn_endpoint = f1_ixn_traffic.EndpointSet.find()
    assert f1_ixn_endpoint.Sources == []
    f1_cfg_endpoint = [
        {"arg1": d1_ixn_pool.href, "arg2": 1, "arg3": 1, "arg4": 3, "arg5": 2},
        {"arg1": d1_ixn_pool.href, "arg2": 1, "arg3": 1, "arg4": 7, "arg5": 2},
    ]
    assert f1_ixn_endpoint.ScalableSources == f1_cfg_endpoint

    # Assert traffic endpoint for f2
    f2_ixn_traffic = ixnetwork.Traffic.TrafficItem.find(
        Name=config_values["f2_name"]
    )
    f2_ixn_endpoint = f2_ixn_traffic.EndpointSet.find()
    f2_cfg_src_endpoint = [
        {
            "arg1": d1.href + "/ethernet/1",
            "arg2": 1,
            "arg3": 1,
            "arg4": 2,
            "arg5": 1,
        }
    ]

    f2_cfg_dst_endpoint = [
        {
            "arg1": d2.href + "/ethernet/1",
            "arg2": 1,
            "arg3": 1,
            "arg4": 2,
            "arg5": 1,
        }
    ]
    assert f2_ixn_endpoint.ScalableSources == f2_cfg_src_endpoint
    assert f2_ixn_endpoint.ScalableDestinations == f2_cfg_dst_endpoint

    # Assert traffic endpoint for f3
    f3_ixn_traffic = ixnetwork.Traffic.TrafficItem.find(
        Name=config_values["f3_name"]
    )
    f3_ixn_endpoint = f3_ixn_traffic.EndpointSet.find()
    assert f3_ixn_endpoint.Sources[0] == d1.href + "/ethernet/1/ipv4/1"


def validate_route_withdraw(api, config_values):
    ixnetwork = api._ixnetwork
    d1 = ixnetwork.Topology.find().DeviceGroup.find(
        Name=config_values["d1_name"]
    )
    d3 = ixnetwork.Topology.find().DeviceGroup.find(
        Name=config_values["d3_name"]
    )
    d1_ixn_pool = d1.NetworkGroup.find().Ipv4PrefixPools.find()
    d3_ixn_pool = d3.NetworkGroup.find().Ipv4PrefixPools.find()
    assert (d1_ixn_pool.BgpIPRouteProperty.find().Active.Values)[6] == "false"
    assert (d1_ixn_pool.BgpIPRouteProperty.find().Active.Values)[7] == "false"
    assert (d3_ixn_pool.BgpIPRouteProperty.find().Active.Values)[0] == "false"


import pytest
if __name__ == "__main__":
    pytest.main(["-s", __file__])