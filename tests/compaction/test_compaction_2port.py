import pytest


# @pytest.mark.skip("4 port configuration is not supported in ci")
def test_compaction_2port(api, b2b_raw_config, utils):
    """
    Test for the bgpv4 metrics
    """
    api._enable_port_compaction(True)
    packets = 10000
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

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
    bgp1_peer.as_number = packets

    bgp2_peer.peer_address = "10.1.1.1"
    bgp2_peer.as_type = "ibgp"
    bgp2_peer.as_number = packets

    flow = b2b_raw_config.flows.flow(name="flow")[-1]
    flow.tx_rx.device.tx_names = [ip1.name]
    flow.tx_rx.device.rx_names = [ip2.name]
    flow.size.fixed = 128
    flow.rate.pps = 1000
    flow.duration.fixed_packets.packets = packets
    flow.metrics.enable = True
    flow.packet.ethernet().ipv4()
    
    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config)

    utils.wait_for(
        lambda: results_ok(api, ["flow"], packets),
        "stats to be as expected",
        timeout_seconds=60,
    )

    utils.stop_traffic(api, b2b_raw_config)

    captures_ok(api, b2b_raw_config, utils)

    assert (api._ixnetwork.Topology.find()[0]
            .DeviceGroup.find()
            .Multiplier) == 1
    
    assert (api._ixnetwork.Topology.find()[0]
            .DeviceGroup.find()
            .Count) == 2
    
    # Set the flag back to false else other tests will fail
    api._enable_port_compaction(False)

def results_ok(api, flow_names, expected):
    """
    Returns True if there is no traffic loss else False
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    flow_rx = sum([f.frames_rx for f in flow_results])
    return flow_rx == expected

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
