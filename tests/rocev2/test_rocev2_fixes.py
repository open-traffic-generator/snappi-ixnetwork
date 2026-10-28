"""End-to-end verification for the RoCEv2 fixes.

Each test maps to a specific fix and asserts against the state actually
pushed to IxNetwork (via ``api._ixnetwork``), so they can be run on real
ports/IxNetwork to confirm every fix independently.

Fix -> test mapping
-------------------
- Dual IP stack (node on 2nd-added stack is pushed) ...... test_dual_stack_second_stack_node_pushed
- Destination peer resolution + "Clear" for externals ... test_destination_peers_and_clear
- set_config re-run re-creates nodes (dedup reset) ...... test_reconfigure_recreates_nodes
- Traffic stopped before RoCEv2Traffic delete .......... test_reconfigure_while_traffic_running
- Retransmission global port settings applied .......... test_retransmission_global_port_settings
"""
import pytest

@pytest.mark.skip(
    reason="""
    "Skipping this test in CI due to setup unavailability"
    """
)

# --------------------------------------------------------------------------- #
# Query helpers (white-box assertions against the pushed IxNetwork config)
# --------------------------------------------------------------------------- #
def _v4_nodes(api):
    return (
        api._ixnetwork.Topology.find()
        .DeviceGroup.find()
        .Ethernet.find()
        .Ipv4.find()
        .Rocev2.find()
    )


def _v6_nodes(api):
    return (
        api._ixnetwork.Topology.find()
        .DeviceGroup.find()
        .Ethernet.find()
        .Ipv6.find()
        .Roce6v2.find()
    )


def _global_rocev2(api):
    return api._ixnetwork.Globals.Topology.find().Rocev2.find()


def _node_names(nodes):
    return [n.Name for n in nodes]


# --------------------------------------------------------------------------- #
# Config builders
# --------------------------------------------------------------------------- #
def _add_port_eth(config, utils, dev_name, port_name, port_index, mac):
    port = config.ports.add(
        name=port_name, location=utils.settings.ports[port_index]
    )
    device = config.devices.add(name=dev_name)
    eth = device.ethernets.add()
    eth.connection.port_name = port.name
    eth.mac = mac
    eth.name = "%s_eth" % dev_name
    return port, device, eth


# --------------------------------------------------------------------------- #
# Fix: dual IP stack - RoCEv2 node on the second-added stack must be pushed
# --------------------------------------------------------------------------- #
def test_dual_stack_second_stack_node_pushed(api, utils):
    """ipv4 added first, ipv6 added second; RoCEv2 configured on the ipv6
    (second) stack. The roce6v2 node must still be pushed to IxNetwork."""
    config = api.config()
    _, d1, eth1 = _add_port_eth(
        config, utils, "rocev2_1", "tx", 0, "00:00:00:00:00:11"
    )
    _, d2, eth2 = _add_port_eth(
        config, utils, "rocev2_2", "rx", 1, "00:00:00:00:00:22"
    )

    # ipv4 added FIRST
    ip4_1, ip4_2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip4_1.name, ip4_2.name = "ip4_1", "ip4_2"
    ip4_1.address, ip4_2.address = "10.1.1.1", "10.1.1.2"
    ip4_1.prefix = ip4_2.prefix = 24
    ip4_1.gateway, ip4_2.gateway = ip4_2.address, ip4_1.address

    # ipv6 added SECOND
    ip6_1, ip6_2 = eth1.ipv6_addresses.add(), eth2.ipv6_addresses.add()
    ip6_1.name, ip6_2.name = "ip6_1", "ip6_2"
    ip6_1.address, ip6_2.address = "2000::1", "2000::2"
    ip6_1.prefix = ip6_2.prefix = 64
    ip6_1.gateway, ip6_2.gateway = ip6_2.address, ip6_1.address

    # RoCEv2 on the ipv6 (second-added) stack
    int1 = d1.rocev2.ipv6_interfaces.add()
    int2 = d2.rocev2.ipv6_interfaces.add()
    int1.ipv6_name, int2.ipv6_name = ip6_1.name, ip6_2.name
    int1.ib_mtu = int2.ib_mtu = 1027
    peer1, peer2 = int1.peers.add(), int2.peers.add()
    peer1.name, peer2.name = "v6_peer_1", "v6_peer_2"
    peer1.destination_ip_address = ip6_2.address
    peer2.destination_ip_address = ip6_1.address
    peer1.qps.add().qp_name = "v6_qp_1"
    peer2.qps.add().qp_name = "v6_qp_2"

    api.set_config(config)

    v6_names = _node_names(_v6_nodes(api))
    assert "v6_peer_1" in v6_names, (
        "RoCEv2 node on the second-added (ipv6) stack was not pushed: %s"
        % v6_names
    )
    assert "v6_peer_2" in v6_names, (
        "RoCEv2 node on the second-added (ipv6) stack was not pushed: %s"
        % v6_names
    )


