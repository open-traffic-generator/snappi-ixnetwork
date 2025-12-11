import pytest


# @pytest.mark.skip("4 port configuration is not supported in ci")
def test_compaction_4port(api, b2b_raw_config_4port, utils):
    """
    Test for the bgpv4 metrics
    """
    api._enable_port_compaction(True)
    packets = 10000
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
    bgp1_peer.as_number = packets

    bgp2_peer.peer_address = "10.1.1.1"
    bgp2_peer.as_type = "ibgp"
    bgp2_peer.as_number = packets

    ip3.address = "10.2.1.1"
    ip3.gateway = "10.2.1.2"
    ip3.prefix = 24

    ip4.address = "10.2.1.2"
    ip4.gateway = "10.2.1.1"
    ip4.prefix = 24

    bgp3_peer.peer_address = "10.2.1.2"
    bgp3_peer.as_type = "ibgp"
    bgp3_peer.as_number = packets

    bgp4_peer.peer_address = "10.2.1.1"
    bgp4_peer.as_type = "ibgp"
    bgp4_peer.as_number = packets

    flow_1 = b2b_raw_config_4port.flows.flow(name="flow_1")[-1]
    flow_1.tx_rx.device.tx_names = [ip1.name]
    flow_1.tx_rx.device.rx_names = [ip2.name]
    flow_1.size.fixed = 128
    flow_1.rate.pps = 1000
    flow_1.duration.fixed_packets.packets = packets
    flow_1.metrics.enable = True
    flow_1.packet.ethernet().ipv4()

    flow_2 = b2b_raw_config_4port.flows.flow(name="flow_2")[-1]
    flow_2.tx_rx.device.tx_names = [ip3.name]
    flow_2.tx_rx.device.rx_names = [ip4.name]
    flow_2.size.fixed = 128
    flow_2.rate.pps = 1000
    flow_2.duration.fixed_packets.packets = packets
    flow_2.metrics.enable = True
    flow_2.packet.ethernet().ipv4()

    api.set_config(b2b_raw_config_4port)

    utils.start_traffic(api, b2b_raw_config_4port)

    utils.wait_for(
        lambda: results_ok(api),
        "states to be as expected",
        timeout_seconds=30,
    )

    utils.stop_traffic(api, b2b_raw_config_4port)

    captures_ok(api, b2b_raw_config_4port, utils)

    assert (api._ixnetwork.Topology.find()[0]
            .DeviceGroup.find()
            .Multiplier) == 1
    
    assert (api._ixnetwork.Topology.find()[0]
            .DeviceGroup.find()
            .Count) == 4

    # Set the flag back to false else other tests will fail
    api._enable_port_compaction(False)

def results_ok(api):
    """
    Returns True if there is no traffic loss else False
    """
    req = api.metrics_request()
    req.bgpv4.column_names = ["session_state"]
    results = api.get_metrics(req)
    ok = []
    for r in results.bgpv4_metrics:
        ok.append(r.session_state == "up")
    return all(ok)

def captures_ok(api, cfg, utils):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src_mac = [0x00, 0x00, 0x00, 0x00, 0x00, 0x11]
    dst_mac = [0x00, 0x00, 0x00, 0x00, 0x00, 0x22]

    src_ip = [0x0A, 0x01, 0x01, 0x01]
    dst_ip = [0x0A, 0x01, 0x01, 0x02]

    src_port = [0x00, 0xB3]
    dst_port = [0x80, 0x11]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1
    for b in cap_dict[list(cap_dict.keys())[0]]:
        assert (b[0:6] == dst_mac and b[6:12] == src_mac) or (b[0:6] == src_mac and b[6:12] == dst_mac)
        assert (b[26:30] == src_ip and b[30:34] == dst_ip) or (b[26:30] == dst_ip and b[30:34] == src_ip)
        if len(b) == 256:
            assert (b[34:36] == src_port and b[36:38] == dst_port) or (b[34:36] == dst_port and b[36:38] == src_port)

if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
