import pytest


def test_bgp_evpn_validation(api, utils):
    "Validate BGP EVPN Attributes against RestPy"

    BGPV4_EVPN_ETH_SEGMENT = {
        "DfElectionTimer": 10,
        "EsiValue": "1000000000000000",
        "EsiLabel": 8,
        "EnableSingleActive": "true",
        "MultiExitDiscriminator": 5,
        "EnableMultiExitDiscriminator": "true",
        "Origin": "egp",
        "EnableOrigin": "true",
        "EnableCommunity": "true",
        "EnableExtendedCommunity": "true",
        "EnableAsPathSegments": "true",
        "AsSetMode": "includelocalasasasset",
    }

    BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST = {
        "Type": "manual",
        "AsNumber": "8",
        "LastTwoOctets": "8",
    }

    BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST = {
        "Type": "opaque",
        "SubType": "color",
        "ColorValue": "200",
    }

    BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST = {
        "SegmentType": "asseqconfederation",
    }

    BGPV4_EVPN_VXLAN = {
        "AdRouteLabel": 10,
        "UpstreamDownstreamAssignedMplsLabel": 20,
        "RdASNumber": 1000,
        "RdEvi": 10,
        "MultiExitDiscriminator": 99,
    }

    BGPV4_EVPN_VXLAN_EXPORT_TARGET = {
        "TargetAs4Number": "100",
        "TargetAssignedNumber": "20",
    }

    BGPV4_EVPN_VXLAN_IMPORT_TARGET = {
        "TargetAs4Number": "200",
        "TargetAssignedNumber": "30",
    }

    BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET = {
        "TargetAs4Number": "300",
        "TargetAssignedNumber": "50",
    }

    BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET = {
        "TargetAs4Number": "400",
        "TargetAssignedNumber": "60",
    }

    BROADCAST_DOMAIN = {"EthernetTagId": "5", "EnableVlanAwareService": "true"}

    MAC_ADDRESS = {
        "Mac": "10:11:22:33:44:55",
        "PrefixLength": "48",
        "NumberOfAddressesAsy": "1",
    }

    IP_ADDRESS = {
        "NetworkAddress": "2.2.2.2",
        "PrefixLength": "24",
        "NumberOfAddressesAsy": "1",
    }

    IPV6_ADDRESS = {
        "NetworkAddress": "2000:0:2:1::1",
        "PrefixLength": "64",
        "NumberOfAddressesAsy": "1",
    }

    CMAC_PROPERTIES = {
        "FirstLabelStart": "16",
        "SecondLabelStart": "20",
        "MultiExitDiscriminator": "37",
        "IncludeDefaultGatewayExtendedCommunity": "true",
    }

    # Creating Ports
    config = api.config()
    p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    # Create BGP devices on tx
    tx_d = config.devices.device(name="tx_d")[-1]
    tx_eth = tx_d.ethernets.add()
    tx_eth.connection.port_name = p1.name
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:11:00:00:00:01"
    tx_ip = tx_eth.ipv4_addresses.ipv4(
        name="tx_ip", address="20.20.20.2", gateway="20.20.20.1"
    )[-1]

    # tx_bgp
    tx_bgp = tx_d.bgp
    tx_bgp.router_id = "192.0.0.1"
    tx_bgp_iface = tx_bgp.ipv4_interfaces.v4interface(ipv4_name=tx_ip.name)[-1]
    tx_bgp_peer = tx_bgp_iface.peers.v4peer(
        name="tx_eBGP",
        peer_address="20.20.20.1",
        as_type="ebgp",
        as_number=100,
    )[-1]

    # Create & advertise loopback under bgp in tx and rx
    tx_l1 = tx_d.ipv4_loopbacks.add()
    tx_l1.name = "tx_loopback1"
    tx_l1.eth_name = "tx_eth"
    tx_l1.address = "1.1.1.1"
    tx_l1_r = tx_bgp_peer.v4_routes.add(name="tx_l1")
    tx_l1_r.addresses.add(address="1.1.1.1", prefix=32)

    # Create BGP EVPN on tx
    tx_vtep = config.devices.device(name="tx_vtep")[-1]
    tx_vtep_bgp = tx_vtep.bgp
    tx_vtep_bgp.router_id = "190.0.0.1"
    tx_vtep_bgp_iface = tx_vtep_bgp.ipv4_interfaces.v4interface(
        ipv4_name=tx_l1.name
    )[-1]
    tx_vtep_bgp_peer = tx_vtep_bgp_iface.peers.v4peer(
        name="bgp1", peer_address="2.2.2.2", as_type="ibgp", as_number=101
    )[-1]

    tx_eth_seg = tx_vtep_bgp_peer.evpn_ethernet_segments.ethernetsegment()[-1]
    tx_eth_seg.df_election.election_timer = BGPV4_EVPN_ETH_SEGMENT[
        "DfElectionTimer"
    ]
    tx_eth_seg.esi = BGPV4_EVPN_ETH_SEGMENT["EsiValue"]
    tx_eth_seg.esi_label = BGPV4_EVPN_ETH_SEGMENT["EsiLabel"]
    tx_eth_seg.active_mode = tx_eth_seg.SINGLE_ACTIVE
    tx_eth_seg.advanced.origin = tx_eth_seg.advanced.EGP
    tx_eth_seg.advanced.multi_exit_discriminator = BGPV4_EVPN_ETH_SEGMENT[
        "MultiExitDiscriminator"
    ]
    tx_eth_seg_community = tx_eth_seg.communities.add()
    tx_eth_seg_community.type = tx_eth_seg_community.MANUAL_AS_NUMBER
    tx_eth_seg_community.as_number = int(
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST["AsNumber"]
    )
    tx_eth_seg_community.as_custom = int(
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST["LastTwoOctets"]
    )
    tx_eth_seg_ext_community = tx_eth_seg.ext_communities.add()
    tx_eth_seg_ext_community.type = "opaque"
    tx_eth_seg_ext_community.subtype = "color"
    tx_eth_seg_ext_community.value = "0000000000C8"
    tx_eth_seg.as_path.as_set_mode = "include_as_set"
    tx_eth_seg.as_path.segments.add("as_confed_seq", [2, 3])

    # Adding Tx EVI on the Ethernet Segment
    tx_evi_vxlan = tx_eth_seg.evis.evi_vxlan()[-1]
    tx_evi_vxlan.route_distinguisher.rd_type = (
        tx_evi_vxlan.route_distinguisher.AS_2OCTET
    )
    tx_evi_vxlan.route_distinguisher.rd_value = (
        str(BGPV4_EVPN_VXLAN["RdASNumber"])
        + ":"
        + str(BGPV4_EVPN_VXLAN["RdEvi"])
    )
    tx_evi_vxlan.ad_label = BGPV4_EVPN_VXLAN["AdRouteLabel"]
    tx_evi_vxlan.pmsi_label = BGPV4_EVPN_VXLAN[
        "UpstreamDownstreamAssignedMplsLabel"
    ]

    export_rt = tx_evi_vxlan.route_target_export.routetarget()[-1]
    import_rt = tx_evi_vxlan.route_target_import.routetarget()[-1]
    export_rt.rt_type = export_rt.AS_4OCTET
    export_rt.rt_value = (
        BGPV4_EVPN_VXLAN_EXPORT_TARGET["TargetAs4Number"]
        + ":"
        + BGPV4_EVPN_VXLAN_EXPORT_TARGET["TargetAssignedNumber"]
    )
    import_rt.rt_type = import_rt.AS_4OCTET
    import_rt.rt_value = (
        BGPV4_EVPN_VXLAN_IMPORT_TARGET["TargetAs4Number"]
        + ":"
        + BGPV4_EVPN_VXLAN_IMPORT_TARGET["TargetAssignedNumber"]
    )

    l3_export_rt = tx_evi_vxlan.l3_route_target_export.routetarget()[-1]
    l3_import_rt = tx_evi_vxlan.l3_route_target_import.routetarget()[-1]
    l3_export_rt.rt_type = l3_export_rt.AS_4OCTET
    l3_export_rt.rt_value = (
        BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET["TargetAs4Number"]
        + ":"
        + BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET["TargetAssignedNumber"]
    )
    l3_import_rt.rt_type = l3_import_rt.AS_4OCTET
    l3_import_rt.rt_value = (
        BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET["TargetAs4Number"]
        + ":"
        + BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET["TargetAssignedNumber"]
    )

    tx_evi_vxlan.advanced.origin = tx_evi_vxlan.advanced.EGP
    tx_evi_vxlan.advanced.multi_exit_discriminator = BGPV4_EVPN_VXLAN[
        "MultiExitDiscriminator"
    ]
    tx_evi_vxlan_comm = tx_evi_vxlan.communities.add()
    tx_evi_vxlan_comm.type = tx_evi_vxlan_comm.MANUAL_AS_NUMBER
    tx_evi_vxlan_comm.as_number = int(
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST["AsNumber"]
    )
    tx_evi_vxlan_comm.as_custom = int(
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST["LastTwoOctets"]
    )
    tx_evi_vxlan_ext_comm = tx_evi_vxlan.ext_communities.add()
    tx_evi_vxlan_ext_comm.type = "opaque"
    tx_evi_vxlan_ext_comm.subtype = "color"
    tx_evi_vxlan_ext_comm.value = "0000000000C8"
    tx_evi_vxlan.as_path.segments.add("as_confed_seq", [9, 10])

    # Adding tx Broadcast Domain per EVI and MAC range
    tx_evpn_brodcast_domain = tx_evi_vxlan.broadcast_domains.broadcastdomain()[
        -1
    ]
    tx_evpn_brodcast_domain.ethernet_tag_id = int(
        BROADCAST_DOMAIN["EthernetTagId"]
    )
    tx_evpn_brodcast_domain.vlan_aware_service = True
    tx_broadcast_macrange = tx_evpn_brodcast_domain.cmac_ip_range.cmaciprange(
        l2vni=16, l3vni=20, name="tx_cmaciprange", include_default_gateway=True
    )[-1]
    tx_broadcast_macrange.mac_addresses.address = MAC_ADDRESS["Mac"]
    tx_broadcast_macrange.ipv4_addresses.address = IP_ADDRESS["NetworkAddress"]
    tx_broadcast_macrange.ipv6_addresses.address = IPV6_ADDRESS[
        "NetworkAddress"
    ]

    tx_broadcast_macrange.advanced.multi_exit_discriminator = int(
        CMAC_PROPERTIES["MultiExitDiscriminator"]
    )

    cmac_comm = tx_broadcast_macrange.communities.add()
    cmac_comm.type = cmac_comm.MANUAL_AS_NUMBER
    cmac_comm.as_number = int(
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST["AsNumber"]
    )
    cmac_comm.as_custom = int(
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST["LastTwoOctets"]
    )
    cmac_ext_comm = tx_broadcast_macrange.ext_communities.add()
    cmac_ext_comm.type = "opaque"
    cmac_ext_comm.subtype = "color"
    cmac_ext_comm.value = "0000000000C8"
    tx_broadcast_macrange.as_path.segments.add("as_confed_seq", [9, 10])

    api.set_config(config)

    validate_config(
        api,
        BGPV4_EVPN_ETH_SEGMENT,
        BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST,
        BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST,
        BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST,
        BGPV4_EVPN_VXLAN,
        BGPV4_EVPN_VXLAN_EXPORT_TARGET,
        BGPV4_EVPN_VXLAN_IMPORT_TARGET,
        BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET,
        BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET,
        BROADCAST_DOMAIN,
        MAC_ADDRESS,
        IP_ADDRESS,
        IPV6_ADDRESS,
        CMAC_PROPERTIES,
    )