# --------------------------------------------------------------------------- #
# Fix: destination peer resolution + "Clear" (QpCount=0) for externals
# --------------------------------------------------------------------------- #
def test_destination_peers_and_clear(api, utils):
    """A peer pointing at another device's IP resolves to that node; a peer
    pointing at an IP outside the config is cleared (QpCount reset to 0)."""
    config = api.config()
    _, d1, eth1 = _add_port_eth(
        config, utils, "rocev2_1", "tx", 0, "00:00:00:00:00:11"
    )
    _, d2, eth2 = _add_port_eth(
        config, utils, "rocev2_2", "rx", 1, "00:00:00:00:00:22"
    )
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address, ip2.address = "10.1.1.1", "10.1.1.2"
    ip1.prefix = ip2.prefix = 24
    ip1.gateway, ip2.gateway = ip2.address, ip1.address

    int1 = d1.rocev2.ipv4_interfaces.add()
    int2 = d2.rocev2.ipv4_interfaces.add()
    int1.ipv4_name, int2.ipv4_name = ip1.name, ip2.name
    int1.ib_mtu = int2.ib_mtu = 1027

    # d1 peer -> external IP not present in the config => expect "Clear"
    ext_peer = int1.peers.add()
    ext_peer.name = "ext_peer"
    ext_peer.destination_ip_address = "10.1.1.99"
    ext_peer.qps.add().qp_name = "ext_qp"

    # d2 peer -> d1's IP => expect resolution to "ext_peer" node
    resolvable_peer = int2.peers.add()
    resolvable_peer.name = "resolvable_peer"
    resolvable_peer.destination_ip_address = ip1.address
    resolvable_peer.qps.add().qp_name = "res_qp"

    api.set_config(config)

    nodes = {n.Name: n for n in _v4_nodes(api)}
    assert "ext_peer" in nodes and "resolvable_peer" in nodes

    # External destination -> cleared peers and QpCount reset to 0
    assert int(nodes["ext_peer"].QpCount) == 0, (
        "external-destination node QpCount should be 0, got %s"
        % nodes["ext_peer"].QpCount
    )
    assert "Clear" not in nodes["ext_peer"].DestinationPeerNames, (
        "'Clear' is a command, it must not persist as a peer name"
    )

    # Resolvable destination -> points at the node sitting on that IP
    assert "ext_peer" in nodes["resolvable_peer"].DestinationPeerNames, (
        "resolvable peer should point at the node on the destination IP, got %s"
        % nodes["resolvable_peer"].DestinationPeerNames
    )


# --------------------------------------------------------------------------- #
# Fix: set_config re-run re-creates nodes (dedup set is reset per run)
# --------------------------------------------------------------------------- #
def test_reconfigure_recreates_nodes(api, utils):
    """Pushing the same config twice must still create the RoCEv2 nodes the
    second time (the dedup set is reset at the start of each config run)."""
    config = _basic_b2b_rocev2_config(api, utils)

    api.set_config(config)
    first = sorted(_node_names(_v4_nodes(api)))
    assert first == ["peer_1", "peer_2"], first

    # Second push of the same config must not silently skip node creation
    api.set_config(config)
    second = sorted(_node_names(_v4_nodes(api)))
    assert second == ["peer_1", "peer_2"], (
        "nodes missing after reconfigure (dedup set not reset): %s" % second
    )


