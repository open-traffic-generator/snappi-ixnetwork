import pytest


def test_bgp_evpn_validation(api, utils):
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
    rx_ip = rx_eth.ipv4_addresses.ipv4(name='p2_ip1',
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

    tx_eth_seg = tx_vtep_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]
    tx_eth_seg.esi = '00000000000000000002'
    tx_eth_seg.esi_label = 8
    tx_eth_seg.active_mode = tx_eth_seg.SINGLE_ACTIVE
    tx_eth_seg.advanced.origin = tx_eth_seg.advanced.EGP
    tx_eth_seg.advanced.multi_exit_discriminator = 5
    tx_eth_seg_community = tx_eth_seg.communities.add()
    tx_eth_seg_community.type = tx_eth_seg_community.MANUAL_AS_NUMBER
    tx_eth_seg_community.as_number = 8
    tx_eth_seg_community.as_custom = 8
    tx_eth_seg.as_path.segments.add("as_confed_seq", [2, 3])
    # Adding Tx EVI on the Ethernet Segment
    tx_evi_vxlan = tx_eth_seg.evis.evi_vxlan()[-1]
    tx_evi_vxlan.route_distinguisher.rd_type = tx_evi_vxlan.route_distinguisher.AS_2OCTET
    tx_evi_vxlan.route_distinguisher.rd_value = "1000:1"
    tx_evi_vxlan.advanced.origin = tx_evi_vxlan.advanced.EGP
    tx_evi_vxlan_comm = tx_evi_vxlan.communities.add()
    tx_evi_vxlan_comm.type = tx_evi_vxlan_comm.MANUAL_AS_NUMBER
    tx_evi_vxlan_comm.as_number = 3
    tx_evi_vxlan_comm.as_custom = 3
    tx_evi_vxlan.as_path.segments.add("as_seq", [9, 10])
    tx_export_rt = tx_evi_vxlan.route_target_export.routetarget()[-1]
    tx_import_rt = tx_evi_vxlan.route_target_import.routetarget()[-1]
    tx_export_rt.rt_type = tx_export_rt.AS_2OCTET
    tx_export_rt.rt_value = "200:20"
    tx_import_rt.rt_type = tx_import_rt.AS_2OCTET
    tx_import_rt.rt_value = "300:30"
    # Adding tx Broadcast Domain per EVI and MAC range
    tx_evpn_brodcust_domain = tx_evi_vxlan.broadcast_domains.broadcastdomain()[-1]
    tx_evpn_brodcust_domain.ethernet_tag_id = 5
    tx_evpn_brodcust_domain.vlan_aware_service = True
    tx_broadcust_macrange = tx_evpn_brodcust_domain.cmac_ip_range.cmaciprange(l2vni=16, name="tx_cmaciprange")[-1]
    tx_broadcust_macrange.mac_addresses.address = "10:11:22:33:44:55"
    tx_broadcust_macrange.ipv4_addresses.address = "2.2.2.2"
    tx_broadcust_macrange.ipv6_addresses.address = "2000:0:2:1::1"

    # Create BPG EVPN on rx
    rx_vtep = config.devices.device(name='rx_vtep')[-1]
    rx_vtep_bgp = rx_vtep.bgp
    rx_vtep_bgp.router_id = "191.0.0.1"
    rx_vtep_bgp_iface = (rx_vtep_bgp.ipv4_interfaces
        .v4interface(ipv4_name=rx_l1.name)[-1])
    rx_vtep_bgp_peer = rx_vtep_bgp_iface.peers.v4peer(name="bgp2",
                                                      peer_address='1.1.1.1',
                                                      as_type='ibgp',
                                                      as_number=101)[-1]
    rx_eth_seg = rx_vtep_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]
    rx_eth_seg.esi = '00000000000000000002'
    rx_eth_seg.esi_label = 8
    rx_eth_seg.active_mode = rx_eth_seg.SINGLE_ACTIVE
    rx_eth_seg.advanced.origin = rx_eth_seg.advanced.EGP
    rx_eth_seg_community = rx_eth_seg.communities.add()
    rx_eth_seg_community.type = rx_eth_seg_community.MANUAL_AS_NUMBER
    rx_eth_seg_community.as_number = 9
    rx_eth_seg_community.as_custom = 9
    rx_eth_seg.as_path.segments.add("as_confed_seq", [4, 5])
    # Adding Tx EVI on the Ethernet Segment
    rx_evi_vxlan = rx_eth_seg.evis.evi_vxlan()[-1]
    rx_evi_vxlan.route_distinguisher.rd_type = rx_evi_vxlan.route_distinguisher.AS_2OCTET
    rx_evi_vxlan.route_distinguisher.auto_config_rd_ip_addr = False
    rx_evi_vxlan.route_distinguisher.rd_value = "3000:3"
    rx_evi_vxlan.advanced.origin = rx_evi_vxlan.advanced.EGP
    rx_evi_vxlan_comm = rx_evi_vxlan.communities.add()
    rx_evi_vxlan_comm.type = rx_evi_vxlan_comm.MANUAL_AS_NUMBER
    rx_evi_vxlan_comm.as_number = 4
    rx_evi_vxlan_comm.as_custom = 4
    # rx_evi_vxlan.as_path.segments.add("as_seq", [9, 10])
    rx_export_rt = rx_evi_vxlan.route_target_export.routetarget()[-1]
    rx_import_rt = rx_evi_vxlan.route_target_import.routetarget()[-1]
    rx_export_rt.rt_type = rx_export_rt.AS_4OCTET
    rx_export_rt.rt_value = "400:40"
    rx_import_rt.rt_type = rx_import_rt.AS_4OCTET
    rx_import_rt.rt_value = "500:50"
    rx_export_rt = rx_evi_vxlan.route_target_export.routetarget()[-1]
    rx_import_rt = rx_evi_vxlan.route_target_import.routetarget()[-1]
    rx_export_rt.rt_type = rx_export_rt.IPV4_ADDRESS
    rx_export_rt.rt_value = "3.3.3.3:60"
    rx_import_rt.rt_type = rx_import_rt.IPV4_ADDRESS
    rx_import_rt.rt_value = "4.4.4.4:70"
    # Adding tx Broadcast Domain per EVI and MAC range
    rx_evpn_brodcust_domain = rx_evi_vxlan.broadcast_domains.broadcastdomain()[-1]
    rx_evpn_brodcust_domain.ethernet_tag_id = 5
    rx_evpn_brodcust_domain.vlan_aware_service = True
    rx_broadcust_macrange = rx_evpn_brodcust_domain.cmac_ip_range.cmaciprange(l2vni=16, name="rx_cmaciprange")[-1]
    rx_broadcust_macrange.mac_addresses.address = "10:11:33:33:44:55"
    rx_broadcust_macrange.ipv4_addresses.address = "3.3.3.1"
    rx_broadcust_macrange.ipv6_addresses.address = "3000:0:3:1::1"

    print(config.serialize())
    api.set_config(config)
    validate_result(api)

def validate_result(api):
    ixn = api._ixnetwork
    bgps = ixn.Topology.find().DeviceGroup.find().DeviceGroup.find().Ipv4Loopback.find().BgpIpv4Peer.find()
    for bgp in bgps:
        assert bgp.EthernetSegmentsCountV4 == 1
        assert bgp.BgpEthernetSegmentV4.EvisCount == 1
        evis = bgp.BgpIPv4EvpnVXLAN.find()
        assert evis.Multiplier == 1

if __name__ == "__main__":
    pytest.main(["-s", __file__])