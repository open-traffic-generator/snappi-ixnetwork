from snappi_ixnetwork.device.base import Base

class Bgp(Base):
    _BGP = {
        "peer_address": "dutIp",
        "as_type": {
            "ixn_attr": "type",
            "enum_map": {
                "ibgp": "internal",
                "ebgp": "external"
            }
        },
    }

    _ADVANCED = {
        "hold_time_interval": "holdTimer",
        "keep_alive_interval": "keepaliveTimer",
        "update_interval": "updateInterval",
        "time_to_live": "ttl",
        "md5_key": "md5Key"
    }

    _CAPABILITY = {
        "ipv4_unicast": "capabilityIpV4Unicast",
        "ipv4_multicast": "capabilityIpV4Multicast",
        "ipv6_unicast": "capabilityIpV6Unicast",
        "ipv6_multicast": "capabilityIpV6Multicast",
        "vpls": "capabilityVpls",
        "route_refresh": "capabilityRouteRefresh",
        "route_constraint": "capabilityRouteConstraint",
        "ink_state_non_vpn": "capabilityLinkStateNonVpn",
        "link_state_vpn": "capabilityLinkStateVpn",
        "evpn": "evpn",
        # "extended_next_hop_encoding": "",
        "ipv4_multicast_vpn": "capabilityIpV4MulticastVpn",
        "ipv4_mpls_vpn": "capabilityIpV4MplsVpn",
        "ipv4_mdt": "capabilityIpV4Mdt",
        "ipv4_multicast_mpls_vpn": "ipv4MulticastBgpMplsVpn",
        "ipv4_unicast_flow_spec": "capabilityipv4UnicastFlowSpec",
        "ipv4_sr_te_policy": "capabilitySRTEPoliciesV4",
        "ipv4_unicast_add_path": "capabilityIpv4UnicastAddPath",
        "ipv6_multicast_vpn": "capabilityIpV6MulticastVpn",
        "ipv6_mpls_vpn": "capabilityIpV6MplsVpn",
        # "ipv6_mdt": "",
        "ipv6_multicast_mpls_vpn": "ipv6MulticastBgpMplsVpn",
        "ipv6_unicast_flow_spec": "capabilityipv6UnicastFlowSpec",
        "ipv6_sr_te_policy": "capabilitySRTEPoliciesV6",
        "ipv6_unicast_add_path": "capabilityIpv6UnicastAddPath"
    }

    _IP_POOL = {
        "address": "networkAddress",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy",
        "step": "prefixAddrStep"
    }

    _ROUTE = {
        "next_hop_mode" : {
            "ixn_attr": "nextHopType",
            "enum_map": {
                "local_ip": "sameaslocalip",
                "manual": "manually"
            }
        },
        "next_hop_address_type": "nextHopIPType",
        "next_hop_ipv4_address": "ipv4NextHop",
        "next_hop_ipv6_address": "ipv6NextHop",
    }

    _COMMUNITY = {
        "type" : {
            "ixn_attr": "type",
            "enum_map": {
                "manual_as_number": "manual",
                "no_export": "noexport",
                "no_advertised": "noadvertised",
                "no_export_subconfed": "noexport_subconfed",
                "llgr_stale": "llgr_stale",
                "no_llgr": "no_llgr",
            }
        },
        "as_number": "asNumber",
        "as_custom": "lastTwoOctets"
    }

    _BGP_AS_MODE = {
        "do_not_include_local_as": "dontincludelocalas",
        "include_as_seq": "includelocalasasasseq",
        "include_as_set": "includelocalasasasset",
        "include_as_confed_seq": "includelocalasasasseqconfederation",
        "include_as_confed_set": "includelocalasasassetconfederation",
        "prepend_to_first_segment": "prependlocalastofirstsegment",
    }

    _BGP_SEG_TYPE = {
        "as_seq": "asseq",
        "as_set": "asset",
        "as_confed_seq": "asseqconfederation",
        "as_confed_set": "assetconfederation",
    }

    def __init__(self, ngpf):
        super(Bgp, self).__init__()
        self._ngpf = ngpf
        self._router_id = None

    def config(self, device):
        bgp = device.get("bgp")
        if bgp is None:
            return
        self._router_id = bgp.get("router_id")
        self._config_ipv4_interfaces(bgp)

    def _config_ipv4_interfaces(self, bgp):
        ipv4_interfaces = bgp.get("ipv4_interfaces")
        for ipv4_interface in ipv4_interfaces:
            ipv4_name = ipv4_interface.get("ipv4_name")
            ixn_ipv4 = self._ngpf._api.ixn_objects.get_object(ipv4_name)
            self._config_bgpv4(ipv4_interface.get("peers"),
                               ixn_ipv4)

    def _config_as_number(self, bgp_peer, ixn_bgp):
        as_number_width = bgp_peer.get("as_number_width")
        as_number = bgp_peer.get("as_number")
        if as_number_width == "two":
            ixn_bgp["localAs2Bytes"] = self.multivalue(as_number)
        else:
            ixn_bgp["enable4ByteAs"] = self.multivalue(True)
            ixn_bgp["localAs4Bytes"] = self.multivalue(as_number)

    def _config_bgpv4(self, bgp_peers, ixn_ipv4):
        for bgp_peer in bgp_peers:
            ixn_bgpv4 = self.create_node_elemet(
                ixn_ipv4, "bgpIpv4Peer", bgp_peer.get("name")
            )
            self._ngpf.set_device_info(bgp_peer, ixn_bgpv4, "ipv4")
            self.configure_multivalues(bgp_peer, ixn_bgpv4, Bgp._BGP)
            self._config_as_number(bgp_peer, ixn_bgpv4)
            advanced = bgp_peer.get("advanced")
            if advanced is not None:
                self.configure_multivalues(advanced, ixn_bgpv4, Bgp._ADVANCED)
            capability = bgp_peer.get("capability")
            if capability is not None:
                self.configure_multivalues(capability, ixn_bgpv4, Bgp._CAPABILITY)
            self._bgp_route_builder(bgp_peer, ixn_bgpv4)

    def _bgp_route_builder(self, bgp_peer, ixn_bgpv4):
        v4_routes = bgp_peer.get("v4_routes")
        if v4_routes is not None:
            self._configure_bgpv4_route(v4_routes, ixn_bgpv4)

        self._ngpf.compactor.compact(self._ngpf.working_dg.get(
            "networkGroup"
        ))

    def _configure_bgpv4_route(self, v4_routes, ixn_bgpv4):
        for route in v4_routes:
            addresses = route.get("addresses")
            for addresse in addresses:
                ixn_ng = self.create_node_elemet(
                    self._ngpf.working_dg, "networkGroup"
                )
                ixn_ng["multiplier"] = 1
                ixn_ip_pool = self.create_node_elemet(
                    ixn_ng, "ipv4PrefixPools", route.get("name")
                )
                ixn_connector = self.create_property(ixn_ip_pool, "connector")
                ixn_connector["connectedTo"] = self.post_calculated(
                    "connectedTo", ref_ixnobj=ixn_bgpv4
                )
                self.configure_multivalues(addresse, ixn_ip_pool, Bgp._IP_POOL)
                ixn_route = self.create_node_elemet(ixn_ip_pool, "bgpIPRouteProperty")
                self._ngpf.set_device_info(route, ixn_ip_pool)
                self._configure_route(route, ixn_route)

    def _configure_route(self, route, ixn_route):
        self.configure_multivalues(route, ixn_route, Bgp._ROUTE)

        advanced = route.get("advanced")
        if advanced is not None:
            multi_exit_discriminator = advanced.get("multi_exit_discriminator")
            if multi_exit_discriminator is not None:
                ixn_route["enableMultiExitDiscriminator"] = self.multivalue(True)
                ixn_route["multiExitDiscriminator"] = multi_exit_discriminator
            ixn_route["origin"] = self.multivalue(advanced["origin"])

        communities = route.get("communities")
        if communities is not None and len(communities) > 0:
            ixn_route["enableCommunity"] = self.multivalue(True)
            ixn_route["noOfCommunities"] = len(communities)
            for community in communities:
                ixn_community = self.create_node_elemet(
                    ixn_route, "bgpCommunitiesList"
                )
                self.configure_multivalues(community, ixn_community, Bgp._COMMUNITY)

        as_path = route.get("as_path")
        if as_path is not None:
            ixn_route["enableAsPathSegments"] = self.multivalue(True)
            ixn_route["asSetMode"] = self.multivalue(
                as_path.get("as_set_mode"), Bgp._BGP_AS_MODE
            )
            segments = as_path.get("segments")
            ixn_route["noOfASPathSegmentsPerRouteRange"] = len(segments)
            for segment in segments:
                ixn_segment = self.create_node_elemet(ixn_route, "bgpAsPathSegmentList")
                ixn_segment["segmentType"] = self.multivalue(
                    segment.get(type), Bgp._BGP_SEG_TYPE
                )
                as_numbers = segment.get("as_numbers")
                ixn_segment["numberOfAsNumberInSegment"] = len(as_numbers)
                for as_number in as_numbers:
                    ixn_as_number = self.create_node_elemet(
                        ixn_segment, "bgpAsNumberList"
                    )
                    ixn_as_number["asNumber"] = self.multivalue(as_number)