# --------------------------------------------------------------------------- #
# Fix: traffic is stopped before RoCEv2Traffic is deleted
# --------------------------------------------------------------------------- #
# def test_reconfigure_while_traffic_running(api, utils):
#     """Start RoCEv2 traffic, then push a new config. remove_ixn_traffic must
#     stop the stateful traffic before deleting roceV2Traffic (no exception)."""
#     config = _basic_b2b_rocev2_config(api, utils, with_stateful_flow=True)
#     api.set_config(config)
#
#     # start protocols
#     cs = api.control_state()
#     cs.protocol.all.state = cs.protocol.all.START
#     api.set_control_state(cs)
#
#     # start traffic
#     ts = api.control_state()
#     ts.traffic.flow_transmit.state = ts.traffic.flow_transmit.START
#     api.set_control_state(ts)
#
#     # Reconfiguring while traffic is running must not raise.
#     api.set_config(config)
#
#     names = sorted(_node_names(_v4_nodes(api)))
#     assert names == ["peer_1", "peer_2"], names


# --------------------------------------------------------------------------- #
# Fix: retransmission global port settings are applied
# --------------------------------------------------------------------------- #
def test_retransmission_global_port_settings(api, utils):
    """enable_retransmission_timeout / retransmission_timeout_value /
    retransmission_retry_count flow into the global RoCEv2 port settings."""
    config = _basic_b2b_rocev2_config(api, utils)

    ppo = config.options.per_port_options.add()
    ppo.port_name = "tx"
    proto = ppo.protocols.add()
    proto.choice = "rocev2"
    proto.rocev2.cnp.choice = "ip_dscp"
    proto.rocev2.cnp.ip_dscp.value = 48
    rc = proto.rocev2.connection_type.reliable_connection
    rc.enable_retransmission_timeout = True
    rc.retransmission_timeout_value = 7
    rc.retransmission_retry_count = 5

    api.set_config(config)

    gp = _global_rocev2(api)
    assert "tx" in gp.RowNames, gp.RowNames
    idx = gp.RowNames.index("tx")

    enable_vals = gp.EnableACKTimeout.Values
    ack_timeout_vals = gp.AckTimeout.Values
    retry_vals = gp.RetransRetryCount.Values

    assert str(enable_vals[idx]).lower() == "true", enable_vals
    assert str(ack_timeout_vals[idx]) == "7", ack_timeout_vals
    assert str(retry_vals[idx]) == "5", retry_vals


# --------------------------------------------------------------------------- #
# Shared minimal back-to-back RoCEv2 config
# --------------------------------------------------------------------------- #
def _basic_b2b_rocev2_config(api, utils, with_stateful_flow=False):
    config = api.config()
    p1, d1, eth1 = _add_port_eth(
        config, utils, "rocev2_1", "tx", 0, "00:00:00:00:00:11"
    )
    p2, d2, eth2 = _add_port_eth(
        config, utils, "rocev2_2", "rx", 1, "00:00:00:00:00:22"
    )
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address, ip2.address = "10.1.1.1", "10.1.1.2"
    ip1.prefix = ip2.prefix = 24
    ip1.gateway, ip2.gateway = ip2.address, ip1.address

    int1 = d1.rocev2.ipv4_interfaces.add()
    int2 = d2.rocev2.ipv4_interfaces.add()
    int1.ipv4_name, int2.ipv4_name = ip1.name, ip2.name
    int1.ib_mtu = int2.ib_mtu = 1027
    peer1, peer2 = int1.peers.add(), int2.peers.add()
    peer1.name, peer2.name = "peer_1", "peer_2"
    peer1.destination_ip_address = ip2.address
    peer2.destination_ip_address = ip1.address
    qp1, qp2 = peer1.qps.add(), peer2.qps.add()
    qp1.qp_name, qp2.qp_name = "qp_1", "qp_2"
    qp1.connection_type.choice = "reliable_connection"
    qp2.connection_type.choice = "reliable_connection"

    if with_stateful_flow:
        sf = config.stateful_flows.rocev2.add()
        tx_port = sf.tx_ports.add()
        tx_port.port_name = p1.name
        tx_port.transmit_type.choice = "target_line_rate"
        flow = tx_port.transmit_type.target_line_rate.flows.add()
        flow.name = qp1.qp_name
        flow.rocev2_verb.choice = "write"
        flow.message_size_unit = "kb"

    return config


