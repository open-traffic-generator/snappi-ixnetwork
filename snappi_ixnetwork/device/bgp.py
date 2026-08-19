import re
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
        # get_learned_prefixes call by _warn_missing_column's caller.
        self._warned_columns = set()

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

    # ------------------------------------------------------------------
    # Learned-info column names
    # ------------------------------------------------------------------
    # The keys below are IxNetwork column *display names*.  RestPy exposes
    # no `name` attribute for learned-info columns: in ixnetwork_restpy
    # 1.10.0 the `learnedInfo/table` resource's _SDM_ATT_MAP is only
    # {Actions, Columns, RowCount, Type, Values}, `learnedInfo` itself adds
    # only Id__/State, and the deprecated `col` child carries just `value`.
    # `columns` holds the display names, so keying off the display name is
    # the only option the API offers.
    # Notes :
    #   * 'IPv4 Prefix ' carries a trailing space.  _get_learned_table()
    #     strips every column name, so the constants here are unpadded.
    #   * an absent value arrives as 'NA', 'removePacket[ ]' or
    #     'removePacket[N/A]' -- never a bare 'N/A'.  All are normalised to
    #     None by _get_cell; 'removePacket' is matched by prefix because
    #     the bracketed part varies (_NA_VALUE_PREFIXES).
    #   * 'AIGP', 'Color', 'Large Community', 'SRv6 SID' and the locator
    #     columns have no OTG counterpart and are deliberately unmapped.
    #   * 'IPv6 Next Hop 2' is a second next-hop, not an alias of
    #     'IPv6 Next Hop'; OTG has no field for it.
    #   * this table has no extended-community column.
    # A tuple with more than one entry is an ordered candidate list
    # (first hit wins).  Keep these tuples minimal: every extra entry is
    # a guess that hides a schema change instead of surfacing it.
    #
    # The IPv6 unicast table has not been captured yet -- entries tagged
    # UNCONFIRMED are inferred from the IPv4 naming pattern above.
    _V4_ADDR_COLS = ("IPv4 Prefix",)
    _V6_ADDR_COLS = ("IPv6 Prefix",)
    _NLRI_COLS = ("Prefix Length",)
    _V4_NH_COLS = ("IPv4 Next Hop",)
    _V6_NH_COLS = ("IPv6 Next Hop",)
    # Legacy single next-hop column, used only as a fallback when neither
    # explicit per-family column is present.  Not seen in 10.80.
    _NH_COLS = ("Next Hop",)
    _ORIGIN_COLS = ("Origin",)
    _LOCPREF_COLS = ("Local Preference",)
    _MED_COLS = ("MED",)
    _ASPATH_COLS = ("AS Path",)
    _COMMUNITY_COLS = ("Community",)
    _PATHID_COLS = ("Path ID",)

    # Cell values that mean "no value" rather than data.  Compared
    # case-insensitively against the stripped cell; 'removePacket[...]'
    # is matched by prefix because the bracketed part varies.
    _NA_VALUES = frozenset(("", "na", "n/a", "null", "none"))
    _NA_VALUE_PREFIXES = ("removepacket",)

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

        Limitations
        -----------
        Peers are found by walking the live NGPF tree rather than by looking
        them up by name, which has three known consequences.  The same walk
        is used by the ``ipv4_neighbors``/``ipv6_neighbors`` branches of
        :meth:`Ngpf.get_states`, so these apply there too.

        * **Cost grows with the topology.** The walk runs on every call and
          nothing is cached between calls (the topology may have changed),
          so a configuration with very many device groups pays for a full
          traversal each time.
        * **Only top-level device groups are searched.**
          ``DeviceGroup.find()`` returns the groups directly beneath the
          topology, not their children, so a peer in a nested ("chained")
          device group is not found.
        * **Only Ethernet-backed interfaces are searched.** The chain is
          ``DeviceGroup -> Ethernet -> Ipv4/Ipv6 -> BgpIpv4Peer/BgpIpv6Peer``,
          so a peer configured on a loopback is not found.  This is not
          hypothetical: :class:`LoopbackInt` places each loopback in a
          *child* device group and attaches it as ``ipv4Loopback`` /
          ``ipv6Loopback`` (or, for a VXLAN source interface, as
          ``ethernet/ipv4`` inside that child group), so both limitations
          above apply to it at once.

        In each of those cases a requested peer name is reported as
        "BGP peer(s) not found in topology", which does not distinguish an
        unsupported topology from a mistyped name.

        The robust fix is to stop searching and look the peer up directly:
        ``ixn_objects`` already maps every snappi name to an ``IxNetInfo``
        carrying ``.xpath``/``.href``, and the object type is the trailing
        xpath segment (``.../ipv4[1]/bgpIpv4Peer[1]``), so filtering to
        ``bgpIpv4Peer``/``bgpIpv6Peer`` needs no new capability in
        :class:`IxNetObjects`.  That belongs in a follow-up which also
        converts the two neighbor paths, so all three share one lookup
        helper instead of three hand-rolled traversals.
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
            One ``{column_display_name: value_str}`` dict per prefix row.
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
                    self.logger.debug(
                        "_get_learned_table: peer=%r Type=%r Columns=%r "
                        "RowCount=%d"
                        % (
                            peer_obj.Name,
                            table.Type,
                            columns,
                            len(table.Values or []),
                        )
                    )
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

    def _is_na(self, value):
        """Return True if *value* is an IxNetwork "no value" placeholder.

        IxNetwork does not leave absent cells empty; it emits ``NA`` or
        ``removePacket[ ]`` (the bracketed part varies).  Treating those as
        data yields nonsense such as ``path_id=0`` from ``'NA'`` or an
        ``ipv6_next_hop`` of ``'removePacket[ ]'``.
        """
        lowered = value.lower()
        if lowered in self._NA_VALUES:
            return True
        return lowered.startswith(self._NA_VALUE_PREFIXES)

    def _get_cell(self, row, *col_names, **kwargs):
        """Return the value of the first matching column in *row*.

        Candidate names are IxNetwork column *display names* -- RestPy
        exposes no ``name`` attribute for learned-info columns, so the
        display name is the only key available (see the note above the
        ``_*_COLS`` constants).  Names are matched against the already
        stripped keys built by :meth:`_get_learned_table`.

        Returns ``None`` when no candidate column is present, and also
        when the matched cell holds a "no value" placeholder such as
        ``NA`` or ``removePacket[ ]`` (see :meth:`_is_na`).

        Keyword Arguments
        -----------------
        warn : bool, default True
            Log a warning when none of *col_names* is present in *row*, so
            that a renamed or removed column surfaces in the log instead of
            silently producing an incomplete prefix.  Pass ``warn=False``
            for probes that legitimately expect a miss -- the address
            columns are used to decide whether a row belongs to this
            address family at all.
        """
        warn = kwargs.pop("warn", True)
        if kwargs:
            raise TypeError(
                "_get_cell got unexpected keyword arguments: %s"
                % sorted(kwargs)
            )
        for name in col_names:
            val = row.get(name)
            if val is not None:
                val = val.strip()
                return None if self._is_na(val) else val
        if warn:
            self._warn_missing_column(col_names, row)
        return None

    def _warn_missing_column(self, col_names, row):
        """Warn once per candidate-column set that no candidate matched.

        Deduplicated for the lifetime of one
        :meth:`get_learned_prefixes` call so that a missing column costs
        one log line rather than one per learned prefix.
        """
        if col_names in self._warned_columns:
            return
        self._warned_columns.add(col_names)
        self.logger.warning(
            "Learned-info column not found: tried %s. Available columns: "
            "%s. The corresponding field will be omitted from the "
            "returned prefixes -- the IxNetwork column display name may "
            "have changed." % (list(col_names), sorted(row))
        )

    @staticmethod
    def _safe_int(s, default=0):
        """Convert *s* to ``int``; return *default* on failure."""
        try:
            return int(s)
        except (TypeError, ValueError):
            return default

    # --- AS-path / community parsers ---------------------------------

    # AS numbers are uint32 in OTG (``as_numbers`` itemformat).  Community
    # ``as_number``/``as_custom`` are each capped at 65535 by the OTG
    # model, and snappi raises at serialisation time for anything larger,
    # so an out-of-range parse would fail the whole get_states call.
    _MAX_ASN = 2 ** 32 - 1
    _MAX_COMMUNITY_FIELD = 65535

    _ASDOT_RE = re.compile(r"^\d+\.\d+$")

    # Members within an AS-path group are separated by whitespace, commas
    # or both: 10.80 emits AS_SEQ as '<100 200>' but AS_SET as '{300,400}'.
    # The same splitter is reused for the comma-separated community list.
    _ASN_SEPARATOR_RE = re.compile(r"[,\s]+")

    # Well-known community names → OTG type.  Keys are the *normalised*
    # form: lower-cased with '-' folded to '_', because IxNetwork has been
    # observed emitting both 'no-export' and the uppercase 'NO_EXPORT'.
    _WELL_KNOWN_COMMUNITIES = {
        "no_export": "no_export",
        "noexport": "no_export",
        "no_advertise": "no_advertised",
        "noadvertise": "no_advertised",
        "no_advertised": "no_advertised",
        "no_export_subconfed": "no_export_subconfed",
        "noexport_subconfed": "no_export_subconfed",
        "llgr_stale": "llgr_stale",
        "no_llgr": "no_llgr",
    }

    def _parse_asn_list(self, text):
        """Parse comma- and/or whitespace-separated AS numbers from *text*.

        Anything that is not a plain (asplain) uint32 is skipped **with a
        warning** rather than dropped silently -- a silent drop turns a
        format surprise into a wrong AS path, which is exactly the kind of
        result these states are used to assert on.
        """
        asns = []
        for token in self._ASN_SEPARATOR_RE.split(text.strip()):
            if not token:
                continue
            if token.isdigit():
                value = int(token)
                if value <= self._MAX_ASN:
                    asns.append(value)
                    continue
                self.logger.warning(
                    "Skipping AS number %s in learned AS path: exceeds the "
                    "uint32 maximum (%d)." % (token, self._MAX_ASN)
                )
                continue
            self._warn_bad_asn(token)
        return asns

    def _warn_bad_asn(self, token):
        """Warn about an AS-path token that is not an asplain AS number."""
        hint = ""
        if self._ASDOT_RE.match(token):
            # Deliberate non-support: IxNetwork 10.80 emits asplain
            # ('<100 200>') and neither bgpIpv4Peer nor anything else in
            # ixnetwork_restpy 1.10.0 exposes an asdot notation setting.
            # Guessing at a format we have never observed is what made the
            # learned-info column aliases wrong; if this warning ever
            # fires, implement the conversion (X.Y = X * 65536 + Y) here.
            hint = (
                " This looks like asdot notation; asdot is not parsed "
                "because IxNetwork has only ever been observed emitting "
                "asplain. Convert as X.Y = X * 65536 + Y if needed."
            )
        self.logger.warning(
            "Skipping unparseable AS number %r in learned AS path.%s"
            % (token, hint)
        )

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
                asns = self._parse_asn_list(inner)
                segments.append({"type": seg_type, "as_numbers": asns})
                i = (end + 1) if end != -1 else len(token)
            else:
                # Collect plain ASNs up to the next group delimiter
                next_group = len(token)
                for delim in ("{", "(", "[", "<"):
                    pos = token.find(delim, i)
                    if pos != -1 and pos < next_group:
                        next_group = pos
                seq_buf.extend(self._parse_asn_list(token[i:next_group]))
                i = next_group

        _flush_seq()
        return {"segments": segments}

    def _parse_communities(self, cell):
        """Convert an IxNetwork communities string to a list of OTG dicts.

        Handled formats (the first is what 10.80 actually emits)::

            "1 : 2, NO_EXPORT, 65535 : 65535"
                           → two ``manual_as_number`` entries plus
                             ``no_export``
            "1:2 3:4"      → two ``manual_as_number`` entries
            "no-export"    → ``no_export`` well-known entry
            "no-advertise" → ``no_advertised`` well-known entry
            "" / "N/A"     → empty list
        """
        if not cell or cell.strip().lower() in ("", "n/a"):
            return []

        # IxNetwork emits spaces around the colon: the 10.80 capture shows
        # '1 : 2'.  Normalise to '1:2' before tokenising, so that a spaced
        # pair does not split into three tokens.
        cell = re.sub(r"\s*:\s*", ":", cell)

        result = []
        # Entries are separated by commas, whitespace, or both -- 10.80
        # emits '1 : 2, NO_EXPORT, 65535 : 65535'.
        for token in self._ASN_SEPARATOR_RE.split(cell.strip()):
            if not token:
                continue
            # Well-known names arrive in several spellings across versions
            # and columns: 'no-export' and the uppercase 'NO_EXPORT' have
            # both been observed, so normalise separators before lookup.
            well_known = self._WELL_KNOWN_COMMUNITIES.get(
                token.lower().replace("-", "_")
            )
            if well_known is not None:
                result.append({"type": well_known})
            elif ":" in token:
                parts = token.split(":", 1)
                try:
                    as_number = int(parts[0])
                    as_custom = int(parts[1])
                except (ValueError, IndexError):
                    # e.g. a large community 'X:Y:Z' -- int('Y:Z') raises.
                    self.logger.warning(
                        "Skipping unrecognised community token %r: not an "
                        "<as_number>:<as_custom> pair." % token
                    )
                    continue
                over = [
                    name
                    for name, value in (
                        ("as_number", as_number),
                        ("as_custom", as_custom),
                    )
                    if value > self._MAX_COMMUNITY_FIELD
                ]
                if over:
                    # Emitting this would raise at snappi serialisation
                    # time and fail the whole get_states call, so skip it.
                    self.logger.warning(
                        "Skipping community token %r: %s exceeds the OTG "
                        "maximum of %d."
                        % (token, " and ".join(over),
                           self._MAX_COMMUNITY_FIELD)
                    )
                    continue
                result.append({
                    "type": "manual_as_number",
                    "as_number": as_number,
                    "as_custom": as_custom,
                })
            else:
                self.logger.warning(
                    "Skipping unrecognised community token %r: not a "
                    "well-known name or an <as_number>:<as_custom> pair."
                    % token
                )
        return result

    # --- row → OTG prefix dict ---------------------------------------

    def _get_next_hops(self, row):
        """Return ``(ipv4_next_hop, ipv6_next_hop)`` for *row*.
        """
        ipv4_nh = self._get_cell(row, *self._V4_NH_COLS, warn=False)
        ipv6_nh = self._get_cell(row, *self._V6_NH_COLS, warn=False)
        if ipv4_nh is not None or ipv6_nh is not None:
            return ipv4_nh, ipv6_nh

        # Distinguish "column absent" from "column present but holding a
        # placeholder" -- only the former is a schema change worth a
        # warning.  A row legitimately carries no next hop for the family
        # that does not apply to it.
        explicit_cols = self._V4_NH_COLS + self._V6_NH_COLS
        if self._has_any_column(row, explicit_cols):
            return None, None

        nh_cell = self._get_cell(row, *self._NH_COLS, warn=False)
        if nh_cell is not None:
            if ":" in nh_cell:
                return None, nh_cell
            return nh_cell, None

        if not self._has_any_column(row, self._NH_COLS):
            # No next-hop column of any kind: report the whole candidate
            # set in one warning rather than one per candidate.
            self._warn_missing_column(explicit_cols + self._NH_COLS, row)
        return None, None

    @staticmethod
    def _has_any_column(row, col_names):
        """Return True if *row* has any of *col_names* as a key.

        Presence is independent of the cell's value: a column holding a
        placeholder such as ``NA`` is still present.
        """
        return any(name in row for name in col_names)

    def _row_to_ipv4_prefix(self, row):
        """Convert a raw IxNetwork row dict to an OTG IPv4 unicast prefix dict.

        Returns ``None`` when the row lacks address information (e.g. it
        belongs to a different table type such as IPv4 MPLS).
        """
        # warn=False: a miss here means the row belongs to another address
        # family, which is expected, not a schema change.
        addr_cell = self._get_cell(row, *self._V4_ADDR_COLS, warn=False)

        if not addr_cell:
            return None

        nlri_cell = self._get_cell(row, *self._NLRI_COLS)

        # Some IxN versions emit a full CIDR in the address column.
        if "/" in addr_cell:
            parts = addr_cell.split("/", 1)
            ipv4_address = parts[0]
            prefix_length = self._safe_int(parts[1])
        else:
            ipv4_address = addr_cell
            prefix_length = self._safe_int(nlri_cell)

        ipv4_nh, ipv6_nh = self._get_next_hops(row)

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
        # warn=False: see the matching probe in _row_to_ipv4_prefix.
        addr_cell = self._get_cell(row, *self._V6_ADDR_COLS, warn=False)

        if not addr_cell:
            return None

        nlri_cell = self._get_cell(row, *self._NLRI_COLS)

        if "/" in addr_cell:
            parts = addr_cell.split("/", 1)
            ipv6_address = parts[0]
            prefix_length = self._safe_int(parts[1])
        else:
            ipv6_address = addr_cell
            prefix_length = self._safe_int(nlri_cell)

        ipv4_nh, ipv6_nh = self._get_next_hops(row)

        origin_raw = self._get_cell(row, *self._ORIGIN_COLS) or ""
        origin = self._IXN_ORIGIN_MAP.get(origin_raw.lower())

        prefix = {
            "ipv6_address": ipv6_address,
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
        # Fresh warning scope: a missing column is reported once per call,
        # not once per prefix, and not suppressed forever after the first.
        self._warned_columns = set()

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
