import time

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

    # OTG learned_information_filter → IxNetwork filterIpV*/filterIpV* Multivalue.
    # Enabling a filter instructs IxNetwork to capture that route family in
    # learnedInfo.  Without at least one filter set to True the server stores
    # nothing and GetIPv4/6LearnedInfo returns empty results.
    _LEARNED_INFO_FILTER = {
        "unicast_ipv4_prefix": "filterIpV4Unicast",
        "unicast_ipv6_prefix": "filterIpV6Unicast",
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
            lif = bgp_peer.get("learned_information_filter")
            if lif is not None:
                self.configure_multivalues(
                    lif, ixn_bgpv4, Bgp._LEARNED_INFO_FILTER
                )

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
            lif = bgp_peer.get("learned_information_filter")
            if lif is not None:
                self.configure_multivalues(
                    lif, ixn_bgpv6, Bgp._LEARNED_INFO_FILTER
                )

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
                    self._ngpf.working_dg, "networkGroup", route.get("name")
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
                    ixn_ip_pool, "bgpV6IPRouteProperty", route.get("name")
                )
                self._ngpf.set_device_info(route, ixn_ip_pool)
                self._configure_route(route, ixn_route)

    # ------------------------------------------------------------------
    # Learned-info helpers (used by ngpf.get_bgp_prefix_states)
    # ------------------------------------------------------------------

    # IxNetwork single-char origin → OTG origin string
    _IXN_ORIGIN_MAP = {
        "i": "igp",
        "e": "egp",
        "?": "incomplete",
        # accept long-form in case a future IxN version emits them
        "igp": "igp",
        "egp": "egp",
        "incomplete": "incomplete",
    }

    # Column-name aliases tried in order (first hit wins).  IxNetwork has
    # varied slightly across versions; this covers the known variants.
    _V4_ADDR_COLS    = ("IPv4 Prefix",)
    _V6_ADDR_COLS    = ("IPv6 Address", "IPv6 Prefix", "IP Address", "Network Address", "Network")
    _NLRI_COLS       = ("Prefix Length",)
    _NH_COLS         = ("Next Hop",    "NextHop",   "Next-Hop")
    _V4_NH_COLS      = ("IPv4 Next Hop",)
    _V6_NH_COLS      = ("Ipv6 Next Hop",)
    _ORIGIN_COLS     = ("Origin",)
    _LOCPREF_COLS    = ("Local Preference", "Local Pref", "LocalPref")
    _MED_COLS        = ("MED",         "Multi Exit Discriminator")
    _ASPATH_COLS     = ("AS Path",     "AS-Path",   "AsPath")
    _COMMUNITY_COLS  = ("Community",   "Communities")
    _PATHID_COLS     = ("Path ID",     "PathId",    "Add Path ID")

    def get_bgp_peer_objects(self, peer_names):
        """Return a list of ``(peer_name, restpy_peer_obj, session_index,
        family)`` for every BGP peer that matches *peer_names*.

        Parameters
        ----------
        peer_names : list[str]
            Snappi peer names to query.  An empty list means *all* configured
            BGP peers.

        Returns
        -------
        list of (str, restpy_obj, int, str)
            *session_index* is 1-based (as required by
            ``GetIPv4/6LearnedInfo``).  *family* is ``"v4"`` or ``"v6"``.

        Raises
        ------
        Exception
            If any name in *peer_names* is not found in the live topology.
        """
        requested = set(peer_names) if peer_names else None
        ixn_object_names = set(self._ngpf.api.ixn_objects.names)
        results = []

        topologies = self._ngpf.api._ixnetwork.Topology.find()
        dg_chain = topologies.DeviceGroup.find().Ethernet.find()

        try:
            bgpv4_peers = dg_chain.Ipv4.find().BgpIpv4Peer.find()
        except Exception:
            # No IPv4 interfaces in the current topology (e.g. IPv6-only test).
            bgpv4_peers = []

        try:
            bgpv6_peers = dg_chain.Ipv6.find().BgpIpv6Peer.find()
        except Exception:
            # No IPv6 interfaces in the current topology (e.g. IPv4-only test).
            bgpv6_peers = []

        for peer_obj in bgpv4_peers:
            self._collect_peer_entries(
                peer_obj, "v4", requested, ixn_object_names, results
            )
        for peer_obj in bgpv6_peers:
            self._collect_peer_entries(
                peer_obj, "v6", requested, ixn_object_names, results
            )

        if requested:
            found = {r[0] for r in results}
            missing = sorted(requested - found)
            if missing:
                raise Exception(
                    "BGP peer(s) not found in topology: %s" % missing
                )
        return results

    def _collect_peer_entries(
        self, peer_obj, family, requested, ixn_object_names, results
    ):
        """Append ``(name, peer_obj, session_idx, family)`` to *results*.

        Handles both non-compacted (single-session) and compacted
        (multi-session scalable) peers.  For compacted peers the
        ``ixn_objects`` entry for the root name carries the full ``names``
        list; each name's 0-based position in that list is its session
        index.  *session_idx* is 1-based.
        """
        root_name = peer_obj.Name
        if root_name not in ixn_object_names:
            return
        ixn_info = self._ngpf.api.ixn_objects.get(root_name)
        # Non-compacted peers have names=[]; treat root_name as the sole entry.
        names = ixn_info.names if ixn_info.names else [root_name]
        for idx, name in enumerate(names):
            if name is None or name not in ixn_object_names:
                continue
            if requested is not None and name not in requested:
                continue
            results.append((name, peer_obj, idx + 1, family))

    def _get_learned_table(self, peer_obj, session_index, family):
        """Trigger learned-info fetch and return rows as column-keyed dicts.

        Implements the RestPy pattern from the official IxNetwork sample
        ``samples/protocols/bgp_learned_info.py``::

            bgp.GetAllLearnedInfo()
            learned_info_table = bgp.LearnedInfo.find().Table.find()

        ``GetAllLearnedInfo`` (not ``GetIPv4/6LearnedInfo``) is the operation
        that populates the ``Table`` child resource.  ``GetIPv4/6LearnedInfo``
        only updates the deprecated inline ``Columns``/``Values`` fields which
        are no longer written in IxNetwork 10.x.

        Parameters
        ----------
        peer_obj :
            Live RestPy ``bgpIpv4Peer`` or ``bgpIpv6Peer`` object.
        session_index : int
            Informational; the trigger covers all sessions on *peer_obj*.
        family : str
            ``"v4"`` or ``"v6"``.

        Returns
        -------
        list[dict[str, str]]
            One ``{column_name: value_str}`` dict per prefix row.
        """
        # --- Step 1: trigger the learned-info fetch -----------------------
        # Equivalent to right-click → "Get Learned Info" in the GUI.
        try:
            peer_obj.GetAllLearnedInfo()
        except Exception as e:
            self.logger.warning(
                "GetAllLearnedInfo failed for peer %r: %s"
                % (peer_obj.Name, e)
            )
            return []

        # --- Step 2: read LearnedInfo.find().Table.find() -----------------
        rows = []
        try:
            for li in peer_obj.LearnedInfo.find():
                for table in li.Table.find():
                    columns = table.Columns
                    if not columns:
                        continue
                    # self.logger.warning(
                    #     "_get_learned_table: peer=%r Type=%r "
                    #     "Columns=%r RowCount=%d"
                    #     % (peer_obj.Name, table.Type,
                    #        columns, len(table.Values or []))
                    # )
                    col_idx = {col.strip(): i for i, col in enumerate(columns)}
                    for row_vals in (table.Values or []):
                        rows.append({
                            col: row_vals[i]
                            for col, i in col_idx.items()
                            if i < len(row_vals)
                        })
        except Exception as e:
            self.logger.warning(
                "_get_learned_table: Table.find() failed for peer %r: %s"
                % (peer_obj.Name, e)
            )
        return rows

    # --- static low-level helpers ------------------------------------

    @staticmethod
    def _get_cell(row, *col_names):
        """Return the stripped value of the first matching column in *row*,
        or ``None`` if none of the candidate column names are present."""
        for name in col_names:
            val = row.get(name)
            if val is not None:
                return val.strip()
        return None

    @staticmethod
    def _safe_int(s, default=0):
        """Convert *s* to ``int``; return *default* on failure."""
        try:
            return int(s)
        except (TypeError, ValueError):
            return default

    # --- AS-path / community parsers ---------------------------------

    def _parse_as_path(self, cell):
        """Convert an IxNetwork AS-path string to an OTG ``as_path`` dict.

        Supported input formats::

            "100 200 300"      → single AS_SEQ segment
            "{100 200} 300"    → AS_SET [100,200] then AS_SEQ [300]
            "(100 200)"        → AS_CONFED_SEQ segment
            "[100 200]"        → AS_CONFED_SET segment
            ""  / "N/A" / "0"  → empty segments list
        """
        if not cell or cell.strip().lower() in ("", "n/a", "0"):
            return {"segments": []}

        segments = []
        seq_buf = []   # accumulates plain ASNs for the current AS_SEQ

        def _flush_seq():
            if seq_buf:
                segments.append({"type": "as_seq",
                                  "as_numbers": list(seq_buf)})
                seq_buf.clear()

        i = 0
        token = cell.strip()
        while i < len(token):
            ch = token[i]
            if ch in ("{", "(", "[", "<"):
                close = {"{": "}",
                         "(": ")",
                         "[": "]",
                         "<": ">"}[ch]
                seg_type = {"{": "as_set",
                            "(": "as_confed_seq",
                            "[": "as_confed_set",
                            "<": "as_seq"}[ch]
                _flush_seq()
                end = token.find(close, i + 1)
                inner = token[i + 1 : end if end != -1 else len(token)]
                asns = [int(x) for x in inner.split() if x.isdigit()]
                segments.append({"type": seg_type, "as_numbers": asns})
                i = (end + 1) if end != -1 else len(token)
            else:
                # Collect plain ASNs up to the next group delimiter
                next_group = len(token)
                for delim in ("{", "(", "[", "<"):
                    pos = token.find(delim, i)
                    if pos != -1 and pos < next_group:
                        next_group = pos
                for part in token[i:next_group].split():
                    if part.isdigit():
                        seq_buf.append(int(part))
                i = next_group

        _flush_seq()
        return {"segments": segments}

    def _parse_communities(self, cell):
        """Convert an IxNetwork communities string to a list of OTG dicts.

        Handled formats::

            "1:2 3:4"      → two ``manual_as_number`` entries
            "no-export"    → ``no_export`` well-known entry
            "no-advertise" → ``no_advertised`` well-known entry
            "" / "N/A"     → empty list
        """
        if not cell or cell.strip().lower() in ("", "n/a"):
            return []

        # IxNetwork sometimes emits spaces around the colon, e.g. "1 : 2".
        # Normalise to "1:2" before tokenising.
        import re
        cell = re.sub(r'\s*:\s*', ':', cell)

        _WELL_KNOWN = {
            "no-export": "no_export",
            "noexport": "no_export",
            "no-advertise": "no_advertised",
            "noadvertise": "no_advertised",
            "no-advertised": "no_advertised",
            "no_export_subconfed": "no_export_subconfed",
            "no-export-subconfed": "no_export_subconfed",
            "llgr_stale": "llgr_stale",
            "no_llgr": "no_llgr",
        }

        result = []
        for token in cell.split():
            lower = token.lower()
            if lower in _WELL_KNOWN:
                result.append({"type": _WELL_KNOWN[lower]})
            elif ":" in token:
                parts = token.split(":", 1)
                try:
                    result.append({
                        "type": "manual_as_number",
                        "as_number": int(parts[0]),
                        "as_custom": int(parts[1]),
                    })
                except (ValueError, IndexError):
                    self.logger.warning(
                        "1. Skipping unrecognised community token: %s" % token
                    )
            else:
                self.logger.warning(
                    "2. Skipping unrecognised community token: %s" % token
                )
        return result

    # --- row → OTG prefix dict ---------------------------------------

    def _row_to_ipv4_prefix(self, row):
        """Convert a raw IxNetwork row dict to an OTG IPv4 unicast prefix dict.

        Returns ``None`` when the row lacks address information (e.g. it
        belongs to a different table type such as IPv4 MPLS).
        """
        addr_cell = self._get_cell(row, *self._V4_ADDR_COLS)
        nlri_cell = self._get_cell(row, *self._NLRI_COLS)

        if not addr_cell:
            return None

        # Some IxN versions emit a full CIDR in the address column.
        if "/" in addr_cell:
            parts = addr_cell.split("/", 1)
            ipv4_address = parts[0]
            prefix_length = self._safe_int(parts[1])
        else:
            ipv4_address = addr_cell
            prefix_length = self._safe_int(nlri_cell)

        ipv4_nh = self._get_cell(row, *self._V4_NH_COLS) or None
        ipv6_nh = self._get_cell(row, *self._V6_NH_COLS) or None
        # Fall back to legacy single next-hop column, using ":" to distinguish.
        if ipv4_nh is None and ipv6_nh is None:
            nh_cell = self._get_cell(row, *self._NH_COLS) or ""
            ipv4_nh = nh_cell if nh_cell and ":" not in nh_cell else None
            ipv6_nh = nh_cell if ":" in nh_cell else None

        origin_raw = self._get_cell(row, *self._ORIGIN_COLS) or ""
        origin = self._IXN_ORIGIN_MAP.get(origin_raw.lower())

        prefix = {
            "ipv4_address": ipv4_address,
            "prefix_length": prefix_length,
            "as_path": self._parse_as_path(
                self._get_cell(row, *self._ASPATH_COLS)
            ),
            "communities": self._parse_communities(
                self._get_cell(row, *self._COMMUNITY_COLS)
            ),
        }
        if origin:
            prefix["origin"] = origin
        if ipv4_nh:
            prefix["ipv4_next_hop"] = ipv4_nh
        if ipv6_nh:
            prefix["ipv6_next_hop"] = ipv6_nh

        locpref_val = self._get_cell(row, *self._LOCPREF_COLS)
        if locpref_val not in (None, "", "N/A"):
            prefix["local_preference"] = self._safe_int(locpref_val)

        med_val = self._get_cell(row, *self._MED_COLS)
        if med_val not in (None, "", "N/A"):
            prefix["multi_exit_discriminator"] = self._safe_int(med_val)

        pid_val = self._get_cell(row, *self._PATHID_COLS)
        if pid_val not in (None, "", "N/A", "0"):
            prefix["path_id"] = self._safe_int(pid_val)

        return prefix

    def _row_to_ipv6_prefix(self, row):
        """Convert a raw IxNetwork row dict to an OTG IPv6 unicast prefix dict.

        Returns ``None`` when the row lacks address information.
        """
        addr_cell = self._get_cell(row, *self._V6_ADDR_COLS)
        nlri_cell = self._get_cell(row, *self._NLRI_COLS)

        if not addr_cell:
            return None

        if "/" in addr_cell:
            parts = addr_cell.split("/", 1)
            ipv6_address  = parts[0]
            prefix_length = self._safe_int(parts[1])
        else:
            ipv6_address  = addr_cell
            prefix_length = self._safe_int(nlri_cell)

        nh_cell = self._get_cell(row, *self._NH_COLS) or ""
        ipv6_nh = nh_cell if ":" in nh_cell else None
        ipv4_nh = nh_cell if ":" not in nh_cell and nh_cell else None

        origin_raw = self._get_cell(row, *self._ORIGIN_COLS) or ""
        origin = self._IXN_ORIGIN_MAP.get(origin_raw.lower())

        prefix = {
            "ipv6_address"  : ipv6_address,
            "prefix_length" : prefix_length,
            "as_path"       : self._parse_as_path(
                self._get_cell(row, *self._ASPATH_COLS)
            ),
            "communities"   : self._parse_communities(
                self._get_cell(row, *self._COMMUNITY_COLS)
            ),
        }
        if origin:
            prefix["origin"] = origin
        if ipv6_nh:
            prefix["ipv6_next_hop"] = ipv6_nh
        if ipv4_nh:
            prefix["ipv4_next_hop"] = ipv4_nh

        locpref_val = self._get_cell(row, *self._LOCPREF_COLS)
        if locpref_val not in (None, "", "N/A"):
            prefix["local_preference"] = self._safe_int(locpref_val)

        med_val = self._get_cell(row, *self._MED_COLS)
        if med_val not in (None, "", "N/A"):
            prefix["multi_exit_discriminator"] = self._safe_int(med_val)

        pid_val = self._get_cell(row, *self._PATHID_COLS)
        if pid_val not in (None, "", "N/A", "0"):
            prefix["path_id"] = self._safe_int(pid_val)

        return prefix

    # --- filter application ------------------------------------------

    @staticmethod
    def _prefix_matches_filter(prefix, filt, addr_key):
        """Return True if *prefix* satisfies all non-None fields of *filt*.

        Missing / None filter fields are treated as wildcards (match all).
        """
        addresses = filt.addresses
        if addresses:
            if prefix.get(addr_key) not in addresses:
                return False

        prefix_length = filt.prefix_length
        if prefix_length is not None:
            if prefix.get("prefix_length") != prefix_length:
                return False

        origin = filt.origin
        if origin is not None:
            if prefix.get("origin") != origin:
                return False

        path_id = filt.path_id
        if path_id is not None:
            if prefix.get("path_id", 0) != path_id:
                return False

        return True

    def _apply_v4_filters(self, prefixes, filters):
        """Return prefixes that match at least one IPv4 unicast filter.

        An empty *filters* list (or ``None``) means no restriction: all
        prefixes are returned.  Multiple filters are OR-ed; within each
        filter, fields are AND-ed.
        """
        if not filters:
            return prefixes
        return [
            p for p in prefixes
            if any(
                self._prefix_matches_filter(p, f, "ipv4_address")
                for f in filters
            )
        ]

    def _apply_v6_filters(self, prefixes, filters):
        """Return prefixes that match at least one IPv6 unicast filter.

        Semantics identical to :meth:`_apply_v4_filters`.
        """
        if not filters:
            return prefixes
        return [
            p for p in prefixes
            if any(
                self._prefix_matches_filter(p, f, "ipv6_address")
                for f in filters
            )
        ]

    # --- public orchestrator -----------------------------------------

    def get_learned_prefixes(self, peer_obj, session_index, family,
                             bgp_prefix_request):
        """Fetch and translate learned prefixes for one peer session.

        Calls :meth:`_get_learned_table` to retrieve raw IxNetwork rows,
        converts each row to an OTG prefix dict, then applies any
        unicast filters present in *bgp_prefix_request*.

        Parameters
        ----------
        peer_obj :
            Live RestPy ``bgpIpv4Peer`` or ``bgpIpv6Peer`` object.
        session_index : int
            1-based session index (from :meth:`get_bgp_peer_objects`).
        family : str
            ``"v4"`` or ``"v6"``.
        bgp_prefix_request :
            Snappi ``BgpPrefixStateRequest`` (``request.bgp_prefixes``).
            May be ``None`` when called without filter context.

        Returns
        -------
        list[dict]
            OTG-shaped prefix dicts ready for serialisation into
            ``BgpPrefixIpv4/6UnicastState``.
        """
        rows = self._get_learned_table(peer_obj, session_index, family)

        if family == "v4":
            prefixes = [
                p for p in (self._row_to_ipv4_prefix(r) for r in rows)
                if p is not None
            ]
            filters = (
                bgp_prefix_request.ipv4_unicast_filters
                if bgp_prefix_request is not None
                else None
            )
            return self._apply_v4_filters(prefixes, filters)
        else:
            prefixes = [
                p for p in (self._row_to_ipv6_prefix(r) for r in rows)
                if p is not None
            ]
            filters = (
                bgp_prefix_request.ipv6_unicast_filters
                if bgp_prefix_request is not None
                else None
            )
            return self._apply_v6_filters(prefixes, filters)

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
                    segment.get("type"), Bgp._BGP_SEG_TYPE
                )
                as_numbers = segment.get("as_numbers")
                ixn_segment["numberOfAsNumberInSegment"] = len(as_numbers)
                for as_number in as_numbers:
                    ixn_as_number = self.create_node_elemet(
                        ixn_segment, "bgpAsNumberList"
                    )
                    ixn_as_number["asNumber"] = self.multivalue(as_number)