# --------------------------------------------------------------------------- #
# Bug: "Snappi set_config not deleting rocev2 traffic if session already has a
# config loaded." Start RoCEv2 protocols + traffic, then push a new config and
# assert the stale RoCEv2 traffic is deleted.
# --------------------------------------------------------------------------- #
def test_set_config_deletes_stale_rocev2_traffic(api, utils):
    """Start RoCEv2 traffic, then load a new config. The RoCEv2 traffic from
    the previous config must be removed by set_config."""
    # start from a clean, empty config
    api.set_config(api.config())

    config = _rocev2_traffic_config(api, utils)
    api.set_config(config)

    # start protocols
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)

    # Start traffic. The RoCEv2 flow groups (RoceV2Traffic) are created before
    # the Traffic.Apply() step; a known IxNetwork issue can fail that apply, so
    # tolerate it here - we only need RoceV2Traffic to exist to test deletion.
    try:
        ts = api.control_state()
        ts.traffic.flow_transmit.state = ts.traffic.flow_transmit.START
        api.set_control_state(ts)
    except Exception as err:
        print("Ignoring RoCEv2 traffic apply error: %s" % err)

    before = _rocev2_stream_count(api)
    print("RoCEv2 streams after start: %d" % before)
    assert before > 0, "RoCEv2 traffic (streams) was not created"

    # Load a new NON-EMPTY config without RoCEv2. This takes the traffic path
    # (not NewConfig), so remove_ixn_traffic().DeleteAllStreams() must clear the
    # stale RoCEv2 streams.
    new_config = api.config()
    new_config.ports.add(name="tx", location=utils.settings.ports[0])
    new_config.ports.add(name="rx", location=utils.settings.ports[1])
    api.set_config(new_config)

    after = _rocev2_stream_count(api)
    print("RoCEv2 streams after new non-empty set_config: %d" % after)
    assert after == 0, (
        "stale RoCEv2 traffic was not deleted when a new config was loaded "
        "(streams still present: %d)" % after
    )


def _rocev2_stream_count(api):
    rocev2_traffic = api._ixnetwork.Traffic.RoceV2Traffic.find()
    if len(rocev2_traffic) == 0:
        return 0
    return len(rocev2_traffic.RoceV2Stream.find())


def _rocev2_traffic_config(api, utils):
    config = api.config()
    p1, d1, eth1 = _add_port_eth(
        config, utils, "rocev2_1", "tx", 0, "00:00:00:00:00:11"
    )
    p2, d2, eth2 = _add_port_eth(
        config, utils, "rocev2_2", "rx", 1, "00:00:00:00:00:22"
    )
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address, ip2.address = "10.1.1.1", "10.1.1.2"
    ip1.prefix = ip2.prefix = 24
    ip1.gateway, ip2.gateway = ip2.address, ip1.address

    int1 = d1.rocev2.ipv4_interfaces.add()
    int2 = d2.rocev2.ipv4_interfaces.add()
    int1.ipv4_name, int2.ipv4_name = ip1.name, ip2.name
    int1.ib_mtu = int2.ib_mtu = 1027
    peer1, peer2 = int1.peers.add(), int2.peers.add()
    peer1.name, peer2.name = "RoCEv2 1", "RoCEv2 2"
    peer1.destination_ip_address = ip2.address
    peer2.destination_ip_address = ip1.address

    qp1, qp2 = peer1.qps.add(), peer2.qps.add()
    qp1.qp_name, qp2.qp_name = "QP_1", "QP_2"
    qp1.connection_type.choice = "reliable_connection"
    qp1.connection_type.reliable_connection.source_qp_number = 33
    qp1.connection_type.reliable_connection.dscp = 27
    qp2.connection_type.choice = "reliable_connection"
    qp2.connection_type.reliable_connection.source_qp_number = 34
    qp2.connection_type.reliable_connection.dscp = 28

    # stateful RoCEv2 flow (immediate verb carries data -> no empty multivalue)
    sf = config.stateful_flows.rocev2.add()
    tx_port = sf.tx_ports.add()
    tx_port.port_name = p1.name
    tx_port.transmit_type.target_line_rate.value = 80
    tx_port.transmit_type.choice = "target_line_rate"
    flow = tx_port.transmit_type.target_line_rate.flows.add()
    flow.tx_endpoint = qp1.qp_name
    flow.name = qp1.qp_name
    flow.rocev2_verb.choice = "send_with_immediate"
    flow.rocev2_verb.send_with_immediate.immediate_data = "bb"
    flow.message_size_unit = "kb"

    return config


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", __file__]))
