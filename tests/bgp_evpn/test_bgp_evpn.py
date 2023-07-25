def test_bgp_evpn(api, utils):
    # Creating Ports
    config = api.config()
    p1 = config.ports.port(name='p1', location=utils.settings.ports[0])[-1]
    p2 = config.ports.port(name='p2', location=utils.settings.ports[1])[-1]

    # Create BGP devices on tx & rx
    tx_d = config.devices.device(name='tx_d')[-1]
    rx_d = config.devices.device(name='rx_d')[-1]

    tx_eth = tx_d.ethernets.ethernet(port_name=p1.name)[-1]
    rx_eth = rx_d.ethernets.ethernet(port_name=p2.name)[-1]

    tx_eth.name = 'tx_eth'
    tx_eth.mac = '00:11:00:00:00:01'
    tx_ip = tx_eth.ipv4_addresses.ipv4(name='tx_ip',
                                       address='20.20.20.2',
                                       gateway='20.20.20.1')[-1]

    rx_eth.name = 'rx_eth'
    rx_eth.mac = '00:12:00:00:00:01'
    rx_ip = rx_eth.ipv4_addresses.ipv4(name='rx_ip',
                                       address='20.20.20.1',
                                       gateway='20.20.20.2')[-1]

    # tx_bgp
    tx_bgp = tx_d.bgp
    tx_bgp.router_id = "192.0.0.1"
    tx_bgp_iface = (tx_bgp.ipv4_interfaces
                    .v4interface(ipv4_name=tx_ip.name)[-1])
    tx_bgp_peer = tx_bgp_iface.peers.v4peer(name="tx_eBGP",
                                            peer_address='20.20.20.1',
                                            as_type='ebgp',
                                            as_number=100)[-1]

    # rx_bgp
    rx_bgp = rx_d.bgp
    rx_bgp.router_id = "193.0.0.1"
    rx_bgp_iface = (rx_bgp.ipv4_interfaces
                    .v4interface(ipv4_name=rx_ip.name)[-1])
    rx_bgp_peer = rx_bgp_iface.peers.v4peer(name="rx_eBGP",
                                            peer_address='20.20.20.2',
                                            as_type='ebgp',
                                            as_number=200)[-1]

    # Create & advertise loopback under bgp in tx and rx
    tx_l1 = tx_d.ipv4_loopbacks.add()
    tx_l1.name = "tx_loopback1"
    tx_l1.eth_name = "tx_eth"
    tx_l1.address = "1.1.1.1"

    tx_l1_r = tx_bgp_peer.v4_routes.add(name="tx_l1")
    tx_l1_r.addresses.add(address="1.1.1.1", prefix=32)

    rx_l1 = rx_d.ipv4_loopbacks.add()
    rx_l1.name = "rx_loopback1"
    rx_l1.eth_name = "rx_eth"
    rx_l1.address = "2.2.2.2"

    rx_l1_r = rx_bgp_peer.v4_routes.add(name="rx_l1")
    rx_l1_r.addresses.add(address="2.2.2.2", prefix=32)

    # Create BGP EVPN on tx
    tx_vtep = config.devices.device(name='tx_vtep')[-1]
    tx_vtep_bgp = tx_vtep.bgp
    tx_vtep_bgp.router_id = "190.0.0.1"
    tx_vtep_bgp_iface = (tx_vtep_bgp.ipv4_interfaces
                         .v4interface(ipv4_name=tx_l1.name)[-1])
    tx_vtep_bgp_peer = tx_vtep_bgp_iface.peers.v4peer(name="bgp1",
                                                      peer_address='2.2.2.2',
                                                      as_type='ibgp',
                                                      as_number=101)[-1]

    # Adding 1 Ethernet Segment per Bgp Peer
    tx_vtep_es1 = tx_vtep_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]

    # Adding 1 EVI on the Ethernet Segment
    tx_es1_evisV4_1 = tx_vtep_es1.evis.evi_vxlan()[-1]
    tx_es1_evisV4_1.route_distinguisher.auto_config_rd_ip_addr = True
    tx_es1_evisV4_1.route_distinguisher.rd_type = (
        tx_es1_evisV4_1.route_distinguisher.AS_2OCTET)
    tx_es1_evisV4_1.route_distinguisher.rd_value = "100:1"

    export_rt = tx_es1_evisV4_1.route_target_export.routetarget()[-1]
    import_rt = tx_es1_evisV4_1.route_target_import.routetarget()[-1]
    export_rt.rt_type = export_rt.AS_2OCTET
    export_rt.rt_value = "100:20"

    import_rt.rt_type = import_rt.AS_2OCTET
    import_rt.rt_value = "100:20"

    # Adding 1 Broadcast Domain per EVI
    tx_es1_evisV4_1_bd_1 = (tx_es1_evisV4_1
                            .broadcast_domains
                            .broadcastdomain()[-1])

    # Adding 1 MAC Range Per Broadcast Domain
    tx_es1_evisV4_1_bd_1_mac_Pool1 = (tx_es1_evisV4_1_bd_1
                                      .cmac_ip_range
                                      .cmaciprange(l2vni=20)[-1])

    tx_es1_evisV4_1_bd_1_mac_Pool1.name = "tx_mac_pool"
    tx_es1_evisV4_1_bd_1_mac_Pool1.mac_addresses.address = "10:11:22:33:44:55"

    # Adding 1 IP Range Per Broadcast Domain
    tx_es1_evisV4_1_bd_1_mac_Pool1.ipv4_addresses.address = "192.168.0.1"

    # Create BGP EVPN on rx
    rx_vtep = config.devices.device(name='rx_vtep')[-1]
    rx_vtep_bgp = rx_vtep.bgp
    rx_vtep_bgp.router_id = "191.0.0.1"
    rx_vtep_bgp_iface = (rx_vtep_bgp.ipv4_interfaces
                         .v4interface(ipv4_name=rx_l1.name)[-1])
    rx_vtep_bgp_peer = rx_vtep_bgp_iface.peers.v4peer(name="bgp2",
                                                      peer_address='1.1.1.1',
                                                      as_type='ibgp',
                                                      as_number=101)[-1]

    # Adding 1 Ethernet Segment per Bgp Peer
    rx_vtep_es1 = rx_vtep_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]

    # Adding 1 EVI on the Ethernet Segment
    rx_es1_evisV4_1 = rx_vtep_es1.evis.evi_vxlan()[-1]

    rx_es1_evisV4_1.route_distinguisher.rd_type = (
        rx_es1_evisV4_1.route_distinguisher.AS_2OCTET)
    rx_es1_evisV4_1.route_distinguisher.rd_value = "1000:1"

    export_rt = rx_es1_evisV4_1.route_target_export.routetarget()[-1]
    import_rt = rx_es1_evisV4_1.route_target_import.routetarget()[-1]
    export_rt.rt_type = export_rt.AS_2OCTET
    export_rt.rt_value = "100:20"

    import_rt.rt_type = import_rt.AS_2OCTET
    import_rt.rt_value = "100:20"

    # Adding 1 Broadcast Domain per EVI
    rx_es1_evisV4_1_bd_1 = (rx_es1_evisV4_1
                            .broadcast_domains
                            .broadcastdomain()[-1])

    # Adding 1 MAC Range Per Broadcast Domain
    rx_es1_evisV4_1_bd_1_mac_Pool1 = (rx_es1_evisV4_1_bd_1
                                      .cmac_ip_range
                                      .cmaciprange(l2vni=20)[-1])
    rx_es1_evisV4_1_bd_1_mac_Pool1.name = "rx_mac_pool"
    rx_es1_evisV4_1_bd_1_mac_Pool1.mac_addresses.address = "10:11:22:33:44:77"

    # Adding 1 IP Range Per Broadcast Domain
    rx_es1_evisV4_1_bd_1_mac_Pool1.ipv4_addresses.address = "192.168.1.2"

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [tx_es1_evisV4_1_bd_1_mac_Pool1.name]
    f1.tx_rx.device.rx_names = [rx_es1_evisV4_1_bd_1_mac_Pool1.name]

    f1.duration.fixed_packets.packets = 1000

    f1.size.fixed = 1500
    f1.metrics.enable = True
    f1.metrics.loss = True

    utils.start_traffic(api, config)

    utils.wait_for(
        lambda: results_ok(api, ["f1"], 1000),
        "stats to be as expected",
        timeout_seconds=10,
    )
    utils.stop_traffic(api, config)


def results_ok(api, flow_names, expected):
    """
    Returns True if there is no traffic loss else False
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    flow_rx = sum([f.frames_rx for f in flow_results])
    return flow_rx == expected
