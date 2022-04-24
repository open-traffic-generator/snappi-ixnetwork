from snappi_ixnetwork.device.base import Base

"""
Need clarification form Protocols team
    - evpn_ethernet_segments/active_mode => check ixn property
    - evpn_ethernet_segments/advance/multi_exit_discriminator => need review
    - evpn_ethernet_segments/ext_communities/value => check ixn map
"""


class BgpEvpn(Base):
    _ETHER_SEGMENT = {
        "esi": "esiValue",
        "esi_label": "esiLabel"
        # "active_mode": {
        #     "ixn_attr": "asSetMode",
        #     "enum_map": {
        #         "single_active": "includelocalasasasseq",
        #         "all_active": ""
        #     }
        # },
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

    def __init__(self, ngpf):
        super(BgpEvpn, self).__init__()
        self._ngpf = ngpf
        self._peer_class = None

    def config(self, bgp_peer, ixn_bgpv4):
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
            ixn_bgpv4["ethernetSegmentsCountV4"] = eth_segment_info.max_len
            ixn_eth_segments = self.create_property(
                ixn_bgpv4, "bgpEthernetSegmentV4"
            )
        else:
            raise Exception("TBD")

        self._config_eth_segment(eth_segment_info, ixn_eth_segments)
        self._config_evis(eth_segment_info, ixn_bgpv4, ixn_eth_segments)

    def _config_advance(self, parent_info, ixn_parent):
        advanced = parent_info.get_tab("advanced")
        if advanced.is_all_null:
            return None

        ixn_parent["origin"] = advanced.get_multivalues(
            "origin"
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

    def _config_evis(self, eth_segment_info, ixn_bgpv4, ixn_eth_segments):
        vxlan_info = eth_segment_info.get_symmetric_nodes("evis")
        ixn_eth_segments["evisCount"] = vxlan_info.max_len
        if self._peer_class == "BgpV4Peer":
            ixn_xvlan = self.create_node_elemet(
                ixn_bgpv4, "bgpIPv4EvpnVXLAN"
            )
        else:
            raise Exception("TBD")
        vxlan_info.config_values(ixn_xvlan, BgpEvpn._VXLAN)
        distinguisher_info = vxlan_info.get_tab("route_distinguisher")
        ixn_xvlan["rdType"] = distinguisher_info.get_multivalues(
            "rd_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
        )
        ixn_xvlan["rdASNumber"] = self.multivalue([
            self.asdot2plain(v) for v in distinguisher_info.get_values("rd_value")
        ])

        exports_info_list = vxlan_info.get_group_nodes("route_target_export")
        if len(exports_info_list) > 0:
            ixn_xvlan["numRtInExportRouteTargetList"] = len(
                exports_info_list
            )
        for exports_info in exports_info_list:
            ixn_exports = self.create_node_elemet(ixn_xvlan, "bgpExportRouteTargetList")
            ixn_exports["targetType"] = exports_info.get_multivalues(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            ixn_exports["targetAsNumber"] = self.multivalue([
                self.asdot2plain(v) for v in exports_info.get_values("rt_value")
            ])

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
                broadcast_domains_info.config_values(
                    ixn_broadcast_domains, BgpEvpn._BROADCAST_DOMAINS
                )
                self._config_cmac_ip_range(broadcast_domains_info)


    def _config_cmac_ip_range(self, broadcast_domains_info):
        cmac_ip_range_info = broadcast_domains_info.get_symmetric_nodes(
            "cmac_ip_range"
        )
        if cmac_ip_range_info.is_all_null:
            return

