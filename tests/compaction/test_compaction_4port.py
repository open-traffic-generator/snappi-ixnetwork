import pytest


@pytest.mark.skip("4 port configuration is not supported in ci")
def test_compaction_4port(api, b2b_raw_config_4port, utils):
    """
    Test for the bgpv4 metrics
    """
    api._enable_port_compaction(True)
    api.set_config(api.config())
    b2b_raw_config_4port.flows.clear()

    p1, p2, p3, p4 = b2b_raw_config_4port.ports
    d1, d2, d3, d4 = b2b_raw_config_4port.devices.device(name="tx_bgp_1").device(name="rx_bgp_1").device(name="tx_bgp_2").device(name="rx_bgp_2")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth3, eth4 = d3.ethernets.add(), d4.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth3.connection.port_name, eth4.connection.port_name = p3.name, p4.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    eth3.mac, eth4.mac = "00:00:00:00:00:33", "00:00:00:00:00:44"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip3, ip4 = eth3.ipv4_addresses.add(), eth4.ipv4_addresses.add()
    bgp1, bgp2 = d1.bgp, d2.bgp
    bgp3, bgp4 = d3.bgp, d4.bgp

    eth1.name, eth2.name = "eth1", "eth2"
    eth3.name, eth4.name = "eth3", "eth4"
    ip1.name, ip2.name = "ip1", "ip2"
    ip3.name, ip4.name = "ip3", "ip4"

    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"
    bgp3.router_id, bgp4.router_id = "192.1.0.1", "192.1.0.2"
    bgp1_int, bgp2_int = bgp1.ipv4_interfaces.add(), bgp2.ipv4_interfaces.add()
    bgp3_int, bgp4_int = bgp3.ipv4_interfaces.add(), bgp4.ipv4_interfaces.add()
    bgp1_int.ipv4_name, bgp2_int.ipv4_name = ip1.name, ip2.name
    bgp3_int.ipv4_name, bgp4_int.ipv4_name = ip3.name, ip4.name
    bgp1_peer, bgp2_peer = bgp1_int.peers.add(), bgp2_int.peers.add()
    bgp3_peer, bgp4_peer = bgp3_int.peers.add(), bgp4_int.peers.add()
    bgp1_peer.name, bgp2_peer.name = "bgp1", "bpg2"
    bgp3_peer.name, bgp4_peer.name = "bgp3", "bpg4"
    
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

    ip3.address = "10.2.1.1"
    ip3.gateway = "10.2.1.2"
    ip3.prefix = 24

    ip4.address = "10.2.1.2"
    ip4.gateway = "10.2.1.1"
    ip4.prefix = 24

    bgp3_peer.peer_address = "10.2.1.2"
    bgp3_peer.as_type = "ibgp"
    bgp3_peer.as_number = 10

    bgp4_peer.peer_address = "10.2.1.1"
    bgp4_peer.as_type = "ibgp"
    bgp4_peer.as_number = 10

    flow_1 = b2b_raw_config_4port.flows.flow(name="f1")[-1]
    flow_1.tx_rx.device.tx_names = [ip1.name]
    flow_1.tx_rx.device.rx_names = [ip2.name]
    flow_1.packet.ethernet().vlan().tcp()

    flow_2 = b2b_raw_config_4port.flows.flow(name="f2")[-1]
    flow_2.tx_rx.device.tx_names = [ip3.name]
    flow_2.tx_rx.device.rx_names = [ip4.name]
    flow_2.packet.ethernet().vlan().tcp()

    api.set_config(b2b_raw_config_4port)
    # Set the flag back to false else other tests will fail
    api._enable_port_compaction(False)

if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
