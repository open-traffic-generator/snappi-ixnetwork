import pytest

@pytest.mark.skip(
    reason="CI-Testing"
)
def test_loopback_interface(b2b_raw_config, api):
    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="tx_bgp").device(name="rx_bgp")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    bgp1, bgp2 = d1.bgp, d2.bgp

    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"
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

    bgp1_peer.peer_address = "10.1.1.2"
    bgp1_peer.as_type = "ibgp"
    bgp1_peer.as_number = 10

    bgp2_peer.peer_address = "10.1.1.1"
    bgp2_peer.as_type = "ibgp"
    bgp2_peer.as_number = 10

    loop1, loop2 = d1.ipv4_loopbacks.add(), d2.ipv4_loopbacks.add()
    loop1.name, loop2.name = "loop1", "loop2"
    loop1.eth_name, loop2.eth_name = eth1.name, eth2.name
    loop1.address, loop2.address = "20.20.0.1", "20.20.0.2"

    loop3, loop4 = d1.ipv4_loopbacks.add(), d2.ipv4_loopbacks.add()
    loop3.name, loop4.name = "loop3", "loop4"
    loop3.eth_name, loop4.eth_name = eth1.name, eth2.name
    loop3.address, loop4.address = "20.20.0.3", "20.20.0.4"

    loop5, loop6 = d1.ipv6_loopbacks.add(), d2.ipv6_loopbacks.add()
    loop5.name, loop6.name = "loop5", "loop6"
    loop5.eth_name, loop6.eth_name = eth1.name, eth2.name
    loop5.address, loop6.address = "2222::1", "2222::2"

    loop7, loop8 = d1.ipv6_loopbacks.add(), d2.ipv6_loopbacks.add()
    loop7.name, loop8.name = "loop7", "loop8"
    loop7.eth_name, loop8.eth_name = eth1.name, eth2.name
    loop7.address, loop8.address = "2222::3", "2222::4"

    api.set_config(b2b_raw_config)
    validate_result(api)


def validate_result(api):
    validate_v4 = {
        "loop1": {
            "address": ["20.20.0.1", "20.20.0.3"],
        },
        "loop2": {
            "address": ["20.20.0.2", "20.20.0.4"],
        },
    }
    validate_v6 = {
        "loop5": {
            "address": ["2222::1", "2222::3"],
        },
        "loop6": {
            "address": ["2222::2", "2222::4"],
        },
    }
    ixn = api._ixnetwork
    dgs = ixn.Topology.find().DeviceGroup.find().DeviceGroup.find()
    for dg in dgs:
        loop = dg.Ipv4Loopback.find()
        if len(loop) > 0:
            key_values = validate_v4.get(loop.Name)
            assert loop.Address.Values == key_values["address"]

        loop_v6 = dg.Ipv6Loopback.find()
        if len(loop_v6) > 0:
            key_values = validate_v6.get(loop_v6.Name)
            assert loop_v6.Address.Values == key_values["address"]


if __name__ == "__main__":
    pytest.main(["-s", __file__])
