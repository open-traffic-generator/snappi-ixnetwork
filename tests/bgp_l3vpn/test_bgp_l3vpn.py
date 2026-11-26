"""
BGP/MPLS L3VPN (RFC 4364) smoke test - one VRF per peer, IS-IS underlay.

Matches the depth/style of tests/bgp_evpn/test_bgp_evpn.py: config, bring
sessions up, send traffic, assert loss-free. Deeper verification (BGP UPDATE
wire parsing for RD/RT/label, route withdrawal, RT-mismatch isolation) lives
in the private ai-snappi-ixnetwork/tests/bgp/bgp_l3vpn/test_bgp_l3vpn_b2b.py suite, not
here - see ai-snappi-ixnetwork/docs/design_snappi_ixnetwork_bgp_l3vpn.md
Section 5.2 for the public/private split rationale.

Topology (back-to-back, 2 ports, no DUT)
-----------------------------------------
  Port p1                                Port p2
  Device tx_d                            Device rx_d
    tx_eth (00:11:00:00:00:01)             rx_eth (00:12:00:00:00:01)
    tx_ip 192.168.1.1/30  <--IS-IS L2 adj-->  rx_ip 192.168.1.2/30
    tx_loopback1 1.1.1.1                   rx_loopback1 2.2.2.2
    tx_bgp_peer (iBGP AS 65000, over loopback, next hop resolved via IS-IS)
                          <--MP-BGP VPNv4-->
                                          rx_bgp_peer (iBGP AS 65000, over loopback)
    VRF "VPN_A"                             VRF "VPN_A"
      RD 65000:100                            RD 65000:200
      RT export/import 65000:999               RT export/import 65000:999
      v4_routes: 10.1.1.0/24 label 1000        v4_routes: 10.2.1.0/24 label 2000

Both devices are emulated directly on the two ixia-c ports (B2B, no DUT) -
tx_d and rx_d each play a PE role. IS-IS is underlay-only here (no
LDP/RSVP-TE - out of scope per PRD FR-U1); the flow "f1" runs
tx_customer_route -> rx_customer_route to prove end-to-end forwarding across
the VPN, but does not itself verify RD/RT/label content - see the private
suite for that.
"""


