from snappi_ixnetwork.device.base import Base, NodesInfo
from snappi_ixnetwork.device.utils import convert_as_values, hex_to_ipv4


class BgpEvpn(Base):
    _ETHER_SEGMENT = {
        "esi": "esiValue",
        "esi_label": "esiLabel",
        "active_mode": {
            "ixn_attr": "enableSingleActive",
            "enum_map": {"single_active": True, "all_active": False},
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
                "no_llgr": "no_llgr",
            },
        },
        "as_number": "asNumber",
        "as_custom": "lastTwoOctets",
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
                "administrator_as_2octet_link_bandwidth": "administratoras2octetlinkbw",
            },
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
                "mac_address": "macaddress",
            },
        },
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
        "pmsi_label": "upstreamDownstreamAssignedMplsLabel",
        "replication_type": {
            "ixn_attr": "multicastTunnelType",
            "enum_map": {
                "ingress_replication": "tunneltypeingressreplication"
            },
        },
    }

    _COMMON_ROUTE_TYPE = {
        "as_2octet": "as",
        "as_4octet": "as4",
        "ipv4_address": "ip",
    }

    _BROADCAST_DOMAINS = {
        "ethernet_tag_id": "ethernetTagId",
        "vlan_aware_service": "enableVlanAwareService",
    }

    _MAC_ADDRESS = {
        "address": "mac",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy",
    }

    _IP_ADDRESS = {
        "address": "networkAddress",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy",
    }

    _CMAC_PROPERTIES = {
        "l2vni": "firstLabelStart",
        "l3vni": "secondLabelStart",
        "include_default_gateway": "includeDefaultGatewayExtendedCommunity",
    }

    def __init__(self, ngpf):
        super(BgpEvpn, self).__init__()
        self._ngpf = ngpf
        self._peer_class = None

    def config(self, bgp_peer, ixn_bgp):
        if bgp_peer.get("evpn_ethernet_segments") is None:
            return
        ixn_bgp["filterEvpn"] = self.multivalue(True)
        eth_segment_info = self.get_symmetric_nodes(
            [bgp_peer], "evpn_ethernet_segments"
        )
        if eth_segment_info.is_all_null or eth_segment_info.max_len == 0:
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

        ixn_parent["origin"] = advanced.get_multivalues("origin")
        med_values = []
        for node in advanced.symmetric_nodes:
            med_values.append(node.get("multi_exit_discriminator"))
        if med_values.count(None) != len(med_values):
            ixn_parent["enableMultiExitDiscriminator"] = self.multivalue(True)
            ixn_parent["multiExitDiscriminator"] = self.multivalue(med_values)

    def _config_communities(self, parent_info, ixn_parent):
        active_list, communities_info_list = parent_info.get_group_nodes(
            "communities"
        )
        if len(communities_info_list) == 0:
            return None

        ixn_parent["noOfCommunities"] = len(communities_info_list)
        ixn_parent["enableCommunity"] = self.multivalue(active_list)
        for communities_info in communities_info_list:
            ixn_communities = self.create_node_elemet(
                ixn_parent, "bgpCommunitiesList"
            )
            communities_info.config_values(
                ixn_communities, BgpEvpn._SEG_COMMUNITIES
            )

    def _config_ext_communities(self, parent_info, ixn_parent):
        active_list, ext_communitiesinfo_list = parent_info.get_group_nodes(
            "ext_communities"
        )
        if len(ext_communitiesinfo_list) == 0:
            return None

        ixn_parent["noOfExtendedCommunity"] = len(ext_communitiesinfo_list)
        ixn_parent["enableExtendedCommunity"] = self.multivalue(active_list)
        for ext_communitiesinfo in ext_communitiesinfo_list:
            ixn_ext_communities = self.create_node_elemet(
                ixn_parent, "bgpExtendedCommunitiesList"
            )
            ext_communitiesinfo.config_values(
                ixn_ext_communities, BgpEvpn._SEG_EXT_COMMUNITIES
            )
            types = ixn_ext_communities.get("type").value
            sub_types = ixn_ext_communities.get("subType").value
            values = ext_communitiesinfo.get_values(
                "value", default="0000000000c8"
            )
            idx = 0
            opaqueData = list()
            ip = list()
            assignedNumber2Bytes = list()
            asNumber2Bytes = list()
            asNumber4Bytes = list()
            assignedNumber4Bytes = list()
            colorCOBits = list()
            colorReservedBits = list()
            colorValue = list()
            for type, sub_type, value in zip(types, sub_types, values):
                value.zfill(12)
                opaqueData.append("000000000000")
                ip.append("1.1.1.1")
                assignedNumber2Bytes.append("1")
                asNumber2Bytes.append("1")
                asNumber4Bytes.append("1")
                assignedNumber4Bytes.append("1")
                colorCOBits.append("00")
                colorReservedBits.append("0")
                colorValue.append("0")

                if type == "administratorip":
                    if sub_type == "extendedbandwidth":
                        opaqueData[idx] = value
                    else:
                        ip[idx] = hex_to_ipv4(value[:8])
                        assignedNumber2Bytes[idx] = int(value[8:], 16)
                elif type == "administratoras2octet":
                    if sub_type == "extendedbandwidth":
                        opaqueData[idx] = value
                    else:
                        asNumber2Bytes[idx] = int(value[:4], 16)
                        assignedNumber4Bytes[idx] = int(value[4:], 16)
                elif type == "administratoras4octet":
                    if sub_type == "extendedbandwidth":
                        opaqueData[idx] = value
                    else:
                        asNumber4Bytes[idx] = int(value[:8], 16)
                        assignedNumber2Bytes[idx] = int(value[8:], 16)
                elif type == "opaque":
                    if sub_type == "color":
                        bin_values = bin(int(value[:4], 16))[2:].zfill(8)
                        colorCOBits[idx] = bin_values[:2]
                        colorReservedBits[idx] = int(bin_values[2:], 2)
                        colorValue[idx] = int(value[4:], 16)
                    else:
                        opaqueData[idx] = value
                elif type == "evpn":
                    if sub_type == "macaddress":
                        opaqueData[idx] = value
                idx += 1

            ixn_ext_communities["opaqueData"] = self.multivalue(opaqueData)
            ixn_ext_communities["ip"] = self.multivalue(ip)
            ixn_ext_communities["assignedNumber2Bytes"] = self.multivalue(
                assignedNumber2Bytes
            )
            ixn_ext_communities["asNumber2Bytes"] = self.multivalue(
                asNumber2Bytes
            )
            ixn_ext_communities["asNumber4Bytes"] = self.multivalue(
                asNumber4Bytes
            )
            ixn_ext_communities["assignedNumber4Bytes"] = self.multivalue(
                assignedNumber4Bytes
            )
            ixn_ext_communities["colorCOBits"] = self.multivalue(colorCOBits)
            ixn_ext_communities["colorReservedBits"] = self.multivalue(
                colorReservedBits
            )
            ixn_ext_communities["colorValue"] = self.multivalue(colorValue)

    def _config_as_path_segments(self, parent_info, ixn_parent):
        as_path = parent_info.get_tab("as_path")
        if as_path.is_all_null:
            return None

        ixn_parent["overridePeerAsSetMode"] = self.multivalue(True)
        ixn_parent["asSetMode"] = as_path.get_multivalues(
            "as_set_mode", BgpEvpn._AS_SET_MODE
        )
        active_list, segments_info_list = as_path.get_group_nodes("segments")
        if len(segments_info_list) > 0:
            ixn_parent["enableAsPathSegments"] = self.multivalue(active_list)
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
                active_list, numbers_info_list = segments_info.get_group_nodes(
                    "as_numbers"
                )
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
            ixn_eth_segments["dfElectionTimer"] = (
                df_election_info.get_multivalues("election_timer")
            )

        self._config_advance(eth_segment_info, ixn_eth_segments)
        self._config_communities(eth_segment_info, ixn_eth_segments)
        self._config_ext_communities(eth_segment_info, ixn_eth_segments)
        self._config_as_path_segments(eth_segment_info, ixn_eth_segments)

    def _set_target(self, ixn_obj, rt_types, convert_rt_values):
        ixn_obj["targetType"] = self.multivalue(rt_types)
        ixn_obj["targetAsNumber"] = self.multivalue(convert_rt_values.as_num)
        ixn_obj["targetAs4Number"] = self.multivalue(convert_rt_values.as4_num)
        ixn_obj["targetIpAddress"] = self.multivalue(convert_rt_values.ip_addr)
        ixn_obj["targetAssignedNumber"] = self.multivalue(
            convert_rt_values.assign_num
        )

    def _config_evis(self, eth_segment_info, ixn_bgp, ixn_eth_segments):
        vxlan_info = eth_segment_info.get_symmetric_nodes("evis")
        ixn_eth_segments["evisCount"] = vxlan_info.max_len
        if self._peer_class == "BgpV4Peer":
            ixn_xvlan = self.create_node_elemet(ixn_bgp, "bgpIPv4EvpnVXLAN")
        else:
            ixn_xvlan = self.create_node_elemet(ixn_bgp, "bgpIPv6EvpnVXLAN")
        vxlan_info.config_values(ixn_xvlan, BgpEvpn._VXLAN)

        # Configure route_distinguisher
        distinguisher_info = vxlan_info.get_tab("route_distinguisher")
        rd_types = distinguisher_info.get_values(
            "rd_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
        )
        convert_values = convert_as_values(
            rd_types,
            distinguisher_info.get_values("rd_value", default="65101:1"),
        )
        ixn_xvlan["rdType"] = self.multivalue(rd_types)
        ixn_xvlan["rdASNumber"] = self.multivalue(convert_values.common_num)
        ixn_xvlan["rdEvi"] = self.multivalue(convert_values.assign_num)
        ixn_xvlan["rdIpAddress"] = self.multivalue(convert_values.ip_addr)
        ixn_xvlan["autoConfigureRdIpAddress"] = (
            distinguisher_info.get_multivalues(
                "auto_config_rd_ip_addr", default=True
            )
        )

        # Configure route_target_export
        exports_info_list = vxlan_info.get_active_group_nodes(
            "route_target_export"
        )
        if len(exports_info_list) > 0:
            ixn_xvlan["numRtInExportRouteTargetList"] = len(exports_info_list)
        for exports_info in exports_info_list:
            ixn_export = self.create_node_elemet(
                ixn_xvlan, "bgpExportRouteTargetList"
            )
            rt_types = exports_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types,
                exports_info.get_values("rt_value", default="65101:1"),
            )
            self._set_target(ixn_export, rt_types, convert_rt_values)

        # Configure route_target_import
        import_info_list = vxlan_info.get_active_group_nodes(
            "route_target_import"
        )
        if len(import_info_list) > 0:
            ixn_xvlan["importRtListSameAsExportRtList"] = False
            ixn_xvlan["numRtInImportRouteTargetList"] = len(import_info_list)
        for import_info in import_info_list:
            ixn_import = self.create_node_elemet(
                ixn_xvlan, "bgpImportRouteTargetList"
            )
            rt_types = import_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types, import_info.get_values("rt_value", default="65101:1")
            )
            self._set_target(ixn_import, rt_types, convert_rt_values)

        # Configure l3_route_target_export
        l3exports_info_list = vxlan_info.get_active_group_nodes(
            "l3_route_target_export"
        )
        if len(l3exports_info_list) > 0:
            ixn_xvlan["numRtInL3vniExportRouteTargetList"] = len(
                l3exports_info_list
            )
        for l3exports_info in l3exports_info_list:
            ixn_l3export = self.create_node_elemet(
                ixn_xvlan, "bgpL3VNIExportRouteTargetList"
            )
            rt_types = l3exports_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types,
                l3exports_info.get_values("rt_value", default="65101:1"),
            )
            self._set_target(ixn_l3export, rt_types, convert_rt_values)

        # Configure l3_route_target_import
        l3import_info_list = vxlan_info.get_active_group_nodes(
            "l3_route_target_import"
        )
        if len(l3import_info_list) > 0:
            ixn_xvlan["l3vniImportRtListSameAsL3vniExportRtList"] = False
            ixn_xvlan["numRtInL3vniImportRouteTargetList"] = len(
                l3import_info_list
            )
        for l3import_info in l3import_info_list:
            ixn_l3import = self.create_node_elemet(
                ixn_xvlan, "bgpL3VNIImportRouteTargetList"
            )
            rt_types = l3import_info.get_values(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )
            convert_rt_values = convert_as_values(
                rt_types,
                l3import_info.get_values("rt_value", default="65101:1"),
            )
            self._set_target(ixn_l3import, rt_types, convert_rt_values)

        self._config_advance(vxlan_info, ixn_xvlan)
        self._config_communities(vxlan_info, ixn_xvlan)
        self._config_ext_communities(vxlan_info, ixn_xvlan)
        self._config_as_path_segments(vxlan_info, ixn_xvlan)

        broadcast_domains_info = vxlan_info.get_symmetric_nodes(
            "broadcast_domains"
        )
        if not broadcast_domains_info.is_all_null:
            if self._peer_class == "BgpV4Peer":
                ixn_xvlan["numBroadcastDomainV4"] = (
                    broadcast_domains_info.max_len
                )
                ixn_broadcast_domains = self.create_property(
                    ixn_xvlan, "broadcastDomainV4"
                )
            else:
                ixn_xvlan["numBroadcastDomainV6"] = (
                    broadcast_domains_info.max_len
                )
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
            symmetric_nodes.append(node.get(address_type))
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
                active_list[idx] = (
                    cmac_ip_range_info.active_list[idx] and active_list[idx]
                )
        return NodesInfo(
            cmac_ip_range_info.max_len, active_list, symmetric_nodes
        )

    def _config_cmac_ip_range(
        self, broadcast_domains_info, ixn_broadcast_domains, ixn_xvlan
    ):
        cmac_ip_range_info = broadcast_domains_info.get_symmetric_nodes(
            "cmac_ip_range"
        )
        if cmac_ip_range_info.is_all_null:
            return

        mac_info = self._get_symetic_address(
            cmac_ip_range_info, "mac_addresses"
        )
        ipv4_info = self._get_symetic_address(
            cmac_ip_range_info, "ipv4_addresses"
        )
        ipv6_info = self._get_symetic_address(
            cmac_ip_range_info, "ipv6_addresses"
        )
        ixn_broadcast_domains["noOfMacPools"] = cmac_ip_range_info.max_len
        if mac_info.is_all_null:
            raise Exception("mac_addresses should configured in cmac_ip_range")
        names = cmac_ip_range_info.get_values("name")
        ixn_ng = self.create_node_elemet(self._ngpf.working_dg, "networkGroup")
        for node in cmac_ip_range_info.symmetric_nodes:
            self._ngpf.set_device_info(node, ixn_ng)
        ixn_ng["name"] = names
        self._ngpf.api.ixn_objects.set_scalable(ixn_ng)
        ixn_ng["enabled"] = self.multivalue(cmac_ip_range_info.active_list)
        ixn_mac_pools = self.create_node_elemet(
            ixn_ng, "macPools", "pool_{}".format(names[0])
        )
        mac_info.config_values(ixn_mac_pools, BgpEvpn._MAC_ADDRESS)
        ixn_connector = self.create_property(ixn_mac_pools, "connector")
        ixn_connector["connectedTo"] = self.post_calculated(
            "connectedTo", ref_ixnobj=ixn_xvlan
        )
        ixn_mac = self.create_node_elemet(
            ixn_mac_pools, "cMacProperties", "mac_{}".format(names[0])
        )
        ixn_mac["enableSecondLabel"] = self.multivalue(True)
        cmac_ip_range_info.config_values(ixn_mac, BgpEvpn._CMAC_PROPERTIES)
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
