from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger
from snappi_ixnetwork.device.bgpevpn import BgpEvpn


class Bgp(Base):
    _BGP = {
        "peer_address": "dutIp",
        "as_type": {
            "ixn_attr": "type",
            "enum_map": {"ibgp": "internal", "ebgp": "external"},
        },
    }

    _ADVANCED = {
        "hold_time_interval": "holdTimer",
        "keep_alive_interval": "keepaliveTimer",
        "update_interval": "updateInterval",
        "time_to_live": "ttl",
        "md5_key": "md5Key",
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
        "ipv4_multicast_vpn": "capabilityIpV4MulticastVpn",
        "ipv4_mpls_vpn": "capabilityIpV4MplsVpn",
        "ipv4_mdt": "capabilityIpV4Mdt",
        "ipv4_multicast_mpls_vpn": "ipv4MulticastBgpMplsVpn",
        "ipv4_unicast_flow_spec": "capabilityipv4UnicastFlowSpec",
        "ipv4_sr_te_policy": "capabilitySRTEPoliciesV4",
        "ipv4_unicast_add_path": "capabilityIpv4UnicastAddPath",
        "ipv6_multicast_vpn": "capabilityIpV6MulticastVpn",
        "ipv6_mpls_vpn": "capabilityIpV6MplsVpn",
        "ipv6_multicast_mpls_vpn": "ipv6MulticastBgpMplsVpn",
        "ipv6_unicast_flow_spec": "capabilityipv6UnicastFlowSpec",
        "ipv6_sr_te_policy": "capabilitySRTEPoliciesV6",
        "ipv6_unicast_add_path": "capabilityIpv6UnicastAddPath",
    }

    _CAPABILITY_IPv6 = {
        "extended_next_hop_encoding": "capabilityNHEncodingCapabilities",
        # "ipv6_mdt": "",
    }

    _IP_POOL = {
        "address": "networkAddress",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy",
        "step": "prefixAddrStep",
    }

    _ROUTE = {
        "next_hop_mode": {
            "ixn_attr": "nextHopType",
            "enum_map": {"local_ip": "sameaslocalip", "manual": "manually"},
        },
        "next_hop_address_type": "nextHopIPType",
        "next_hop_ipv4_address": "ipv4NextHop",
        "next_hop_ipv6_address": "ipv6NextHop",
    }

    _COMMUNITY = {
        "type": {
            "ixn_attr": "type",
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
        self.logger = get_ixnet_logger(__name__)
        self._bgp_evpn = BgpEvpn(ngpf)
        self._router_id = None

    def config(self, device):
        self.logger.debug("Configuring BGP")
        bgp = device.get("bgp")
        if bgp is None:
            return
        self._router_id = bgp.get("router_id")
        self._config_ipv4_interfaces(bgp)
        self._config_ipv6_interfaces(bgp)

    def _get_interface_info(self):
        ip_types = ["ipv4", "ipv6"]
        same_dg_ips = []
        invalid_ips = []
        ethernets = self._ngpf.working_dg.get("ethernet")
        if ethernets is None:
            return same_dg_ips, invalid_ips
        for ethernet in ethernets:
            for ip_type in ip_types:
                ips = ethernet.get(ip_type)
                if ips is not None:
                    ip_names = [ip.get("name").value for ip in ips]
                    same_dg_ips.extend(ip_names)
                    if len(ips) > 1:
                        invalid_ips.extend(ip_names)
        return same_dg_ips, invalid_ips

    def _is_valid(self, ip_name):
        is_invalid = True
        same_dg_ips, invalid_ips = self._get_interface_info()
        self.logger.debug(
            "Validating %s against interface same_dg_ips : %s invalid_ips %s"
            % (ip_name, same_dg_ips, invalid_ips)
        )
        if ip_name in invalid_ips:
            self._ngpf.api.add_error(
                "Multiple IP {name} on top of name Ethernet".format(
                    name=ip_name
                )
            )
            is_invalid = False
        if len(same_dg_ips) > 0 and ip_name not in same_dg_ips:
            self._ngpf.api.add_error(
                "BGP should not configured on top of different device"
            )
            is_invalid = False
        return is_invalid

    def _config_ipv4_interfaces(self, bgp):
        self.logger.debug("Configuring BGP IPv4 interfaces")
        ipv4_interfaces = bgp.get("ipv4_interfaces")
        if ipv4_interfaces is None:
            return
        for ipv4_interface in ipv4_interfaces:
            ipv4_name = ipv4_interface.get("ipv4_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ipv4_name
            )
            if not self._is_valid(ipv4_name):
                continue
            ixn_ipv4 = self._ngpf.api.ixn_objects.get_object(ipv4_name)
            self._config_bgpv4(ipv4_interface.get("peers"), ixn_ipv4)

    def _config_ipv6_interfaces(self, bgp):
        self.logger.debug("Configuring BGP IPv6 interfaces")
        ipv6_interfaces = bgp.get("ipv6_interfaces")
        if ipv6_interfaces is None:
            return
        for ipv6_interface in ipv6_interfaces:
            ipv6_name = ipv6_interface.get("ipv6_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ipv6_name
            )
            if not self._is_valid(ipv6_name):
                continue
            ixn_ipv6 = self._ngpf.api.ixn_objects.get_object(ipv6_name)
            self._config_bgpv6(ipv6_interface.get("peers"), ixn_ipv6)

    def _config_as_number(self, bgp_peer, ixn_bgp):
        as_number_width = bgp_peer.get("as_number_width")
        as_number = bgp_peer.get("as_number")
        if as_number_width == "two":
            ixn_bgp["localAs2Bytes"] = self.multivalue(as_number)
        else:
            ixn_bgp["enable4ByteAs"] = self.multivalue(True)
            ixn_bgp["localAs4Bytes"] = self.multivalue(as_number)

    def _config_bgpv4(self, bgp_peers, ixn_ipv4):
        if bgp_peers is None:
            return
        self.logger.debug("Configuring BGPv4 Peer")
        for bgp_peer in bgp_peers:
            ixn_bgpv4 = self.create_node_elemet(
                ixn_ipv4, "bgpIpv4Peer", bgp_peer.get("name")
            )
            self._ngpf.set_device_info(bgp_peer, ixn_bgpv4)
            self.configure_multivalues(bgp_peer, ixn_bgpv4, Bgp._BGP)
            self._config_as_number(bgp_peer, ixn_bgpv4)
            advanced = bgp_peer.get("advanced")
            if advanced is not None:
                self.configure_multivalues(advanced, ixn_bgpv4, Bgp._ADVANCED)
            capability = bgp_peer.get("capability")
            if capability is not None:
                self.configure_multivalues(
                    capability, ixn_bgpv4, Bgp._CAPABILITY
                )
            self._bgp_route_builder(bgp_peer, ixn_bgpv4)
            self._bgp_evpn.config(bgp_peer, ixn_bgpv4)

    def _config_bgpv6(self, bgp_peers, ixn_ipv6):
        self.logger.debug("Configuring BGPv6 Peer")
        if bgp_peers is None:
            return
        for bgp_peer in bgp_peers:
            ixn_bgpv6 = self.create_node_elemet(
                ixn_ipv6, "bgpIpv6Peer", bgp_peer.get("name")
            )
            self._ngpf.set_device_info(bgp_peer, ixn_bgpv6)
            self.configure_multivalues(bgp_peer, ixn_bgpv6, Bgp._BGP)
            self._config_as_number(bgp_peer, ixn_bgpv6)
            advanced = bgp_peer.get("advanced")
            if advanced is not None:
                self.configure_multivalues(advanced, ixn_bgpv6, Bgp._ADVANCED)
            capability = bgp_peer.get("capability")
            if capability is not None:
                self.configure_multivalues(
                    capability, ixn_bgpv6, Bgp._CAPABILITY
                )
                self.configure_multivalues(
                    capability, ixn_bgpv6, Bgp._CAPABILITY_IPv6
                )
            self._bgp_route_builder(bgp_peer, ixn_bgpv6)
            self._bgp_evpn.config(bgp_peer, ixn_bgpv6)

    def _bgp_route_builder(self, bgp_peer, ixn_bgp):
        v4_routes = bgp_peer.get("v4_routes")
        if v4_routes is not None:
            self._configure_bgpv4_route(v4_routes, ixn_bgp)
        v6_routes = bgp_peer.get("v6_routes")
        if v6_routes is not None:
            self._configure_bgpv6_route(v6_routes, ixn_bgp)
        self._ngpf.compactor.compact(self._ngpf.working_dg.get("networkGroup"))

    def _configure_bgpv4_route(self, v4_routes, ixn_bgp):
        if v4_routes is None:
            return
        self.logger.debug("Configuring BGPv4 Route")
        for route in v4_routes:
            addresses = route.get("addresses")
            for addresse in addresses:
                ixn_ng = self.create_node_elemet(
                    self._ngpf.working_dg, "networkGroup", route.get("name")
                )
                ixn_ng["multiplier"] = 1
                ixn_ip_pool = self.create_node_elemet(
                    ixn_ng, "ipv4PrefixPools", route.get("name")
                )
                ixn_connector = self.create_property(ixn_ip_pool, "connector")
                ixn_connector["connectedTo"] = self.post_calculated(
                    "connectedTo", ref_ixnobj=ixn_bgp
                )
                self.configure_multivalues(addresse, ixn_ip_pool, Bgp._IP_POOL)
                ixn_route = self.create_node_elemet(
                    ixn_ip_pool, "bgpIPRouteProperty", route.get("name")
                )
                self._ngpf.set_device_info(route, ixn_ip_pool)
                self._configure_route(route, ixn_route)

    def _configure_bgpv6_route(self, v6_routes, ixn_bgp):
        if v6_routes is None:
            return
        self.logger.debug("Configuring BGPv6 Route")
        for route in v6_routes:
            addresses = route.get("addresses")
            for addresse in addresses:
                ixn_ng = self.create_node_elemet(
                    self._ngpf.working_dg, "networkGroup"
                )
                ixn_ng["multiplier"] = 1
                ixn_ip_pool = self.create_node_elemet(
                    ixn_ng, "ipv6PrefixPools", route.get("name")
                )
                ixn_connector = self.create_property(ixn_ip_pool, "connector")
                ixn_connector["connectedTo"] = self.post_calculated(
                    "connectedTo", ref_ixnobj=ixn_bgp
                )
                self.configure_multivalues(addresse, ixn_ip_pool, Bgp._IP_POOL)
                ixn_route = self.create_node_elemet(
                    ixn_ip_pool, "bgpV6IPRouteProperty"
                )
                self._ngpf.set_device_info(route, ixn_ip_pool)
                self._configure_route(route, ixn_route)

    def _configure_route(self, route, ixn_route):
        self._ngpf.set_ixn_routes(route, ixn_route)
        self.configure_multivalues(route, ixn_route, Bgp._ROUTE)

        advanced = route.get("advanced")
        if advanced is not None:
            self.logger.debug("Configuring BGP route advance")
            multi_exit_discriminator = advanced.get("multi_exit_discriminator")
            if multi_exit_discriminator is not None:
                ixn_route["enableMultiExitDiscriminator"] = self.multivalue(
                    True
                )
                ixn_route["multiExitDiscriminator"] = self.multivalue(
                    multi_exit_discriminator
                )
            ixn_route["origin"] = self.multivalue(advanced.get("origin"))

        communities = route.get("communities")
        if communities is not None and len(communities) > 0:
            self.logger.debug("Configuring BGP route community")
            ixn_route["enableCommunity"] = self.multivalue(True)
            ixn_route["noOfCommunities"] = len(communities)
            for community in communities:
                ixn_community = self.create_node_elemet(
                    ixn_route, "bgpCommunitiesList"
                )
                self.configure_multivalues(
                    community, ixn_community, Bgp._COMMUNITY
                )

        as_path = route.get("as_path")
        if as_path is not None:
            self.logger.debug("Configuring BGP route AS path")
            ixn_route["enableAsPathSegments"] = self.multivalue(True)
            ixn_route["asSetMode"] = self.multivalue(
                as_path.get("as_set_mode"), Bgp._BGP_AS_MODE
            )
            segments = as_path.get("segments")
            ixn_route["noOfASPathSegmentsPerRouteRange"] = len(segments)
            for segment in segments:
                ixn_segment = self.create_node_elemet(
                    ixn_route, "bgpAsPathSegmentList"
                )
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
