import pytest


def test_manual_gateway_mac(api, utils):
    count = 128
    config = api.config()

    edge1_macs = get_macs("001801000011", count)
    edge2_macs = get_macs("001601000011", count)

    p1, p2 = config.ports.port(
        name="p1", location=utils.settings.ports[0]
    ).port(name="p2", location=utils.settings.ports[1])

    d1, d2 = config.devices.device(name="d1").device(name="d2")

    e1, e2 = d1.ethernets.add(), d2.ethernets.add()
    e1.connection.port_name, e2.connection.port_name = p1.name, p2.name
    e1.name, e2.name = "e1", "e2"
    e1.mac, e2.mac = "00:01:00:00:00:01", "00:01:00:00:00:02"

    ip1, ip2 = e1.ipv4_addresses.add(), e2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip_d1", "ip_d2"

    ip1.address, ip2.address = "10.10.10.1", "10.10.10.2"
    ip1.gateway, ip2.gateway = "10.10.10.2", "10.10.10.1"

    ip1.gateway_mac.value = "aa:aa:aa:aa:aa:aa"

    bgp1, bgp2 = d1.bgp, d2.bgp
    bgp1.router_id, bgp2.router_id = "10.10.10.1", "10.10.10.2"
    bgp1_ipv4 = bgp1.ipv4_interfaces.add()
    bgp2_ipv4 = bgp2.ipv4_interfaces.add()

    bgp1_ipv4.ipv4_name, bgp2_ipv4.ipv4_name = ip1.name, ip2.name
    bgp1_peer, bgp2_peer = bgp1_ipv4.peers.add(), bgp2_ipv4.peers.add()
    bgp1_peer.name, bgp2_peer.name = "bgp_router1", "bgp_router2"

    bgp1_peer.peer_address, bgp2_peer.peer_address = "10.10.10.2", "10.10.10.1"
    bgp1_peer.as_type, bgp2_peer.as_type = "ebgp", "ebgp"
    bgp1_peer.as_number, bgp2_peer.as_number = 100, 200

    # Create & advertise loopbacks under bgp in d1 & d2
    for i in range(1, count + 1):
        d1_l1 = d1.ipv4_loopbacks.add()
        d1_l1.name = "d1_loopback{}".format(i)
        d1_l1.eth_name = "e1"
        d1_l1.address = "1.1.1.{}".format(i)

        bgp1_l1 = bgp1_peer.v4_routes.add(name="bgp_l{}".format(i))
        bgp1_l1.addresses.add(address="1.1.1.{}".format(i), prefix=32)

    for i in range(1, count + 1):
        d2_l1 = d2.ipv4_loopbacks.add()
        d2_l1.name = "d2_loopback{}".format(i)
        d2_l1.eth_name = "e2"
        d2_l1.address = "2.2.2.{}".format(i)

        bgp2_l1 = bgp2_peer.v4_routes.add(name="bgp2_l{}".format(i))
        bgp2_l1.addresses.add(address="2.2.2.{}".format(i), prefix=32)

    # Create vxlan tunnels on d1
    for i in range(1, count + 1):
        d1_vxlan = d1.vxlan.v4_tunnels.add()

        d1_vxlan.vni = 1000 + i
        d1_vxlan.source_interface = "d1_loopback{}".format(i)
        d1_vxlan.name = "d1_vxlan{}".format(i)

        # unicast communication, Add two unicast info
        vtep = d1_vxlan.destination_ip_mode.unicast.vteps.add()
        vtep.remote_vtep_address = "2.2.2.{}".format(i)
        vtep.arp_suppression_cache.add(edge2_macs[i], "100.1.2.{}".format(i))
        vtep.arp_suppression_cache.add("00:1b:6e:00:00:01", "1.2.0.1")

    # Create vxlan on d2
    for i in range(1, count + 1):
        d2_vxlan = d2.vxlan.v4_tunnels.add()

        d2_vxlan.vni = 1000 + i
        d2_vxlan.source_interface = "d2_loopback{}".format(i)
        d2_vxlan.name = "d2_vxlan{}".format(i)

        # unicast communication
        vtep = d2_vxlan.destination_ip_mode.unicast.vteps.add()
        vtep.remote_vtep_address = "1.1.1.{}".format(i)
        vtep.arp_suppression_cache.add(edge1_macs[i], "100.1.1.{}".format(i))
        vtep.arp_suppression_cache.add("00:1b:6e:00:00:01", "1.2.0.1")

    for i in range(1, count + 1):
        edge1_d = config.devices.device(name="edge1_d{}".format(i))[-1]
        edge2_d = config.devices.device(name="edge2_d{}".format(i))[-1]

        edge1_e = edge1_d.ethernets.ethernet()[-1]
        edge2_e = edge2_d.ethernets.ethernet()[-1]

        edge1_e.connection.vxlan_name = "d1_vxlan{}".format(i)
        edge2_e.connection.vxlan_name = "d2_vxlan{}".format(i)

        edge1_e.name = "edge1_e{}".format(i)
        edge2_e.name = "edge2_e{}".format(i)

        edge1_e.mac = edge1_macs[i]
        edge2_e.mac = edge2_macs[i]

        edge1_ip = edge1_e.ipv4_addresses.add()
        edge2_ip = edge2_e.ipv4_addresses.add()

        edge1_ip.name = "edge1_ip_d{}".format(i)
        edge2_ip.name = "edge2_ip_d{}".format(i)

        edge1_ip.address = "100.1.{}.1".format(i)
        edge2_ip.address = "100.1.{}.2".format(i)

        edge1_ip.gateway = "100.1.{}.2".format(i)
        edge2_ip.gateway = "100.1.{}.1".format(i)

        edge1_ip.gateway_mac.value = edge2_macs[i]

        edge1_bgp, edge2_bgp = edge1_d.bgp, edge2_d.bgp
        edge1_bgp.router_id = "100.1.{}.1".format(i)
        edge2_bgp.router_id = "100.1.{}.2".format(i)

        edge1_bgp_ipv4 = edge1_bgp.ipv4_interfaces.add()
        edge2_bgp_ipv4 = edge2_bgp.ipv4_interfaces.add()

        edge1_bgp_ipv4.ipv4_name = "edge1_ip_d{}".format(i)
        edge2_bgp_ipv4.ipv4_name = "edge2_ip_d{}".format(i)

        edge1_bgp_peer = edge1_bgp_ipv4.peers.add()
        edge2_bgp_peer = edge2_bgp_ipv4.peers.add()

        edge1_bgp_peer.name = "edge1_bgp{}".format(i)
        edge2_bgp_peer.name = "edge2_bgp{}".format(i)

        edge1_bgp_peer.peer_address = "100.1.{}.2".format(i)
        edge2_bgp_peer.peer_address = "100.1.{}.1".format(i)

        edge1_bgp_peer.as_type, edge2_bgp_peer.as_type = "ibgp", "ibgp"
        edge1_bgp_peer.as_number, edge2_bgp_peer.as_number = 1000, 1000

        edge1_bgp_rr = edge1_bgp_peer.v4_routes.add(name="A1{}".format(i))
        edge1_bgp_rr.addresses.add(
            address="1.1.0.{}".format(i), count=180, prefix=32
        )

        edge1_bgp_rr2 = edge1_bgp_peer.v4_routes.add(name="D1{}".format(i))
        edge1_bgp_rr2.addresses.add(
            address="2.1.0.{}".format(i), count=1, prefix=32
        )

        edge2_bgp_rr = edge2_bgp_peer.v4_routes.add(name="A2{}".format(i))
        edge2_bgp_rr.addresses.add(
            address="3.1.0.{}".format(i), count=180, prefix=32
        )

        edge2_bgp_rr2 = edge2_bgp_peer.v4_routes.add(name="D2{}".format(i))
        edge2_bgp_rr2.addresses.add(
            address="4.1.0.{}".format(i), count=1, prefix=32
        )

    api.set_config(config)

    assert (
        api._ixnetwork.Topology.find()[0]
        .DeviceGroup.find()
        .DeviceGroup.find()
        .Multiplier
    ) == 128

    assert (
        api._ixnetwork.Topology.find()[0]
        .DeviceGroup.find()
        .DeviceGroup.find()
        .DeviceGroup.find()
        .Count
    ) == 128

    assert (
        api._ixnetwork.Topology.find()[0]
        .DeviceGroup.find()[0]
        .Ethernet.find()[0]
        .Ipv4.find()
        .ManualGatewayMac.Values[0]
    ) == "aa:aa:aa:aa:aa:aa"

    assert (
        api._ixnetwork.Topology.find()[0]
        .DeviceGroup.find()
        .DeviceGroup.find()
        .DeviceGroup.find()
        .Ethernet.find()[0]
        .Ipv4.find()
        .ManualGatewayMac.Values
    ) == edge2_macs[1:]


def get_macs(mac, count, offset=1):
    """
    Take mac as start mac returns the count of macs in a list
    """
    mac_list = list()
    for i in range(count + 1):
        mac_address = "{:012X}".format(int(mac, 16) + offset * i)
        mac_address = ":".join(
            format(s, "02x") for s in bytearray.fromhex(mac_address)
        )
        mac_list.append(mac_address)
    return mac_list


if __name__ == "__main__":
    pytest.main(["-s", __file__])
