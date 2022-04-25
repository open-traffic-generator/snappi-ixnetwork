import pytest


def test_bgp_evpn_validation(api, b2b_raw_config_vports):
    # Creating Ports
    p1, p2 = b2b_raw_config_vports.ports

    # Create BGP running on connected interface.
    p1_d1 = b2b_raw_config_vports.devices.device(name='p1_d1')[-1]
    p1_bgp_d = b2b_raw_config_vports.devices.device(name='p1_bgp_d')[-1]
    p2_d1 = b2b_raw_config_vports.devices.device(name='p2_d1')[-1]

    p1_eth1 = p1_d1.ethernets.ethernet(port_name=p1.name)[-1]
    p2_eth1 = p2_d1.ethernets.ethernet(port_name=p2.name)[-1]

    p1_eth1.name = 'p1_eth1'
    p1_eth1.mac = '00:11:00:00:00:01'
    p1_ip1 = p1_eth1.ipv4_addresses.ipv4(name='p1_ip1', address='20.20.20.2', gateway='20.20.20.1')[-1]

    p2_eth1.name = 'p2_eth1'
    p2_eth1.mac = '00:12:00:00:00:01'
    p2_ip1 = p2_eth1.ipv4_addresses.ipv4(name='p2_ip1', address='30.30.30.2', gateway='30.30.30.1')[-1]

    # lopback in port1 dg p1_bgp_d
    p1_loop = p1_bgp_d.ipv4_loopbacks.add(name="p1_loopback", eth_name="p1_eth1")

    # bgp Port 1
    p1_bgp = p1_bgp_d.bgp
    p1_bgp.router_id = "192.0.0.1"
    p1_bgp_iface = p1_bgp.ipv4_interfaces.v4interface(ipv4_name=p1_loop.name)[-1]
    p1_bgp_peer = p1_bgp_iface.peers.v4peer(name="bgp1", peer_address='20.20.20.1', as_type='ibgp', as_number=100)[-1]

    # Adding 1 Ethernet Segment per Bgp Peer
    p1_es_1 = p1_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]
    p1_es_1.esi = '00000000000000000002'
    p1_es_1.esi_label = 8
    p1_es_1.active_mode = p1_es_1.SINGLE_ACTIVE
    p1_es_1.advanced.origin = p1_es_1.advanced.EGP

    p1_es_1_com = p1_es_1.communities.add()
    p1_es_1_com.type = p1_es_1_com.MANUAL_AS_NUMBER
    p1_es_1_com.as_number = 8
    p1_es_1_com.as_custom = 8
    p1_es_1_com1 = p1_es_1.communities.add()
    p1_es_1_com1.type = p1_es_1_com1.NO_EXPORT
    p1_es_1_com1.as_number = 7
    p1_es_1_com1.as_custom = 7

    p1_es_1.as_path.segments.add("as_confed_seq", [2, 3])
    p1_es_1.as_path.segments.add("as_seq", [8])

    # Adding 1 EVI on the Ethernet Segment
    p1_es1_evisV4_1 = p1_es_1.evis.evi_vxlan()[-1]
    # test = p1_es_1.evis.evpn_mpls()[-1] #For evpn_mpls object [to be incoorporated in future]

    p1_es1_evisV4_1.route_distinguisher.rd_type = p1_es1_evisV4_1.route_distinguisher.AS_2OCTET
    p1_es1_evisV4_1.route_distinguisher.rd_value = "1000:1"

    p1_es1_evisV4_1.advanced.origin = p1_es1_evisV4_1.advanced.EGP
    p1_es1_evisV4_1_com = p1_es1_evisV4_1.communities.add()
    p1_es1_evisV4_1_com.type = p1_es1_evisV4_1_com.MANUAL_AS_NUMBER
    p1_es1_evisV4_1_com.as_number = 3
    p1_es1_evisV4_1_com.as_custom = 3
    p1_es1_evisV4_1.as_path.segments.add("as_seq", [9, 10])

    export_rt = p1_es1_evisV4_1.route_target_export.routetarget()[-1]
    import_rt = p1_es1_evisV4_1.route_target_import.routetarget()[-1]
    export_rt.rt_type = export_rt.AS_2OCTET
    export_rt.rt_value = "100:20"

    import_rt.rt_type = import_rt.AS_2OCTET
    import_rt.rt_value = "100:20"

    # Adding 1 Broadcast Domain per EVI
    p1_es1_evisV4_1_bd_1 = p1_es1_evisV4_1.broadcast_domains.broadcastdomain()[-1]
    p1_es1_evisV4_1_bd_1.ethernet_tag_id = 5
    p1_es1_evisV4_1_bd_1.vlan_aware_service = True

    # Adding 1 MAC Range Per Broadcast Domain
    p1_es1_evisV4_1_bd_1_mac_Pool1 = p1_es1_evisV4_1_bd_1.cmac_ip_range.cmaciprange(l2vni=16)[-1]
    p1_es1_evisV4_1_bd_1_mac_Pool1.mac_addresses.address = "10:11:22:33:44:55"

    ##################################################################
    # bgp Port 2
    p2_bgp = p2_d1.bgp
    p2_bgp.router_id = "193.0.0.1"
    p2_bgp_iface = p2_bgp.ipv4_interfaces.v4interface(ipv4_name=p2_ip1.name)[-1]
    p2_bgp_peer = p2_bgp_iface.peers.v4peer(name="bgp2", peer_address='30.20.20.1', as_type='ibgp', as_number=100)[-1]

    # Adding 1 Ethernet Segment per Bgp Peer
    p2_es_1 = p2_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]

    # For adding multiple ethernet segments we can add the objects in a loop
    # for i in range(0, 9):
    #    p2_es = p2_bgp_peer.evpn_ethernet_segments.ethernetsegment()

    # Adding 1 EVI on the Ethernet Segment
    p2_es1_evisV4_1 = p2_es_1.evis.evi_vxlan()[-1]

    # Adding RD and RT on EVI
    p2_es1_evisV4_1.route_distinguisher.rd_type = p2_es1_evisV4_1.route_distinguisher.AS_2OCTET
    p2_es1_evisV4_1.route_distinguisher.rd_value = "3000:1"

    export_rt = p2_es1_evisV4_1.route_target_export.routetarget()[-1]
    import_rt = p2_es1_evisV4_1.route_target_import.routetarget()[-1]
    export_rt.rt_type = export_rt.AS_2OCTET
    export_rt.rt_value = "300:20"

    import_rt.rt_type = import_rt.AS_2OCTET
    import_rt.rt_value = "300:20"

    # Adding 1 Broadcast Domain per EVI
    p2_es1_evisV4_1_bd_1 = p2_es1_evisV4_1.broadcast_domains.broadcastdomain()[-1]

    # Adding 1 CMAC Range Per Broadcast Domain
    p2_es1_evisV4_1_bd_1_mac_Pool1 = p2_es1_evisV4_1_bd_1.cmac_ip_range.cmaciprange(l2vni=16)[-1]
    p2_es1_evisV4_1_bd_1_mac_Pool1.mac_addresses.address = "20:11:22:33:44:55"
    p2_es1_evisV4_1_bd_1_mac_Pool1.ipv4_addresses.address = "2.2.2.2"

    print(b2b_raw_config_vports.serialize())
    api.set_config(b2b_raw_config_vports)


if __name__ == "__main__":
    pytest.main(["-s", __file__])