def validate_config(
    api,
    BGPV4_EVPN_ETH_SEGMENT,
    BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST,
    BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST,
    BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST,
    BGPV4_EVPN_VXLAN,
    BGPV4_EVPN_VXLAN_EXPORT_TARGET,
    BGPV4_EVPN_VXLAN_IMPORT_TARGET,
    BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET,
    BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET,
    BROADCAST_DOMAIN,
    MAC_ADDRESS,
    IP_ADDRESS,
    IPV6_ADDRESS,
    CMAC_PROPERTIES,
):
    ixn = api._ixnetwork
    bgps = (
        ixn.Topology.find()
        .DeviceGroup.find()
        .DeviceGroup.find()
        .Ipv4Loopback.find()
        .BgpIpv4Peer.find()
    )
    for bgp in bgps:
        assert bgp.EthernetSegmentsCountV4 == 1
        assert bgp.BgpEthernetSegmentV4.EvisCount == 1
        evis = bgp.BgpIPv4EvpnVXLAN.find()
        assert evis.Multiplier == 1

    bgp_eth_seg = bgps[0].BgpEthernetSegmentV4
    for attr in BGPV4_EVPN_ETH_SEGMENT:
        if attr in ["DfElectionTimer", "EsiLabel", "MultiExitDiscriminator"]:
            assert BGPV4_EVPN_ETH_SEGMENT[attr] == int(
                (getattr(bgp_eth_seg, attr).Values)[0]
            )
        else:
            assert BGPV4_EVPN_ETH_SEGMENT[attr] == (
                (getattr(bgp_eth_seg, attr).Values)[0]
            )

    bgp_eth_seg_comm_list = bgps[
        0
    ].BgpEthernetSegmentV4.BgpCommunitiesList.find()
    for attr in BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST[attr] == (
            (getattr(bgp_eth_seg_comm_list, attr).Values)[0]
        )

    bgp_eth_seg_ext_comm_list = bgps[
        0
    ].BgpEthernetSegmentV4.BgpExtendedCommunitiesList.find()
    for attr in BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST[attr] == (
            (getattr(bgp_eth_seg_ext_comm_list, attr).Values)[0]
        )

    bgp_eth_seg_aspath_segments_list = bgps[
        0
    ].BgpEthernetSegmentV4.BgpAsPathSegmentList.find()
    for attr in BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST[attr] == (
            (getattr(bgp_eth_seg_aspath_segments_list, attr).Values)[0]
        )

    bgp_evpn_vxlan = bgps[0].BgpIPv4EvpnVXLAN.find()
    for attr in BGPV4_EVPN_VXLAN:
        assert BGPV4_EVPN_VXLAN[attr] == int(
            (getattr(bgp_evpn_vxlan, attr).Values)[0]
        )

    bgp_evpn_vxlan_export_target = (
        bgp_evpn_vxlan.BgpExportRouteTargetList.find()
    )
    for attr in BGPV4_EVPN_VXLAN_EXPORT_TARGET:
        assert BGPV4_EVPN_VXLAN_EXPORT_TARGET[attr] == (
            (getattr(bgp_evpn_vxlan_export_target, attr).Values)[0]
        )

    bgp_evpn_vxlan_import_target = (
        bgp_evpn_vxlan.BgpImportRouteTargetList.find()
    )
    for attr in BGPV4_EVPN_VXLAN_IMPORT_TARGET:
        assert BGPV4_EVPN_VXLAN_IMPORT_TARGET[attr] == (
            (getattr(bgp_evpn_vxlan_import_target, attr).Values)[0]
        )

    bgp_evpn_vxlan_l3_export_target = (
        bgp_evpn_vxlan.BgpL3VNIExportRouteTargetList.find()
    )
    for attr in BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET:
        assert BGPV4_EVPN_VXLAN_L3_EXPORT_TARGET[attr] == (
            (getattr(bgp_evpn_vxlan_l3_export_target, attr).Values)[0]
        )

    bgp_evpn_vxlan_l3_import_target = (
        bgp_evpn_vxlan.BgpL3VNIImportRouteTargetList.find()
    )
    for attr in BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET:
        assert BGPV4_EVPN_VXLAN_L3_IMPORT_TARGET[attr] == (
            (getattr(bgp_evpn_vxlan_l3_import_target, attr).Values)[0]
        )

    bgp_eth_seg_vxlan_comm_list = (
        bgps[0].BgpIPv4EvpnVXLAN.find().BgpCommunitiesList.find()
    )
    for attr in BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST[attr] == (
            (getattr(bgp_eth_seg_vxlan_comm_list, attr).Values)[0]
        )

    bgp_eth_seg_vxlan_ext_comm_list = (
        bgps[0].BgpIPv4EvpnVXLAN.find().BgpExtendedCommunitiesList.find()
    )
    for attr in BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST[attr] == (
            (getattr(bgp_eth_seg_vxlan_ext_comm_list, attr).Values)[0]
        )

    bgp_eth_seg_vxlan_aspath_segments_list = (
        bgps[0].BgpIPv4EvpnVXLAN.find().BgpAsPathSegmentList.find()
    )
    for attr in BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST[attr] == (
            (getattr(bgp_eth_seg_vxlan_aspath_segments_list, attr).Values)[0]
        )

    bgp_eth_seg_vxlan_broadcast_domain = (
        bgps[0].BgpIPv4EvpnVXLAN.find().BroadcastDomainV4
    )
    for attr in BROADCAST_DOMAIN:
        assert BROADCAST_DOMAIN[attr] == (
            (getattr(bgp_eth_seg_vxlan_broadcast_domain, attr).Values)[0]
        )

    mac = (
        ixn.Topology.find()
        .DeviceGroup.find()
        .DeviceGroup.find()
        .NetworkGroup.find()
        .MacPools.find()
    )
    for attr in MAC_ADDRESS:
        assert MAC_ADDRESS[attr] == ((getattr(mac, attr).Values)[0])

    ipv4 = mac.Ipv4PrefixPools.find()
    for attr in IP_ADDRESS:
        assert IP_ADDRESS[attr] == ((getattr(ipv4, attr).Values)[0])

    ipv6 = mac.Ipv6PrefixPools.find()
    for attr in IPV6_ADDRESS:
        assert IPV6_ADDRESS[attr] == ((getattr(ipv6, attr).Values)[0])

    cmac = mac.CMacProperties.find()
    for attr in CMAC_PROPERTIES:
        assert CMAC_PROPERTIES[attr] == ((getattr(cmac, attr).Values)[0])

    cmac_comm_list = cmac.BgpCommunitiesList.find()
    for attr in BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_COMMUNITIES_lIST[attr] == (
            (getattr(cmac_comm_list, attr).Values)[0]
        )

    cmac_ext_comm_list = cmac.BgpExtendedCommunitiesList.find()
    for attr in BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_EXT_COMMUNITIES_lIST[attr] == (
            (getattr(cmac_ext_comm_list, attr).Values)[0]
        )

    cmac_aspath_segments_list = cmac.BgpAsPathSegmentList.find()
    for attr in BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST:
        assert BGPV4_EVPN_ETH_SEGMENT_ASPATH_SEGMENTS_lIST[attr] == (
            (getattr(cmac_aspath_segments_list, attr).Values)[0]
        )


if __name__ == "__main__":
    pytest.main(["-s", __file__])
