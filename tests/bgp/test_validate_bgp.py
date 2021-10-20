
def test_mulliple_ips_on_ethernet(b2b_raw_config, api):
    """Validate Multiple IPv4 or IPv6 configured on top of single Etherent"""
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="tx_bgp").device(name="rx_bgp")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.port_name, eth2.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip3, ip4 =eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    bgp1, bgp2 = d1.bgp, d2.bgp

    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"
    ip3.name, ip4.name = "ip3", "ip4"
    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"
    bgp1_int, bgp2_int = bgp1.ipv4_interfaces.add(), bgp2.ipv4_interfaces.add()
    bgp1_int.ipv4_name, bgp2_int.ipv4_name = ip1.name, ip2.name
    bgp1_peer, bgp2_peer = bgp1_int.peers.add(), bgp2_int.peers.add()
    bgp1_peer.name, bgp2_peer.name = "bgp1", "bpg2"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip1.prefix = 24

    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"
    ip2.prefix = 24

    ip3.address = "20.1.1.1"
    ip3.gateway = "20.1.1.2"
    ip3.prefix = 24

    ip4.address = "20.1.1.2"
    ip4.gateway = "20.1.1.1"
    ip4.prefix = 24

    bgp1_peer.peer_address = "10.1.1.2"
    bgp1_peer.as_type = "ibgp"
    bgp1_peer.as_number = 10

    bgp2_peer.peer_address = "10.1.1.1"
    bgp2_peer.as_type = "ibgp"
    bgp2_peer.as_number = 10
    try:
        api.set_config(b2b_raw_config)
    except Exception as e:
        print(str(e))
        result = "Multiple IP ip1 on top of name Ethernet" in str(e)
        assert result == True


def test_bgp_on_different_dg(b2b_raw_config, api):
    """Validate BGP try to map with different dg"""
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="tx_bgp").device(name="rx_bgp")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.port_name, eth2.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    bgp1, bgp2 = d1.bgp, d2.bgp

    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"
    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"
    bgp1_int = bgp1.ipv4_interfaces.add()
    bgp1_int.ipv4_name = ip2.name
    bgp1_peer = bgp1_int.peers.add()
    bgp1_peer.name = "bgp1"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip1.prefix = 24

    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"
    ip2.prefix = 24

    bgp1_peer.peer_address = "10.1.1.2"
    bgp1_peer.as_type = "ibgp"
    bgp1_peer.as_number = 10

    try:
        api.set_config(b2b_raw_config)
    except Exception as e:
        print(str(e))
        result = "BGP should not configured on top of different device" in str(e)
        assert result == True