def test_bgp_l3vpn(api, utils):
    # Creating Ports
    config = api.config()
    p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    p2 = config.ports.port(name="p2", location=utils.settings.ports[1])[-1]

    # Create devices on tx & rx
    tx_d = config.devices.device(name="tx_d")[-1]
    rx_d = config.devices.device(name="rx_d")[-1]

    tx_eth = tx_d.ethernets.add()
    tx_eth.connection.port_name = p1.name
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:11:00:00:00:01"
    tx_ip = tx_eth.ipv4_addresses.ipv4(
        name="tx_ip", address="192.168.1.1", gateway="192.168.1.2", prefix=30
    )[-1]

    rx_eth = rx_d.ethernets.add()
    rx_eth.connection.port_name = p2.name
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:12:00:00:00:01"
    rx_ip = rx_eth.ipv4_addresses.ipv4(
        name="rx_ip", address="192.168.1.2", gateway="192.168.1.1", prefix=30
    )[-1]

    # IS-IS underlay only (no LDP/RSVP-TE - out of scope, see PRD FR-U1)
    tx_isis = tx_d.isis
    tx_isis.system_id = "640100010001"
    tx_isis.name = "tx_isis"
    tx_isis_iface = tx_isis.interfaces.interface(eth_name=tx_eth.name)[-1]
    tx_isis_iface.name = "tx_isis_iface"
    tx_isis_iface.network_type = tx_isis_iface.POINT_TO_POINT
    tx_isis_iface.level_type = tx_isis_iface.LEVEL_2

    rx_isis = rx_d.isis
    rx_isis.system_id = "640100010002"
    rx_isis.name = "rx_isis"
    rx_isis_iface = rx_isis.interfaces.interface(eth_name=rx_eth.name)[-1]
    rx_isis_iface.name = "rx_isis_iface"
    rx_isis_iface.network_type = rx_isis_iface.POINT_TO_POINT
    rx_isis_iface.level_type = rx_isis_iface.LEVEL_2

    # BGP peers over loopbacks, next hop resolved via IS-IS
    tx_l1 = tx_d.ipv4_loopbacks.add()
    tx_l1.name, tx_l1.eth_name, tx_l1.address = "tx_loopback1", "tx_eth", "1.1.1.1"

    rx_l1 = rx_d.ipv4_loopbacks.add()
    rx_l1.name, rx_l1.eth_name, rx_l1.address = "rx_loopback1", "rx_eth", "2.2.2.2"

    tx_bgp = tx_d.bgp
    tx_bgp.router_id = "1.1.1.1"
    tx_bgp_iface = tx_bgp.ipv4_interfaces.v4interface(ipv4_name=tx_l1.name)[-1]
    tx_bgp_peer = tx_bgp_iface.peers.v4peer(
        name="tx_bgp_peer",
        peer_address="2.2.2.2",
        as_type="ibgp",
        as_number=65000,
    )[-1]
    tx_bgp_peer.capability.ipv4_mpls_vpn = True

    rx_bgp = rx_d.bgp
    rx_bgp.router_id = "2.2.2.2"
    rx_bgp_iface = rx_bgp.ipv4_interfaces.v4interface(ipv4_name=rx_l1.name)[-1]
    rx_bgp_peer = rx_bgp_iface.peers.v4peer(
        name="rx_bgp_peer",
        peer_address="1.1.1.1",
        as_type="ibgp",
        as_number=65000,
    )[-1]
    rx_bgp_peer.capability.ipv4_mpls_vpn = True

    # One VRF per peer - RD, RT export/import, one customer route with a
    # VPN label each. Multiple VRFs per peer are out of scope here (see
    # Open Question 1 in the design doc).
    # vrf name must be globally unique across the config - snappi rejects
    # two BgpL3vpnVrf objects sharing a name, even on different peers.
    tx_vrf = tx_bgp_peer.l3vpn_vrfs.add(name="tx_vpn_a")
    tx_export_rt = tx_vrf.route_target_export.add()
    tx_export_rt.rt_type = tx_export_rt.AS_2OCTET
    tx_export_rt.rt_value = "65000:999"
    tx_import_rt = tx_vrf.route_target_import.add()
    tx_import_rt.rt_type = tx_import_rt.AS_2OCTET
    tx_import_rt.rt_value = "65000:999"
    tx_route = tx_vrf.v4_routes.add(name="tx_customer_route")
    tx_route.route_distinguisher.rd_type = (
        tx_route.route_distinguisher.AS_2OCTET
    )
    tx_route.route_distinguisher.rd_value = "65000:100"
    tx_route.addresses.add(address="10.1.1.0", prefix=24)
    tx_route.mpls_labels.start = 1000
    tx_route.mpls_labels.max = 1000
    tx_route.mpls_labels.step = 1
    rx_vrf = rx_bgp_peer.l3vpn_vrfs.add(name="rx_vpn_a")
    rx_export_rt = rx_vrf.route_target_export.add()
    rx_export_rt.rt_type = rx_export_rt.AS_2OCTET
    rx_export_rt.rt_value = "65000:999"
    rx_import_rt = rx_vrf.route_target_import.add()
    rx_import_rt.rt_type = rx_import_rt.AS_2OCTET
    rx_import_rt.rt_value = "65000:999"
    rx_route = rx_vrf.v4_routes.add(name="rx_customer_route")
    rx_route.route_distinguisher.rd_type = (
        rx_route.route_distinguisher.AS_2OCTET
    )
    rx_route.route_distinguisher.rd_value = "65000:200"
    rx_route.addresses.add(address="10.2.1.0", prefix=24)
    rx_route.mpls_labels.start = 2000
    rx_route.mpls_labels.max = 2000
    rx_route.mpls_labels.step = 1

    # The flow is deliberately not added to `config` yet: IxNetwork rejects
    # a config push that includes a BGP L3VPN device flow before BGP
    # itself has been started ("Please Start BGP on selected Tx ports
    # before trying to generate BGP L3VPN traffic" - confirmed live). Push
    # protocols-only first, start BGP, wait for it to come up, then add the
    # flow and push again.
    #
    # Known open issue, confirmed live: that second api.set_config() call
    # is not an incremental update in this codebase - it unconditionally
    # tears down and rebuilds the whole topology every call, so it
    # re-triggers the same "not started yet" validation the wait was meant
    # to clear. api.append_config()/ConfigAppend is the real incremental
    # path that avoids this, but is deliberately not used here - do not
    # switch to it without being asked (see the
    # feedback_no_append_config_in_tests memory).
    api.set_config(config)
    utils.start_protocols(api)
    utils.wait_for(
        lambda: bgpv4_sessions_up(api),
        "BGPv4 sessions to come up",
        timeout_seconds=30,
    )

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [tx_route.name]
    f1.tx_rx.device.rx_names = [rx_route.name]

    f1.duration.fixed_packets.packets = 1000
    f1.size.fixed = 512
    f1.metrics.enable = True
    f1.metrics.loss = True

    api.set_config(config)
    utils.start_traffic_only(api)

    utils.wait_for(
        lambda: results_ok(api, ["f1"], 1000),
        "stats to be as expected",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, config)


def bgpv4_sessions_up(api, expected_count=2):
    """Check BGP session state directly via RestPy rather than
    api.get_metrics(): confirmed live that get_metrics()'s per-device-group
    stats gathering returns zero bgpv4_metrics for peers attached to a
    loopback (both peers in this test), even while the peers themselves
    report SessionStatus=up when read directly - the same nested/child
    device-group limitation bgp.py's own get_bgp_peer_objects docstring
    already documents for GetStates apparently applies to get_metrics()'s
    stats path too.
    """
    ixn = api._ixnetwork
    count = 0
    for topo in ixn.Topology.find():
        for dg in topo.DeviceGroup.find():
            for eth in dg.Ethernet.find():
                for ip4 in eth.Ipv4.find():
                    for peer in ip4.BgpIpv4Peer.find():
                        count += 1
                        if not all(s == "up" for s in peer.SessionStatus):
                            return False
            for cdg in dg.DeviceGroup.find():
                for lo in cdg.Ipv4Loopback.find():
                    for peer in lo.BgpIpv4Peer.find():
                        count += 1
                        if not all(s == "up" for s in peer.SessionStatus):
                            return False
    return count == expected_count


def results_ok(api, flow_names, expected):
    """
    Returns True if there is no traffic loss else False
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    flow_rx = sum([f.frames_rx for f in flow_results])
    return flow_rx == expected
