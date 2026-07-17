import ipaddress

from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Isis(Base):
    _NETWORK_TYPE = {
        "network_type": {
            "ixn_attr": "networkType",
            "default_value": "broadcast",
            "enum_map": {
                "broadcast": "broadcast",
                "point_to_point": "pointpoint"
            },
        },
    }

    _LEVEL_TYPE = {
        "level_type": {
            "ixn_attr": "levelType",
            "default_value": "level_2",
            "enum_map": {
                "level_1": "level1",
                "level_2": "level2",
                "level_1_2": "l1l2"
            },
        },
    }

    _AUTH_TYPE = {
        "auth_type": {
            "ixn_attr": "authType",
            "enum_map": {"md5": "md5", "password": "password"},
        },
        "mde5": "md5",
        "password": "password",
    }

    _ORIGIN_TYPE = {
        "origin_type": {
            "ixn_attr": "routeOrigin",
            "default_value": "internal",
            "enum_map": {"internal": "internal", "external": "external"},
        }
    }

    _REDISTRIBUTION_TYPE = {
        "redistribution_type": {
            "ixn_attr": "redistribution",
            "default_value": "up",
            "enum_map": {"up": "up", "down": "down"},
        }
    }

    _BASIC = {
        "ipv4_te_router_id": "tERouterId",
        "hostname": "hostName",
        "enable_wide_metric": "enableWideMetric",
        "learned_lsp_filter": "discardLSPs",
    }

    _ADVANCED = {
        "enable_hello_padding": "enableHelloPadding",
        "max_area_addresses": "maxAreaAddresses",
        "area_addresses": "areaAddresses",
        "lsp_refresh_rate": "lSPRefreshRate",
        "lsp_lifetime": "lSPLifetime",
        "psnp_interval": "pSNPInterval",
        "csnp_interval": "cSNPInterval",
        "max_lsp_size": "maxLSPSize",
        "lsp_mgroup_min_trans_interval": "lSPorMGroupPDUMinTransmissionInterval",   # noqa
        "enable_attached_bit": "attached",
    }

    _L1_SETTINGS = {
        "priority": "level1Priority",
        "hello_interval": "level1HelloInterval",
        "dead_interval": "level1DeadInterval",
    }

    _L2_SETTINGS = {
        "priority": "level2Priority",
        "hello_interval": "level2HelloInterval",
        "dead_interval": "level2DeadInterval",
    }

    _MULTI_TOPOLOGY_IDS = {
        "mt_id": "mtId",
        "link_metric": "linkMetric",
    }

    _TRAFFIC_ENGINEERING = {
        "administrative_group": "administratorGroup",
        "metric_level": "metricLevel",
        "max_bandwith": "maxBandwidth",
        "max_reservable_bandwidth": "maxReservableBandwidth",
    }

    _PRIORITY_BANDWIDTHS = {
        "pb0": "bandwidthPriority0",
        "pb1": "bandwidthPriority1",
        "pb2": "bandwidthPriority2",
        "pb3": "bandwidthPriority3",
        "pb4": "bandwidthPriority4",
        "pb5": "bandwidthPriority5",
        "pb6": "bandwidthPriority6",
        "pb7": "bandwidthPriority7",
    }

    _ADVANCED_INTERFACE = {
        "auto_adjust_mtu": "autoAdjustMTU",
        "auto_adjust_area": "autoAdjustArea",
        "auto_adjust_supported_protocols": "autoAdjustSupportedProtocols",
        "enable_3way_handshake": "enable3WayHandshake",
    }

    _LINK_PROTECTION = {
        "extra_traffic": "extraTraffic",
        "unprotected": "unprotected",
        "shared": "shared",
        "dedicated_1_to_1": "dedicatedOneToOne",
        "dedicated_1_plus_1": "dedicatedOnePlusOne",
        "enhanced": "enhanced",
        "reserved_40": "reserved0x40",
        "reserved_80": "reserved0x80",
    }
    _ROUTER_AUTH = {
        "ignore_receive_md5": "ignoreReceiveMD5",
        "area_auth": {
            "ixn_attr": "areaAuthenticationType",
            "enum_map": {"md5": "areaTransmitPasswordOrMD5Key", "password": "areaTransmitPasswordOrMD5Key"},    # noqa
        },
        "domain_auth": {
            "ixn_attr": "domainAuthenticationType",
            "enum_map": {"md5": "domainTransmitPasswordOrMD5Key", "password": "domainTransmitPasswordOrMD5Key"},    # noqa
        },
    }

    _IP_POOL = {
        "address": "networkAddress",
        "prefix": "prefixLength",
        "count": "numberOfAddressesAsy",
        "step": "prefixAddrStep",
    }

    # OTG endpoint_behavior enum → RFC 8986 codepoint sent to IxNetwork
    _ENDPOINT_BEHAVIOR = {
        "end":                    1,
        "end_with_psp":           2,
        "end_with_usp":           3,
        "end_with_psp_usp":       4,
        "end_with_usd":           28,
        "end_with_psp_usd":       29,
        "end_with_usp_usd":       30,
        "end_with_psp_usp_usd":   31,
        "end_dt4":                63,
        "end_dt6":                62,
        "end_dt46":               64,
        "end_x":                  5,
        "end_x_with_psp":         6,
        "end_x_with_usp":         7,
        "end_x_with_psp_usp":     8,
        "end_x_with_usd":         32,
        "end_x_with_psp_usd":     33,
        "end_x_with_usp_usd":     34,
        "end_x_with_psp_usp_usd": 35,
        "end_dx4":                15,
        "end_dx6":                14,
    }

    # (otg_field, ixn_include_attr, ixn_value_attr) for node MSD on isisL3Router
    # Names verified against isisl3router RestPy SDM_ATT_MAP
    _NODE_MSD_MAP = [
        ("max_sl",          "includeMaxSlMsd",          "maxSL"),
        ("max_end_pop_srh", "includeMaximumEndPopMsd",  "maxEndPopSrh"),
        ("max_h_encaps",    "includeMaximumHEncapMsd",  "maxHEncapMsd"),
        ("max_end_d_srh",   "includeMaximumEndDMsd",    "maxEndDMsd"),
        ("max_t_insert",    "includeMaximumTInsertMsd", "maxTInsertMsd"),
        ("max_t_encaps",    "includeMaximumTEncapMsd",  "maxTEncapMsd"),
    ]

    # (otg_field, ixn_include_attr, ixn_value_attr) for link MSD on isisL3
    # Names verified against isisl3 RestPy SDM_ATT_MAP
    _LINK_MSD_MAP = [
        ("max_sl",          "includeMaxSlMsd",          "maxSlMsd"),
        ("max_end_pop_srh", "includeMaximumEndPopMsd",  "maxEndPopMsd"),
        ("max_h_encaps",    "includeMaximumHEncapMsd",  "maxHEncap"),
        ("max_end_d_srh",   "includeMaximumEndDMsd",    "maxEndDMsd"),
        ("max_t_insert",    "includeMaximumTInsertMsd", "maxTInsertMsd"),
        ("max_t_encaps",    "includeMaximumTEncapMsd",  "maxTEncap"),
    ]

    def __init__(self, ngpf):
        super(Isis, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._system_id = None
        self._isis_router_name = None
        self._isis_interface_name = None

    def config(self, device):
        self.logger.debug("Configuring ISIS")
        isis = device.get("isis")
        if isis is None:
            return
        self._system_id = isis.get("system_id")
        self._isis_router_name = isis.get("name")
        self._add_isis_router(isis)

    def _add_isis_router(self, isis):
        self.logger.debug("Configuring Isis Router")
        interfaces = isis.get("interfaces")
        if interfaces is None:
            return
        # IxNetwork supports single ISIS interface per router
        if len(interfaces) > 1:
            return
        for interface in interfaces:
            ethernet_name = interface.get("eth_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            if not self._is_valid(ethernet_name):
                continue
            ixn_eth = self._ngpf.api.ixn_objects.get_object(ethernet_name)
            ixn_isis = self.create_node_elemet(
                ixn_eth, "isisL3", interface.get("name")
            )
            self._ngpf.set_device_info(interface, ixn_isis)
            self._config_isis_interface(interface, ixn_isis, isis)
            ixn_isis_router = self.create_node_elemet(
                self._ngpf.working_dg, "isisL3Router", isis.get("name")
            )
            self._ngpf.api.ixn_objects.set(isis.get("name"), ixn_isis_router)
            ixn_bridged_data = self.create_node_elemet(
                self._ngpf.working_dg, "bridgeData" 
            )
            self._config_system_id(isis, ixn_bridged_data)
            self._config_isis_router(isis, ixn_isis_router)
            self._add_isis_route_range(isis, ixn_isis_router, ixn_isis)
            
    def _is_valid(self, ethernet_name):
        is_valid = True
        if is_valid:
            self.logger.debug("Isis validation success")
        else:
            self.logger.debug("Isis validation failure")
        return is_valid

    def _config_system_id(self, isis, ixn_bridged_data):
        system_id = isis.get("system_id")
        ixn_bridged_data["systemId"] = self.multivalue(system_id)

    def _config_isis_interface(self, interface, ixn_isis, isis=None):
        self.logger.debug("Configuring Isis interfaces")        
        # Metric
        metric = interface.get("metric")
        ixn_isis["interfaceMetric"] = self.multivalue(metric)
        # Network Type
        network_type = interface.get("network_type")
        mapped_type = Isis._NETWORK_TYPE["network_type"]["enum_map"][network_type]   # noqa
        ixn_isis["networkType"] = self.multivalue(mapped_type)
        # Level Type
        level_type = interface.get("level_type")
        mapped_level = Isis._LEVEL_TYPE["level_type"]["enum_map"][level_type]   # noqa
        ixn_isis["levelType"] = self.multivalue(mapped_level)
        # L1 Settings
        l1_settings = interface.get("l1_settings")
        if l1_settings is not None:
            self.logger.debug("priority %s hello_interval %s dead_interval %s " % (l1_settings.priority, l1_settings.hello_interval, l1_settings.dead_interval)) # noqa
            self.configure_multivalues(l1_settings, ixn_isis, Isis._L1_SETTINGS)  # noqa
        # L2 Settings
        l2_settings = interface.get("l2_settings")
        if l2_settings is not None:
            self.logger.debug("priority %s hello_interval %s dead_interval %s " % (l2_settings.priority, l2_settings.hello_interval, l2_settings.dead_interval)) # noqa
            self.configure_multivalues(l2_settings, ixn_isis, Isis._L2_SETTINGS)  # noqa
        # Multiple Topology IDs
        self._configure_multi_topo_id(interface, ixn_isis)
        # Traffic Engineering
        self._configure_traffic_engineering(interface, ixn_isis)
        # Authentication
        auth = interface.get("authentication")
        if auth is not None:
            self.logger.debug("authentication %s " % (auth.auth_type))
            self.configure_multivalues(auth, ixn_isis, Isis._AUTH_TYPE)
        # Advanced
        advanced = interface.get("advanced")
        if advanced is not None:
            self.logger.debug("auto_adjust_mtu %s auto_adjust_area %s auto_adjust_supported_protocols %s enable_3way_handshake %s p2p_hellos_to_unicast_mac %s " % (advanced.auto_adjust_mtu, advanced.auto_adjust_area, advanced.auto_adjust_supported_protocols, advanced.enable_3way_handshake, advanced.p2p_hellos_to_unicast_mac)) # noqa
            self.configure_multivalues(advanced, ixn_isis, Isis._ADVANCED_INTERFACE) # noqa
        # Link Protection
        link_protection = interface.get("link_protection")
        if link_protection is not None:
            self.logger.debug("Configuring link protection")
            self.configure_multivalues(link_protection, ixn_isis, Isis._LINK_PROTECTION) # noqa
        # srlg values
        srlg_vals = interface.get("srlg_values")
        if srlg_vals is not None:
            srlg_count = len(srlg_vals)
            if srlg_count > 0:
                self.logger.debug("srlg values")
                ixn_isis["enableSRLG"] = True
                ixn_isis["srlgCount"] = srlg_count
                for index, value in enumerate(srlg_vals):
                    ixn_isis["srlgValueList"][index] = self.multivalue(value)
        # SRv6 Adjacency SIDs + Link MSD
        self._configure_adjacency_sids(interface, ixn_isis, isis)

    # TBD
    def _configure_multi_topo_id(self, interface, ixn_isis):
        "Configuring multiple topology IDs"

    # TBD
    def _configure_traffic_engineering(self, interface, ixn_isis):
        "Configuring Traffic Engineering"

    def _configure_adjacency_sids(self, interface, ixn_isis, isis=None):
        "Configuring SRv6 Adjacency SIDs and Link MSD"
        srv6_adj = interface.get("srv6_adjacency_sids")
        if srv6_adj is None:
            return

        # Build locator lookup for SID assembly
        locator_map = {}
        first_locator = None
        if isis is not None:
            sr = isis.get("segment_routing")
            if sr is not None:
                for loc in (sr.get("srv6_locators") or []):
                    lname = loc.get("locator_name") or ""
                    locator_map[lname] = loc
                    if first_locator is None:
                        first_locator = loc

        # --- End.X Adjacency SIDs — ONE dict entry with valueList multivalues ---
        # IxN count-controlled lists share a single multivalue source regardless of
        # XPath index: creating N separate dict entries causes each write to overwrite
        # the previous, leaving all rows with the last value.  The fix (same as
        # _configure_srv6_locators) is ONE entry with N-element valueList multivalues.
        sids = srv6_adj.get("sids")
        if sids:
            ixn_isis["adjSidCount"] = len(sids)

            adj_sid_strs = []
            behaviors    = []
            b_flags      = []
            s_flags      = []
            p_flags      = []
            c_flags      = []
            algorithms   = []
            weights      = []
            lb_lens      = []
            ln_lens      = []
            fn_lens      = []
            arg_lens     = []
            has_ss       = False

            for sid in sids:
                locator_choice = sid.get("locator") or "auto"
                if locator_choice == "auto":
                    chosen_loc = first_locator
                else:
                    ref = sid.get("custom_locator_reference") or ""
                    chosen_loc = locator_map.get(ref) or first_locator

                adj_sid_str = "::"
                if chosen_loc is not None:
                    ss = chosen_loc.get("sid_structure")
                    fn_len  = (ss.get("function_length")  if ss else None) or 16
                    arg_len = (ss.get("argument_length") if ss else None) or 0
                    adj_sid_str = self._assemble_ipv6_sid(
                        chosen_loc.get("locator") or "::",
                        chosen_loc.get("prefix_length") or 64,
                        sid.get("function") or "0000",
                        fn_len,
                        sid.get("argument") or "0000",
                        arg_len,
                    )

                behavior = sid.get("endpoint_behavior") or "end_x"
                adj_sid_strs.append(adj_sid_str)
                behaviors.append(Isis._ENDPOINT_BEHAVIOR.get(behavior, 5))
                b_flags.append(sid.get("b_flag") or False)
                s_flags.append(sid.get("s_flag") or False)
                p_flags.append(sid.get("p_flag") or False)
                c_flags.append(sid.get("c_flag") or False)
                algorithms.append(sid.get("algorithm") or 0)
                weights.append(sid.get("weight") or 0)

                if chosen_loc is not None:
                    ss = chosen_loc.get("sid_structure")
                    if ss is not None:
                        has_ss = True
                        lb_lens.append(ss.get("locator_block_length") or 32)
                        ln_lens.append(ss.get("locator_node_length") or 16)
                        fn_lens.append(ss.get("function_length") or 16)
                        arg_lens.append(ss.get("argument_length") or 0)
                    else:
                        lb_lens.append(32); ln_lens.append(16)
                        fn_lens.append(16); arg_lens.append(0)
                else:
                    lb_lens.append(32); ln_lens.append(16)
                    fn_lens.append(16); arg_lens.append(0)

            n = len(sids)
            adj_name = "adjsid_%s" % (interface.get("name") or "intf")
            ixn_adj = self.create_node_elemet(ixn_isis, "isisSRv6AdjSIDList", adj_name)
            ixn_adj["active"]           = self.multivalue([True] * n)
            ixn_adj["ipv6AdjSid"]       = self.multivalue(adj_sid_strs)
            ixn_adj["endPointFunction"] = self.multivalue(behaviors)
            ixn_adj["bFlag"]            = self.multivalue(b_flags)
            ixn_adj["sFlag"]            = self.multivalue(s_flags)
            ixn_adj["pFlag"]            = self.multivalue(p_flags)
            ixn_adj["cFlag"]            = self.multivalue(c_flags)
            ixn_adj["algorithm"]        = self.multivalue(algorithms)
            ixn_adj["weight"]           = self.multivalue(weights)

            if has_ss:
                ixn_adj["includeSRv6SIDStructureSubSubTlv"] = self.multivalue([True] * n)
                ixn_adj["locatorBlockLength"] = self.multivalue(lb_lens)
                ixn_adj["locatorNodeLength"]  = self.multivalue(ln_lens)
                ixn_adj["functionLength"]     = self.multivalue(fn_lens)
                ixn_adj["argumentLength"]     = self.multivalue(arg_lens)

        # --- Link MSD ---
        srv6_link_msd = srv6_adj.get("srv6_link_msd")
        self._configure_link_msd(srv6_link_msd, ixn_isis)

    def _configure_link_msd(self, srv6_link_msd, ixn_isis):
        "Configure per-link SRv6 MSD sub-TLVs on the IsisL3 interface"
        if srv6_link_msd is None:
            return
        has_any = False
        for otg_field, include_attr, value_attr in Isis._LINK_MSD_MAP:
            msd_val = srv6_link_msd.get(otg_field)
            if msd_val is not None:
                v = msd_val.get("value")
                if v is not None:
                    ixn_isis[include_attr] = self.multivalue(True)
                    ixn_isis[value_attr] = self.multivalue(v)
                    has_any = True
        if has_any:
            ixn_isis["advertiseLinkMsd"] = self.multivalue(True)

    @staticmethod
    def _assemble_ipv6_sid(locator_prefix, prefix_length, function_hex,
                           function_length, argument_hex, argument_length):
        "Assemble a full 128-bit SRv6 SID from locator prefix + function + argument"
        try:
            loc_int = int(ipaddress.IPv6Address(locator_prefix))
        except Exception:
            return "::"
        # Keep only the prefix bits
        mask = ((1 << 128) - 1) << (128 - int(prefix_length))
        sid_int = loc_int & mask
        # Place function bits immediately after the locator prefix
        if function_length and function_length > 0 and function_hex:
            try:
                fn_int = int(function_hex.lstrip("0") or "0", 16)
                sid_int |= fn_int << (128 - int(prefix_length) - int(function_length))
            except Exception:
                pass
        # Place argument bits immediately after the function
        if argument_length and argument_length > 0 and argument_hex:
            try:
                arg_int = int(argument_hex.lstrip("0") or "0", 16)
                shift = 128 - int(prefix_length) - int(function_length) - int(argument_length)
                sid_int |= arg_int << shift
            except Exception:
                pass
        return str(ipaddress.IPv6Address(sid_int))

    def _configure_srv6(self, segment_routing, ixn_isis_router):
        "Configure SRv6 capabilities and locators on the IsisL3Router"
        if segment_routing is None:
            return
        router_cap = segment_routing.get("router_capability")
        if router_cap is not None:
            srv6_cap = router_cap.get("srv6_capability")
            if srv6_cap is not None:
                self._configure_srv6_node_capability(srv6_cap, ixn_isis_router)

        srv6_locators = segment_routing.get("srv6_locators")
        if srv6_locators:
            ixn_isis_router["ipv6Srh"] = self.multivalue(True)
            ixn_isis_router["locatorCount"] = len(srv6_locators)
            self._configure_srv6_locators(srv6_locators, ixn_isis_router)

    def _configure_srv6_node_capability(self, srv6_cap, ixn_isis_router):
        "Configure SRv6 Capabilities Sub-TLV fields on IsisL3Router"
        ixn_isis_router["ipv6Srh"] = self.multivalue(True)
        ixn_isis_router["oFlagOfSRv6Cap"] = self.multivalue(
            srv6_cap.get("o_flag") or False
        )
        ixn_isis_router["cFlagOfSRv6Cap"] = self.multivalue(
            srv6_cap.get("c_flag") or False
        )
        node_msds = srv6_cap.get("node_msds")
        self._configure_node_msd(node_msds, ixn_isis_router)

    def _configure_node_msd(self, node_msds, ixn_isis_router):
        "Configure Node MSD sub-TLVs (type 23 in TLV 242) on IsisL3Router"
        if node_msds is None:
            return
        has_any = False
        for otg_field, include_attr, value_attr in Isis._NODE_MSD_MAP:
            msd_val = node_msds.get(otg_field)
            if msd_val is not None:
                v = msd_val.get("value")
                if v is not None:
                    ixn_isis_router[include_attr] = self.multivalue(True)
                    ixn_isis_router[value_attr] = self.multivalue(v)
                    has_any = True
        if has_any:
            ixn_isis_router["advertiseNodeMsd"] = self.multivalue(True)

    def _configure_srv6_locators(self, locators, ixn_isis_router):
        """Configure all locators in ONE IxN dict entry using valueList multivalues.

        IxN count-controlled lists share a single multivalue source regardless of
        XPath index — creating N separate dict entries causes each write to overwrite
        the previous, leaving all instances with the last value. The fix is ONE dict
        entry with N-element valueList multivalues (auto-collapsed to singleValue when
        all N values are identical).
        """
        # Per-locator scalar attributes
        loc_prefixes = [loc.get("locator") or "::" for loc in locators]
        loc_names    = [loc.get("locator_name") or "loc" for loc in locators]
        prefix_lens  = [loc.get("prefix_length") or 64 for loc in locators]
        algorithms   = [loc.get("algorithm") or 0 for loc in locators]
        metrics      = [loc.get("metric") or 0 for loc in locators]
        d_bits       = [loc.get("d_flag") or False for loc in locators]
        mt_id_vals   = [
            (loc.get("mt_id") or [0])[0] if (loc.get("mt_id") or []) else 0
            for loc in locators
        ]

        # Advertise-as-prefix settings per locator
        adv_list     = [loc.get("advertise_locator_as_prefix") for loc in locators]
        adv_bools    = [adv is not None for adv in adv_list]
        rdist_vals   = [(adv.get("redistribution_type") or "up") if adv else "up" for adv in adv_list]
        rmetric_vals = [(adv.get("route_metric") or 0) if adv else 0 for adv in adv_list]
        rorigin_vals = [(adv.get("route_origin") or "internal") if adv else "internal" for adv in adv_list]
        pfx_list     = [(adv.get("prefix_attributes") if adv else None) for adv in adv_list]
        n_flags      = [(pfx.get("n_flag") or False) if pfx else False for pfx in pfx_list]
        r_flags      = [(pfx.get("r_flag") or False) if pfx else False for pfx in pfx_list]
        x_flags      = [(pfx.get("x_flag") or False) if pfx else False for pfx in pfx_list]

        # One dict entry — multivalue() auto-picks singleValue vs valueList
        ixn_loc = self.create_node_elemet(
            ixn_isis_router, "isisSRv6LocatorEntryList", loc_names[0]
        )
        ixn_loc["locator"]      = self.multivalue(loc_prefixes)
        ixn_loc["locatorName"]  = self.multivalue(loc_names)
        ixn_loc["prefixLength"] = self.multivalue(prefix_lens)
        ixn_loc["algorithm"]    = self.multivalue(algorithms)
        ixn_loc["metric"]       = self.multivalue(metrics)
        ixn_loc["dBit"]         = self.multivalue(d_bits)
        ixn_loc["mtId"]         = self.multivalue(mt_id_vals)

        ixn_loc["advertiseLocatorAsPrefix"] = self.multivalue(adv_bools)
        if any(adv_bools):
            ixn_loc["redistribution"] = self.multivalue(rdist_vals)
            ixn_loc["routeMetric"]    = self.multivalue(rmetric_vals)
            ixn_loc["routeOrigin"]    = self.multivalue(rorigin_vals)
            ixn_loc["enableNFlag"]    = self.multivalue(n_flags)
            ixn_loc["enableRFlag"]    = self.multivalue(r_flags)
            ixn_loc["enableXFlag"]    = self.multivalue(x_flags)

        # End SIDs: aggregate all end SIDs across all locators into ONE entry
        sid_counts = [len(loc.get("end_sids") or []) for loc in locators]
        if any(c > 0 for c in sid_counts):
            # Uniform sidCount → scalar; non-uniform → multivalue per locator instance
            if len(set(sid_counts)) == 1:
                ixn_loc["sidCount"] = sid_counts[0]
            else:
                ixn_loc["sidCount"] = self.multivalue(sid_counts)
            # Build flat list of (end_sid, locator) pairs across all locators
            all_pairs = []
            for loc in locators:
                for esid in (loc.get("end_sids") or []):
                    all_pairs.append((esid, loc))
            self._configure_srv6_end_sids_batch(all_pairs, ixn_loc)

    def _configure_srv6_end_sids_batch(self, sid_locator_pairs, ixn_loc):
        """Configure all end SIDs in ONE IxN dict entry with valueList multivalues.

        sid_locator_pairs: flat list of (end_sid, locator) for every end SID
        across all locators for this router.  multivalue() auto-collapses to
        singleValue when all N values are the same.
        """
        full_sids  = []
        behaviors  = []
        c_flags    = []
        lb_lens    = []
        ln_lens    = []
        fn_lens    = []
        arg_lens   = []
        has_ss     = False

        for end_sid, locator in sid_locator_pairs:
            ss = locator.get("sid_structure")
            fn_len  = (ss.get("function_length")  if ss else None) or 16
            arg_len = (ss.get("argument_length")  if ss else None) or 0
            lb_len  = (ss.get("locator_block_length") if ss else None) or 32
            ln_len  = (ss.get("locator_node_length")  if ss else None) or 16

            function_hex  = end_sid.get("function") or "0000"
            argument_hex  = end_sid.get("argument") or "0000"
            prefix_length = locator.get("prefix_length") or 64
            loc_prefix    = locator.get("locator") or "::"

            full_sids.append(self._assemble_ipv6_sid(
                loc_prefix, prefix_length,
                function_hex, fn_len,
                argument_hex, arg_len,
            ))
            behavior = end_sid.get("endpoint_behavior") or "end"
            behaviors.append(Isis._ENDPOINT_BEHAVIOR.get(behavior, 1))
            c_flags.append(end_sid.get("c_flag") or False)
            lb_lens.append(lb_len)
            ln_lens.append(ln_len)
            fn_lens.append(fn_len)
            arg_lens.append(arg_len)
            if ss is not None:
                has_ss = True

        ixn_sid = self.create_node_elemet(ixn_loc, "isisSRv6EndSIDList", "endsids")
        ixn_sid["sid"]              = self.multivalue(full_sids)
        ixn_sid["endPointFunction"] = self.multivalue(behaviors)
        ixn_sid["cFlag"]            = self.multivalue(c_flags)

        # SID Structure sub-sub-TLV (RFC 9352 Section 9)
        if has_ss:
            ixn_sid["includeSRv6SIDStructureSubSubTlv"] = self.multivalue(True)
            ixn_sid["locatorBlockLength"] = self.multivalue(lb_lens)
            ixn_sid["locatorNodeLength"]  = self.multivalue(ln_lens)
            ixn_sid["functionLength"]     = self.multivalue(fn_lens)
            ixn_sid["argumentLength"]     = self.multivalue(arg_lens)

    def _config_isis_router(self, otg_isis_router, ixn_isis_router):
        "Configuring Isis router"
        isis_router_basic = otg_isis_router.get("basic")
        if isis_router_basic is not None:
            self._configure_isis_router_basic(isis_router_basic, ixn_isis_router) # noqa
        isis_router_advanced = otg_isis_router.get("advanced")
        if isis_router_advanced is not None:
            self._configure_isis_router_advanced(isis_router_advanced, ixn_isis_router) # noqa
        isis_router_auth = otg_isis_router.get("router_auth")
        if isis_router_auth is not None:
            self._configure_isis_router_auth(isis_router_auth, ixn_isis_router) # noqa
        segment_routing = otg_isis_router.get("segment_routing")
        if segment_routing is not None:
            self._configure_srv6(segment_routing, ixn_isis_router)
        
    def _configure_isis_router_basic(self, otg_router_basic, ixn_isis_router):
        "Configuring ISIS router basic"
        ipv4_te_router_id = otg_router_basic.get("ipv4_te_router_id")
        if ipv4_te_router_id is not None:
            ixn_isis_router["enableTE"] = self.multivalue(True)
            ixn_isis_router["tERouterId"] = self.multivalue(ipv4_te_router_id)
        else:
            ixn_isis_router["enableTE"] = self.multivalue(False)
        hostname = otg_router_basic.get("hostname")
        if hostname is not None:
            ixn_isis_router["enableHostName"] = self.multivalue(True)
            ixn_isis_router["hostName"] = self.multivalue(hostname)
        else:
            ixn_isis_router["enableHostName"] = self.multivalue(False) 
        ixn_isis_router["discardLSPs"] = self.multivalue(otg_router_basic.get("learned_lsp_filter")) # noqa
        ixn_isis_router["enableWideMetric"] = self.multivalue(otg_router_basic.get("enable_wide_metric")) # noqa

    def _configure_isis_router_advanced(self, otg_router_advanced, ixn_isis_router): # noqa
        "Configuring ISIS router advanced"
        ixn_isis_router["enableHelloPadding"] = self.multivalue(otg_router_advanced.get("enable_hello_padding")) # noqa
        ixn_isis_router["maxAreaAddresses"] = self.multivalue(otg_router_advanced.get("max_area_addresses")) # noqa
        area_address = "490001"
        if len(otg_router_advanced.get("area_addresses")) > 0:
            area_address = "".join(otg_router_advanced.get("area_addresses"))
        ixn_isis_router["areaAddresses"] = self.multivalue(area_address) # noqa
        ixn_isis_router["lSPRefreshRate"] = self.multivalue(otg_router_advanced.get("lsp_refresh_rate")) # noqa
        ixn_isis_router["lSPLifetime"] = self.multivalue(otg_router_advanced.get("lsp_lifetime")) # noqa
        ixn_isis_router["pSNPInterval"] = self.multivalue(otg_router_advanced.get("psnp_interval")) # noqa
        ixn_isis_router["cSNPInterval"] = self.multivalue(otg_router_advanced.get("csnp_interval")) # noqa
        ixn_isis_router["maxLSPSize"] = self.multivalue(otg_router_advanced.get("max_lsp_size")) # noqa
        ixn_isis_router["lSPorMGroupPDUMinTransmissionInterval"] = self.multivalue(otg_router_advanced.get("lsp_mgroup_min_trans_interval")) # noqa
        ixn_isis_router["attached"] = self.multivalue(otg_router_advanced.get("enable_attached_bit")) # noqa
        
    def _configure_isis_router_auth(self, otg_router_auth, ixn_isis_router): # noqa
        "Configuring ISIS router authentication"
        self.configure_multivalues(otg_router_auth, ixn_isis_router, Isis._ROUTER_AUTH) # noqa

    def _add_isis_route_range(self, otg_isis_router, ixn_isis_router, ixn_isis):
        "Configuring ISIS route range"
        v4_routes = otg_isis_router.get("v4_routes")
        if v4_routes is not None:
            self._configure_isisv4_route(v4_routes, ixn_isis)
        v6_routes = otg_isis_router.get("v6_routes")
        if v6_routes is not None:
            self._configure_isisv6_route(v6_routes, ixn_isis)
        self._ngpf.compactor.compact(self._ngpf.working_dg.get("networkGroup"))
        
    def _configure_isisv4_route(self, v4_routes, ixn_isis):
        "Configuring ISIS v4 routes"
        if v4_routes is None:
            return
        self.logger.debug("Configuring ISISv4 Route")
        for route in v4_routes:
            addresses = route.get("addresses")
            for address in addresses:
                ixn_ng = self.create_node_elemet(
                    self._ngpf.working_dg, "networkGroup", route.get("name")
                )
                ixn_ng["multiplier"] = 1
                ixn_ip_pool = self.create_node_elemet(
                    ixn_ng, "ipv4PrefixPools", route.get("name")
                )
                ixn_connector = self.create_property(ixn_ip_pool, "connector")
                ixn_connector["connectedTo"] = self.post_calculated(
                    "connectedTo", ref_ixnobj=ixn_isis
                )
                self.configure_multivalues(address, ixn_ip_pool, Isis._IP_POOL)
                ixn_route = self.create_node_elemet(
                    ixn_ip_pool, "isisL3RouteProperty", route.get("name")
                )
                self._ngpf.set_device_info(route, ixn_ip_pool)
                self._configure_route(route, ixn_route)

    def _configure_isisv6_route(self, v6_routes, ixn_isis):
        "Configuring ISIS v6 routes"
        if v6_routes is None:
            return
        self.logger.debug("Configuring ISISv6 Route")
        for route in v6_routes:
            addresses = route.get("addresses")
            for address in addresses:
                ixn_ng = self.create_node_elemet(
                    self._ngpf.working_dg, "networkGroup", route.get("name")
                )
                ixn_ng["multiplier"] = 1
                ixn_ip_pool = self.create_node_elemet(
                    ixn_ng, "ipv6PrefixPools", route.get("name")
                )
                ixn_connector = self.create_property(ixn_ip_pool, "connector")
                ixn_connector["connectedTo"] = self.post_calculated(
                    "connectedTo", ref_ixnobj=ixn_isis
                )
                self.configure_multivalues(address, ixn_ip_pool, Isis._IP_POOL)
                ixn_route = self.create_node_elemet(
                    ixn_ip_pool, "isisL3RouteProperty", route.get("name")
                )
                self._ngpf.set_device_info(route, ixn_ip_pool)
                self._configure_route(route, ixn_route)
        
    def _configure_route(self, otg_route, ixn_route):
        "Configuring ISIS v4 routes"
        self._ngpf.set_ixn_routes(otg_route, ixn_route)
        # Link metric
        metric = otg_route.get("link_metric")
        ixn_route["metric"] = self.multivalue(metric)
        # Origin Type
        origin_type = otg_route.get("origin_type")
        mapped_type = Isis._ORIGIN_TYPE["origin_type"]["enum_map"][origin_type]   # noqa
        ixn_route["routeOrigin"] = self.multivalue(mapped_type)
        # Redistribution Type
        redistribution_type = otg_route.get("redistribution_type")
        mapped_type = Isis._REDISTRIBUTION_TYPE["redistribution_type"]["enum_map"][redistribution_type]   # noqa
        ixn_route["redistribution"] = self.multivalue(mapped_type)