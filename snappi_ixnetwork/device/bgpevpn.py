from snappi_ixnetwork.device.base import Base, NodesInfo
from snappi_ixnetwork.device.utils import asdot2plain, convert_as_values


class BgpEvpn(Base):
    _ETHER_SEGMENT = {
        "esi": "esiValue",
        "esi_label": "esiLabel",
        "active_mode": {
            "ixn_attr": "enableSingleActive",
            "enum_map": {
                "single_active": True,
                "all_active": False
            }
        },
    }

    _SEG_COMMUNITIES = {
        "type": {
            "ixn_attr": "type",
            "default_value": "no_export",
            "enum_map": {
                "manual_as_number": "manual",
                "no_export": "noexport",
                "no_advertised": "noadvertised",
                "no_export_subconfed": "noexport_subconfed",
                "llgr_stale": "llgr_stale",
                "no_llgr": "no_llgr"
            }
        },
        "as_number": "asNumber",
        "as_custom": "lastTwoOctets"
    }

    _SEG_EXT_COMMUNITIES = {
        "type": {
            "ixn_attr": "type",
            "default_value": "administrator_as_2octet",
            "enum_map": {
                "administrator_as_2octet": "administratoras2octet",
                "administrator_ipv4_address": "administratorip",
                "administrator_as_4octet": "administratoras4octet",
                "opaque": "opaque",
                "evpn": "evpn",
                "administrator_as_2octet_link_bandwidth": "administratoras2octetlinkbw"
            }
        },
        "subtype": {
            "ixn_attr": "subType",
            "default_value": "route_target",
            "enum_map": {
                "route_target": "routetarget",
                "origin": "origin",
                "extended_bandwidth": "extendedbandwidth",
                "color": "color",
                "encapsulation": "encapsulation",
                "mac_address": "macaddress"
            }
        }
    }

    _AS_SET_MODE = {
        "do_not_include_local_as": "dontincludelocalas",
        "include_as_seq": "includelocalasasasseq",
        "include_as_set": "includelocalasasasset",
        "include_as_confed_seq": "includelocalasasasseqconfederation",
        "include_as_confed_set": "includelocalasasassetconfederation",
        "prepend_to_first_segment": "prependlocalastofirstsegment",
    }

    _SEGMENT_TYPE = {
        "as_seq": "asseq",
        "as_set": "asset",
        "as_confed_seq": "asseqconfederation",
        "as_confed_set": "assetconfederation",
    }

    _VXLAN = {
        "ad_label": "adRouteLabel",
        "replication_type": {
            "ixn_attr": "multicastTunnelType",
            "enum_map": {
                "ingress_replication": "tunneltypeingressreplication"
            }
        }
    }

    _COMMON_ROUTE_TYPE = {
        "as_2octet": "as",
        "as_4octet": "as4",
        "ipv4_address": "ip"
    }

    _BROADCAST_DOMAINS = {
        "ethernet_tag_id": "ethernetTagId",
        "vlan_aware_service": "enableVlanAwareService"
    }

    _MAC_ADDRESS = {
        "address": "mac",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy"
    }

    _IP_ADDRESS = {
        "address": "networkAddress",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy"
    }

    def __init__(self, ngpf):
        super(BgpEvpn, self).__init__()
        self._ngpf = ngpf
        self._peer_class = None

    def config(self, bgp_peer, ixn_bgp):
        if bgp_peer.get("evpn_ethernet_segments") is None:
            return
        eth_segment_info = self.get_symmetric_nodes(
            [bgp_peer], "evpn_ethernet_segments"
        )
        if eth_segment_info.is_all_null or \
                eth_segment_info.max_len == 0:
            return
        self._peer_class = bgp_peer.__class__.__name__
        if self._peer_class == "BgpV4Peer":
            ixn_bgp["ethernetSegmentsCountV4"] = eth_segment_info.max_len
            ixn_eth_segments = self.create_property(
                ixn_bgp, "bgpEthernetSegmentV4"
            )
        else:
            ixn_bgp["ethernetSegmentsCountV6"] = eth_segment_info.max_len
            ixn_eth_segments = self.create_property(
                ixn_bgp, "bgpEthernetSegmentV6"
            )

        self._config_eth_segment(eth_segment_info, ixn_eth_segments)
        self._config_evis(eth_segment_info, ixn_bgp, ixn_eth_segments)

    def _config_advance(self, parent_info, ixn_parent):
        advanced = parent_info.get_tab("advanced")
        if advanced.is_all_null:
            return None

        ixn_parent["origin"] = advanced.get_multivalues(
            "origin"
        )
        med_values = advanced.get_values_fill("multi_exit_discriminator")
        if med_values.count(None) != len(med_values):
            ixn_parent["enableMultiExitDiscriminator"] = self.multivalue(True)
            ixn_parent["multiExitDiscriminator"] = self.multivalue(
                med_values
            )

    def _config_communities(self, parent_info, ixn_parent):
        communities_info_list = parent_info.get_group_nodes("communities")
        if len(communities_info_list) == 0:
            return None

        ixn_parent["noOfCommunities"] = len(communities_info_list)
        ixn_parent["enableCommunity"] = self.multivalue(True)
        for communities_info in communities_info_list:
            ixn_communities = self.create_node_elemet(ixn_parent, "bgpCommunitiesList")
            communities_info.config_values(
                ixn_communities, BgpEvpn._SEG_COMMUNITIES
            )

    def _config_ext_communities(self, parent_info, ixn_parent):
        ext_communitiesinfo_list = parent_info.get_group_nodes("ext_communities")
        if len(ext_communitiesinfo_list) == 0:
            return None

        ixn_parent["noOfExtendedCommunity"] = len(
            ext_communitiesinfo_list
        )
        ixn_parent["enableExtendedCommunity"] = self.multivalue(True)
        for ext_communitiesinfo in ext_communitiesinfo_list:
            ixn_ext_communities = self.create_node_elemet(
                ixn_parent, "bgpExtendedCommunitiesList"
            )
            ext_communitiesinfo.config_values(
                ixn_ext_communities, BgpEvpn._SEG_EXT_COMMUNITIES
            )
            # check and add value logic

    def _config_as_path_segments(self, parent_info, ixn_parent):
        as_path = parent_info.get_tab("as_path")
        if as_path.is_all_null:
            return None

        ixn_parent["overridePeerAsSetMode"] = self.multivalue(True)
        ixn_parent["asSetMode"] = as_path.get_multivalues(
            "as_set_mode", BgpEvpn._AS_SET_MODE
        )
        segments_info_list = as_path.get_group_nodes("segments")
        if len(segments_info_list) > 0:
            ixn_parent["enableAsPathSegments"] = self.multivalue(True)
            ixn_parent["noOfASPathSegmentsPerRouteRange"] = len(
                segments_info_list
            )
            for segments_info in segments_info_list:
                ixn_segments = self.create_node_elemet(
                    ixn_parent, "bgpAsPathSegmentList"
                )
                ixn_segments["segmentType"] = segments_info.get_multivalues(
                    "type", BgpEvpn._SEGMENT_TYPE
                )
                numbers_info_list = segments_info.get_group_nodes("as_numbers")
                if len(numbers_info_list) > 0:
                    ixn_segments["numberOfAsNumberInSegment"] = len(
                        numbers_info_list
                    )
                    for numbers_info in numbers_info_list:
                        ixn_as_number = self.create_node_elemet(
                            ixn_segments, "bgpAsNumberList"
                        )
                        ixn_as_number["enableASNumber"] = self.multivalue(
                            numbers_info.active_list
                        )
                        ixn_as_number["asNumber"] = self.multivalue(
                            numbers_info.symmetric_nodes
                        )

    def _config_eth_segment(self, eth_segment_info, ixn_eth_segments):
        eth_segment_info.config_values(
            ixn_eth_segments, BgpEvpn._ETHER_SEGMENT
        )
        df_election_info = eth_segment_info.get_tab("df_election")
        if not df_election_info.is_all_null:
            ixn_eth_segments["dfElectionTimer"] = df_election_info.get_multivalues(
                "election_timer"
            )

        self._config_advance(eth_segment_info, ixn_eth_segments)
        self._config_communities(eth_segment_info, ixn_eth_segments)
        self._config_ext_communities(eth_segment_info, ixn_eth_segments)
        self._config_as_path_segments(eth_segment_info, ixn_eth_segments)

    def _config_evis(self, eth_segment_info, ixn_bgp, ixn_eth_segments):
        vxlan_info = eth_segment_info.get_symmetric_nodes("evis")
        ixn_eth_segments["evisCount"] = vxlan_info.max_len
        if self._peer_class == "BgpV4Peer":
            ixn_xvlan = self.create_node_elemet(
                ixn_bgp, "bgpIPv4EvpnVXLAN"
            )
        else:
            ixn_xvlan = self.create_node_elemet(
                ixn_bgp, "bgpIPv6EvpnVXLAN"
            )
        vxlan_info.config_values(ixn_xvlan, BgpEvpn._VXLAN)

        # Configure route_distinguisher
        distinguisher_info = vxlan_info.get_tab("route_distinguisher")
        ixn_xvlan["rdType"] = distinguisher_info.get_multivalues(
            "rd_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
        )
        ixn_xvlan["rdASNumber"] = self.multivalue([
            asdot2plain(v) for v in distinguisher_info.get_values("rd_value")
        ])

        # Configure route_target_export
        exports_info_list = vxlan_info.get_group_nodes("route_target_export")
        if len(exports_info_list) > 0:
            ixn_xvlan["numRtInExportRouteTargetList"] = len(
                exports_info_list
            )
        for exports_info in exports_info_list:
            ixn_exports = self.create_node_elemet(ixn_xvlan, "bgpExportRouteTargetList")
            rt_types = exports_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types, exports_info.get_values("rt_value")
            )
            ixn_exports["targetType"] = self.multivalue(rt_types)
            ixn_exports["targetAsNumber"] = self.multivalue(convert_rt_values.as_num)
            ixn_exports["targetAs4Number"] = self.multivalue(convert_rt_values.as4_num)
            ixn_exports["targetAssignedNumber"] = self.multivalue(
                convert_rt_values.assign_num
            )

        # Configure route_target_import
        import_info_list = vxlan_info.get_group_nodes("route_target_import")
        if len(import_info_list) > 0:
            ixn_xvlan["importRtListSameAsExportRtList"] = False
            ixn_xvlan["numRtInImportRouteTargetList"] = len(
                import_info_list
            )
        for import_info in import_info_list:
            ixn_import = self.create_node_elemet(ixn_xvlan, "bgpImportRouteTargetList")
            rt_types = import_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types, import_info.get_values("rt_value")
            )
            ixn_import["targetType"] = self.multivalue(rt_types)
            ixn_import["targetAsNumber"] = self.multivalue(convert_rt_values.as_num)
            ixn_import["targetAs4Number"] = self.multivalue(convert_rt_values.as4_num)
            ixn_import["targetAssignedNumber"] = self.multivalue(
                convert_rt_values.assign_num
            )

        # Configure l3_route_target_export
        l3exports_info_list = vxlan_info.get_group_nodes("l3_route_target_export")
        if len(l3exports_info_list) > 0:
            ixn_xvlan["numRtInL3vniExportRouteTargetList"] = len(
                l3exports_info_list
            )
        for l3exports_info in l3exports_info_list:
            ixn_l3export = self.create_node_elemet(ixn_xvlan, "bgpL3VNIExportRouteTargetList")
            rt_types = l3exports_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types, l3exports_info.get_values("rt_value")
            )
            ixn_l3export["targetType"] = self.multivalue(rt_types)
            ixn_l3export["targetAsNumber"] = self.multivalue(convert_rt_values.as_num)
            ixn_l3export["targetAs4Number"] = self.multivalue(convert_rt_values.as4_num)
            ixn_l3export["targetAssignedNumber"] = self.multivalue(
                convert_rt_values.assign_num
            )

        # Configure l3_route_target_import
        l3import_info_list = vxlan_info.get_group_nodes("l3_route_target_import")
        if len(l3import_info_list) > 0:
            ixn_xvlan["l3vniImportRtListSameAsL3vniExportRtList"] = False
            ixn_xvlan["numRtInL3vniImportRouteTargetList"] = len(
                l3import_info_list
            )
        for l3import_info in l3import_info_list:
            ixn_l3import = self.create_node_elemet(ixn_xvlan, "bgpL3VNIImportRouteTargetList")
            rt_types = l3import_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types, l3import_info.get_values("rt_value")
            )
            ixn_l3import["targetType"] = self.multivalue(rt_types)
            ixn_l3import["targetAsNumber"] = self.multivalue(convert_rt_values.as_num)
            ixn_l3import["targetAs4Number"] = self.multivalue(convert_rt_values.as4_num)
            ixn_l3import["targetAssignedNumber"] = self.multivalue(
                convert_rt_values.assign_num
            )

        self._config_advance(vxlan_info, ixn_xvlan)
        self._config_communities(vxlan_info, ixn_xvlan)
        self._config_ext_communities(vxlan_info, ixn_xvlan)
        self._config_as_path_segments(vxlan_info, ixn_xvlan)

        broadcast_domains_info = vxlan_info.get_symmetric_nodes(
            "broadcast_domains"
        )
        if not broadcast_domains_info.is_all_null:
            if self._peer_class == "BgpV4Peer":
                ixn_xvlan["numBroadcastDomainV4"] = broadcast_domains_info.max_len
                ixn_broadcast_domains = self.create_property(
                    ixn_xvlan, "broadcastDomainV4"
                )
            else:
                ixn_xvlan["numBroadcastDomainV6"] = broadcast_domains_info.max_len
                ixn_broadcast_domains = self.create_property(
                    ixn_xvlan, "broadcastDomainV6"
                )
            ixn_broadcast_domains["active"] = self.multivalue(
                broadcast_domains_info.active_list
            )
            broadcast_domains_info.config_values(
                ixn_broadcast_domains, BgpEvpn._BROADCAST_DOMAINS
            )
            self._config_cmac_ip_range(
                broadcast_domains_info, ixn_broadcast_domains, ixn_xvlan
            )

    def _get_symetic_address(self, cmac_ip_range_info, address_type):
        active_list = []
        symmetric_nodes = []
        dummy_value = None
        for node in cmac_ip_range_info.symmetric_nodes:
            symmetric_nodes.append(
                node.get(address_type)
            )
            if symmetric_nodes[-1] is None:
                active_list.append(False)
            else:
                active_list.append(True)
                if dummy_value is None:
                    dummy_value = symmetric_nodes[-1]

        if dummy_value is not None:
            for idx in range(len(active_list)):
                if active_list[idx] is False:
                    symmetric_nodes[idx] = dummy_value
                active_list[idx] = cmac_ip_range_info.active_list[idx] \
                                   and active_list[idx]
        return NodesInfo(
            cmac_ip_range_info.max_len,
            active_list,
            symmetric_nodes
        )

    def _config_cmac_ip_range(self, broadcast_domains_info, ixn_broadcast_domains, ixn_xvlan):
        cmac_ip_range_info = broadcast_domains_info.get_symmetric_nodes(
            "cmac_ip_range"
        )
        if cmac_ip_range_info.is_all_null:
            return

        mac_info = self._get_symetic_address(cmac_ip_range_info, "mac_addresses")
        ipv4_info = self._get_symetic_address(cmac_ip_range_info, "ipv4_addresses")
        ipv6_info = self._get_symetic_address(cmac_ip_range_info, "ipv6_addresses")
        ixn_broadcast_domains["noOfMacPools"] = cmac_ip_range_info.max_len
        if mac_info.is_all_null:
            raise Exception("mac_addresses should configured in cmac_ip_range")
        name = "macPool" # TBD : add proper name
        ixn_ng = self.create_node_elemet(
            self._ngpf.working_dg, "networkGroup", "ng_{}".format(name)
        )
        ixn_ng["enabled"] = self.multivalue(cmac_ip_range_info.active_list)
        ixn_mac_pools = self.create_node_elemet(
            ixn_ng, "macPools", "pool_{}".format(name)
        )
        mac_info.config_values(
            ixn_mac_pools, BgpEvpn._MAC_ADDRESS
        )
        ixn_connector = self.create_property(ixn_mac_pools, "connector")
        ixn_connector["connectedTo"] = self.post_calculated(
            "connectedTo", ref_ixnobj=ixn_xvlan
        )
        ixn_mac = self.create_node_elemet(
            ixn_mac_pools, "cMacProperties", "mac_{}".format(name)
        )
        self._config_advance(cmac_ip_range_info, ixn_mac)
        self._config_communities(cmac_ip_range_info, ixn_mac)
        self._config_ext_communities(cmac_ip_range_info, ixn_mac)
        self._config_as_path_segments(cmac_ip_range_info, ixn_mac)

        if not ipv4_info.is_all_null:
            ixn_ipv4 = self.create_node_elemet(
                ixn_mac_pools, "ipv4PrefixPools"
            )
            ixn_mac["advertiseIpv4Address"] = self.multivalue(
                ipv4_info.active_list
            )
            ipv4_info.config_values(ixn_ipv4, BgpEvpn._IP_ADDRESS)

        if not ipv6_info.is_all_null:
            ixn_ipv6 = self.create_node_elemet(
                ixn_mac_pools, "ipv6PrefixPools"
            )
            ixn_mac["advertiseIpv6Address"] = self.multivalue(
                ipv6_info.active_list
            )
            ipv6_info.config_values(ixn_ipv6, BgpEvpn._IP_ADDRESS)



















