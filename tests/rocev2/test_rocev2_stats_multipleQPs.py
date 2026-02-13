import pytest
import time

@pytest.mark.skip(
    reason="""
    "Skipping this test in CI due to setup unavailability"
    """
)

def test_rocev2_stats(api, utils):
    """
    Test for the RoCEv2 configuration
    """
    config = api.config()
    #api.set_config(config)
    p1 = config.ports.add(name="tx", location=utils.settings.ports[0])
    p2 = config.ports.add(name="rx", location=utils.settings.ports[1])

    d1, d2 = config.devices.device(name="rocev2_1").device(name="rocev2_2")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"

    ip1.address = "10.1.1.1"
    ip2.address = "10.1.1.2"

    ip1.prefix = 24
    ip2.prefix = 24

    ip1.gateway = ip2.address
    ip2.gateway = ip1.address

    rocev2_1, rocev2_2 = d1.rocev2, d2.rocev2
    rocev2_1_int, rocev2_2_int = rocev2_1.ipv4_interfaces.add(), rocev2_2.ipv4_interfaces.add()
    rocev2_1_int.ipv4_name, rocev2_2_int.ipv4_name = ip1.name, ip2.name
    rocev2_1_int.ib_mtu, rocev2_2_int.ib_mtu = 1027, 1027
    rocev2_1_peer, rocev2_2_peer = rocev2_1_int.peers.add(), rocev2_2_int.peers.add()
    rocev2_1_peer.name, rocev2_2_peer.name = "RoCEv2 1", "RoCEv2 2"
    rocev2_1_peer.destination_ip_address, rocev2_2_peer.destination_ip_address = [ip2.address], [ip1.address]

    peer1_qp_1 = rocev2_1_peer.qps.add()
    peer1_qp_2 = rocev2_1_peer.qps.add()
    peer2_qp_1 = rocev2_2_peer.qps.add()
    peer2_qp_2 = rocev2_2_peer.qps.add()

    peer1_qp_1.qp_name = "QP_1"
    peer1_qp_2.qp_name = "QP_2"
    peer2_qp_1.qp_name = "QP_3"
    peer2_qp_2.qp_name = "QP_4"
    
    peer1_qp_1.connection_type.choice = "reliable_connection"
    peer1_qp_1.connection_type.reliable_connection.source_qp_number = 33
    peer1_qp_1.connection_type.reliable_connection.dscp = 27
    peer1_qp_1.connection_type.reliable_connection.ecn = "ect_0"

    peer1_qp_2.connection_type.choice = "reliable_connection"
    peer1_qp_2.connection_type.reliable_connection.source_qp_number = 34
    peer1_qp_2.connection_type.reliable_connection.dscp = 41
    peer1_qp_2.connection_type.reliable_connection.ecn = "ect_1"

    peer2_qp_1.connection_type.choice = "reliable_connection"
    peer2_qp_1.connection_type.reliable_connection.source_qp_number = 35
    peer2_qp_1.connection_type.reliable_connection.dscp = 28
    peer2_qp_1.connection_type.reliable_connection.ecn = "ect_0"

    peer2_qp_2.connection_type.choice = "reliable_connection"
    peer2_qp_2.connection_type.reliable_connection.source_qp_number = 36
    peer2_qp_2.connection_type.reliable_connection.dscp = 38
    peer2_qp_2.connection_type.reliable_connection.ecn = "ect_1"

    peer1 = config.stateful_flows.rocev2.add()
    tx_port1 = peer1.tx_ports.add()
    tx_port1.port_name = "tx"
    tx_port1.transmit_type.choice = "target_line_rate"

    #flow_1
    peer1_flow1 = tx_port1.transmit_type.target_line_rate.flows.add()
    peer1_flow1.tx_endpoint = peer1_qp_1.qp_name
    peer1_flow1.name = "QP_1"
    peer1_flow1.rocev2_verb.choice = "send_with_immediate"
    peer1_flow1.rocev2_verb.send_with_immediate.immediate_data = "bb"
    peer1_flow1.message_size_unit = "kb"

    #flow_2
    peer1_flow1 = tx_port1.transmit_type.target_line_rate.flows.add()
    peer1_flow1.tx_endpoint = peer2_qp_1.qp_name
    peer1_flow1.name = "QP_2"
    peer1_flow1.rocev2_verb.choice = "write_with_immediate"
    peer1_flow1.rocev2_verb.write_with_immediate.immediate_data = "aa"
    peer1_flow1.message_size_unit = "mb"

    #flow_3
    peer2_flow1 = tx_port1.transmit_type.target_line_rate.flows.add()
    peer2_flow1.tx_endpoint = peer1_qp_1.qp_name
    peer2_flow1.name = "QP_3"
    peer2_flow1.rocev2_verb.choice = "write_with_immediate"
    peer2_flow1.rocev2_verb.send_with_immediate.immediate_data = "bf"
    peer2_flow1.message_size_unit = "kb"

    #flow_4
    peer2_flow2 = tx_port1.transmit_type.target_line_rate.flows.add()
    peer2_flow2.tx_endpoint = peer2_qp_1.qp_name
    peer2_flow2.name = "QP_4"
    peer2_flow2.rocev2_verb.choice = "write_with_immediate"
    peer2_flow2.rocev2_verb.write_with_immediate.immediate_data = "fa"
    peer2_flow2.message_size_unit = "mb"

    #RoCEv2 Protocol Port Settings
    per_port_option1 = config.options.per_port_options.add()
    per_port_option2 = config.options.per_port_options.add()
    per_port_option1.port_name = "tx"
    per_port_option2.port_name = "rx"
    protocol1 = per_port_option1.protocols.add()
    protocol2 = per_port_option2.protocols.add()
    protocol1.choice = "rocev2"
    protocol2.choice = "rocev2"
    protocol1.rocev2.cnp.choice = "ip_dscp"
    protocol1.rocev2.cnp.ip_dscp.value = 49
    protocol1.rocev2.connection_type.choice = "reliable_connection"
    protocol1.rocev2.connection_type.reliable_connection.enable_retransmission_timeout = False
    protocol1.rocev2.connection_type.reliable_connection.retransmission_timeout_value = 10
    protocol1.rocev2.dcqcn_settings.alpha_g = 1020
    protocol1.rocev2.dcqcn_settings.initial_alpha = 1000
    protocol1.rocev2.dcqcn_settings.maximum_rate_decrement_at_time = 12

    api.set_config(config)

    # start all protocols
    print ("Starting Protocols")
    control_state = api.control_state()
    control_state.protocol.all.state = control_state.protocol.all.START
    api.set_control_state(control_state)

    # create a query for rocev2 metrics
    print ("Fetching and Verifying stats...")
    req = api.metrics_request()
    req.rocev2_ipv4.choice = "per_peer"
    req.rocev2_ipv4.per_peer.peer_names = ["rocev2_1"]
    results = api.get_metrics(req)
    utils.wait_for(
        lambda: results_ok(api), "stats to be as expected", timeout_seconds=20
    )


    print ("Stopping Protocols")
    control_state = api.control_state()
    control_state.protocol.all.state = control_state.protocol.all.STOP
    api.set_control_state(control_state)

def results_ok(api):
    req = api.metrics_request()
    req.rocev2_ipv4.choice = "per_peer"
    req.rocev2_ipv4.per_peer.column_names = ["qp_down"]
    results = api.get_metrics(req)
    time.sleep(10)
    ok = []
    for r in results.rocev2_ipv4_per_peer_metrics:
        ok.append(r.qp_down == 0)
    return all(ok)