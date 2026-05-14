import ipaddress

from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class IsisSrv6(Base):
    """Maps OTG IS-IS SRv6 configuration to IxNetwork RestPy objects.

    Covers:
    - SRv6 node capability (c_flag hint; MSD deferred)
    - Locators -> isisSRv6LocatorEntryList
    - End SIDs -> isisSRv6EndSIDList (per locator)
    - Adjacency SIDs -> isisSRv6AdjSIDList (per interface)
    """

    # OTG endpoint_behavior -> IxNetwork EndPointFunction numeric code (End SID)
    # Codes from IxNetwork enumInfo on isisSRv6EndSIDList.endPointFunction.
    # DT/DX behaviors use NEXT-CSID (uSID) variants throughout because IxNetwork
    # does not expose distinct base End.DT4 or End.DT46 codes; the NEXT-CSID
    # variants (uDT4, uDT46, uDT6, uDX6) are the only available options for
    # these behaviors. This is correct for uSID (c_flag=True) deployments.
    _END_SID_BEHAVIOR = {
        "end":                  1,   # End (no PSP, no USP)
        "end_with_psp":         2,   # End with PSP
        "end_with_usp":         3,   # End with USP
        "end_with_psp_usp":     4,   # End with PSP and USP
        "end_with_usd":         47,  # End with NEXT-CSID and USD
        "end_with_psp_usd":     48,  # End with NEXT-CSID, PSP and USD
        "end_with_usp_usd":     49,  # End with NEXT-CSID, USP and USD
        "end_with_psp_usp_usd": 50,  # End with NEXT-CSID, PSP, USP and USD
        "end_dt4":              63,  # uDT4 (End.DT4 NEXT-CSID)
        "end_dt6":              62,  # uDT6 (End.DT6 NEXT-CSID)
        "end_dt46":             64,  # uDT46 (End.DT46 NEXT-CSID)
    }

    # OTG endpoint_behavior -> IxNetwork EndPointFunction numeric code (Adj SID)
    # DX behaviors use NEXT-CSID variants for the same reason as End SID above.
    _ADJ_SID_BEHAVIOR = {
        "end_x":                  5,   # End.X (no PSP, no USP)
        "end_x_with_psp":         6,   # End.X with PSP
        "end_x_with_usp":         7,   # End.X with USP
        "end_x_with_psp_usp":     8,   # End.X with PSP and USP
        "end_x_with_usd":         56,  # End.X with NEXT-CSID and USD
        "end_x_with_psp_usd":     57,  # End.X with NEXT-CSID, PSP and USD
        "end_x_with_usp_usd":     58,  # End.X with NEXT-CSID, USP and USD
        "end_x_with_psp_usp_usd": 59,  # End.X with NEXT-CSID, PSP, USP and USD
        "end_dx4":                61,  # uDX4 (End.DX4 NEXT-CSID)
        "end_dx6":                60,  # uDX6 (End.DX6 NEXT-CSID)
    }

    _REDISTRIBUTION_MAP = {
        "up":   "up",
        "down": "down",
    }

    _ROUTE_ORIGIN_MAP = {
        "internal": "internal",
        "external": "external",
    }

    def __init__(self, ngpf):
        super(IsisSrv6, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._c_flag_hint = False

    # ------------------------------------------------------------------
    # Public entry points called from isis.py
    # ------------------------------------------------------------------

    # OTG IsisSRv6.Msd field -> (IxN include attr, IxN value attr) for node MSD.
    # Uses SRH-specific MSD type codes (RFC 9352 Section 6.2).
    _NODE_MSD_MAP = {
        "max_sl":          ("includeMaximumSLTLV",       "maxSL"),
        "max_end_pop_srh": ("includeMaximumEndPopSrhTLV","maxEndPopSrh"),
        "max_h_encaps":    ("includeMaximumHEncapMsd",   "maxHEncapMsd"),
        "max_end_d_srh":   ("includeMaximumEndDSrhTLV",  "maxEndD"),
        "max_t_insert":    ("includeMaximumTInsertSrhTLV","maxTInsert"),
        "max_t_encaps":    ("includeMaximumTEncapSrhTLV","maxTEncap"),
    }

    # OTG IsisSRv6.Msd field -> (IxN include attr, IxN value attr) for link MSD.
    # Interface-level MSD uses generic MSD type codes on isisL3.
    _LINK_MSD_MAP = {
        "max_sl":          ("includeMaxSlMsd",           "maxSlMsd"),
        "max_end_pop_srh": ("includeMaximumEndPopMsd",   "maxEndPopMsd"),
        "max_h_encaps":    ("includeMaximumHEncapMsd",   "maxHEncap"),
        "max_end_d_srh":   ("includeMaximumEndDMsd",     "maxEndDMsd"),
        "max_t_insert":    ("includeMaximumTInsertMsd",  "maxTInsertMsd"),
        "max_t_encaps":    ("includeMaximumTEncapMsd",   "maxTEncap"),
    }

    def config_node_capability(self, otg_srv6_cap, ixn_isis_router):
        """Map OTG SRv6 node capability to IxNetwork isisL3Router attributes.

        c_flag is stored as a hint applied to all End/Adj SIDs under this
        router (IxNetwork has no single router-level c_flag toggle).
        MSD sub-TLVs use the paired Include* boolean + value pattern
        (RFC 9352 Section 6.2); a value of 0 means suppress the sub-TLV.
        """
        c_flag = otg_srv6_cap.get("c_flag")
        if c_flag is None:
            c_flag = False
        self._c_flag_hint = c_flag

        # Enable SRv6 on the router and set capability flags
        ixn_isis_router["ipv6Srh"]        = self.multivalue(True)
        ixn_isis_router["cFlagOfSRv6Cap"] = self.multivalue(c_flag)
        o_flag = otg_srv6_cap.get("o_flag") or False
        ixn_isis_router["oFlagOfSRv6CapTlv"] = self.multivalue(o_flag)

        node_msds = otg_srv6_cap.get("node_msds")
        if node_msds is not None:
            self._config_msd(node_msds, ixn_isis_router, self._NODE_MSD_MAP,
                             advertise_key="advertiseNodeMsd")

    def config_link_msd(self, otg_link_msd, ixn_isis_iface):
        """Map OTG IsisSRv6.Msd to IxNetwork isisL3 interface link-MSD attributes.

        Each property is a plain integer; 0 (default) suppresses the sub-TLV.
        """
        self._config_msd(otg_link_msd, ixn_isis_iface, self._LINK_MSD_MAP,
                         advertise_key="advertiseLinkMsd")

    def _config_msd(self, otg_msd, ixn_obj, msd_map, advertise_key):
        """Set IxNetwork MSD Include/value multivalue pairs from an OTG Msd object.

        Each OTG MSD property is an IsisSRv6MsdValue object (dict with a
        "value" key, isis-srv6-review-2 API).  A missing or zero value means
        suppress the sub-TLV.
        """
        any_present = False
        for otg_attr, (include_key, value_key) in msd_map.items():
            val_obj = otg_msd.get(otg_attr)
            if val_obj is None:
                continue
            # IsisSRv6MsdValue wraps the integer; fall back to bare int for
            # forward compatibility.
            if isinstance(val_obj, dict):
                val = val_obj.get("value")
            elif hasattr(val_obj, 'value'):
                val = val_obj.value
            else:
                val = val_obj
            if val is None or val == 0:
                continue
            any_present = True
            ixn_obj[include_key] = self.multivalue(True)
            ixn_obj[value_key]   = self.multivalue(val)
        if any_present:
            ixn_obj[advertise_key] = self.multivalue(True)

    def config_locators(self, otg_locators, ixn_isis_router):
        """Map OTG locators to IxN isisSRv6LocatorEntryList.

        IxN importconfig semantics: when locatorCount=N, each scalar
        multivalue on a single isisSRv6LocatorEntryList entry is broadcast
        to ALL N pre-allocated rows, so a second entry for a second locator
        would overwrite the first.  The correct pattern is ONE entry with
        N-value multivalues (one value per locator row), same as the
        N-value SID pattern within a locator.

        All End SIDs from all locators are flattened into a single
        isisSRv6EndSIDList entry with (locatorCount x sidCount)-value
        multivalues.  sidCount is a raw kInteger64 field (not a multivalue)
        so it must be uniform across all locator rows; a warning is emitted
        when locators carry different numbers of End SIDs.
        """
        if not otg_locators:
            return
        n_locs = len(otg_locators)
        ixn_isis_router["locatorCount"] = n_locs
        c_flag_hint = self._c_flag_hint
        self._c_flag_hint = False  # reset so subsequent routers do not inherit

        # -- per-locator attribute vectors (index = locator row) ---------------
        locs_addr, locs_pfxlen, locs_algo, locs_metric = [], [], [], []
        locs_dbit, locs_mtid = [], []
        locs_adv, locs_rt_metric, locs_redist, locs_origin = [], [], [], []
        locs_xflag, locs_rflag, locs_nflag = [], [], []
        sid_counts = []

        # flat SID attribute vectors (all SIDs from all locators, in order)
        all_sids, all_behaviors, all_c_flags = [], [], []
        all_lb, all_ln, all_fn_lens, all_arg_lens = [], [], [], []
        any_structure = False

        for otg_loc in otg_locators:
            locs_addr.append(otg_loc.get("locator") or "::")
            locs_pfxlen.append(otg_loc.get("prefix_length") or 128)
            locs_algo.append(otg_loc.get("algorithm") or 0)
            locs_metric.append(otg_loc.get("metric") or 0)
            locs_dbit.append(otg_loc.get("d_flag") or False)

            mt_id_list = otg_loc.get("mt_id")
            if mt_id_list and len(mt_id_list) > 1:
                self.logger.warning(
                    "IsisSrv6: mt_id has %d elements for locator '%s'; "
                    "only the first is used (IxNetwork exposes a single MtId per locator)",
                    len(mt_id_list), otg_loc.get("locator_name"),
                )
            locs_mtid.append(mt_id_list[0] if mt_id_list else 0)

            adv = otg_loc.get("advertise_locator_as_prefix")
            if adv is not None:
                locs_adv.append(True)
                locs_rt_metric.append(adv.get("route_metric") or 0)
                redist = adv.get("redistribution_type") or "up"
                locs_redist.append(self._REDISTRIBUTION_MAP.get(redist, "up"))
                origin = adv.get("route_origin") or "internal"
                locs_origin.append(self._ROUTE_ORIGIN_MAP.get(origin, "internal"))
                pattr = adv.get("prefix_attributes")
                if pattr is not None:
                    locs_xflag.append(pattr.get("x_flag") or False)
                    locs_rflag.append(pattr.get("r_flag") or False)
                    locs_nflag.append(pattr.get("n_flag") or False)
                else:
                    locs_xflag.append(False)
                    locs_rflag.append(False)
                    locs_nflag.append(False)
            else:
                locs_adv.append(False)
                locs_rt_metric.append(0)
                locs_redist.append("up")
                locs_origin.append("internal")
                locs_xflag.append(False)
                locs_rflag.append(False)
                locs_nflag.append(False)

            # collect this locator's End SIDs into the flat vectors
            otg_end_sids = otg_loc.get("end_sids") or []
            sid_counts.append(len(otg_end_sids))

            sid_structure = otg_loc.get("sid_structure")
            loc_addr   = otg_loc.get("locator") or "::"
            prefix_len = otg_loc.get("prefix_length") or 128
            has_structure = sid_structure is not None

            for otg_sid in otg_end_sids:
                fn_hex  = otg_sid.get("function") or "0000"
                arg_hex = otg_sid.get("argument") or "0000"
                fn_len  = sid_structure.get("function_length")  if has_structure else 0
                arg_len = sid_structure.get("argument_length") if has_structure else 0

                assembled = self._assemble_sid(
                    loc_addr, prefix_len, fn_hex, arg_hex, fn_len, arg_len
                )
                behavior_otg = otg_sid.get("endpoint_behavior") or "end"
                behavior_ixn = self._END_SID_BEHAVIOR.get(behavior_otg, 1)

                c_flag = otg_sid.get("c_flag")
                if c_flag is None:
                    c_flag = c_flag_hint

                all_sids.append(assembled)
                all_behaviors.append(behavior_ixn)
                all_c_flags.append(c_flag)

                if has_structure:
                    any_structure = True
                all_lb.append(sid_structure.get("locator_block_length") if has_structure else 0)
                all_ln.append(sid_structure.get("locator_node_length")  if has_structure else 0)
                all_fn_lens.append(fn_len)
                all_arg_lens.append(arg_len)

        # -- ONE locator entry with N-value multivalues for all locator rows ---
        ixn_loc = self.create_node_elemet(
            ixn_isis_router, "isisSRv6LocatorEntryList",
            otg_locators[0].get("locator_name"),
        )
        ixn_loc["active"]       = self.multivalue([True] * n_locs)
        ixn_loc["locator"]      = self.multivalue(locs_addr)
        ixn_loc["prefixLength"] = self.multivalue(locs_pfxlen)
        ixn_loc["algorithm"]    = self.multivalue(locs_algo)
        ixn_loc["metric"]       = self.multivalue(locs_metric)
        ixn_loc["dBit"]         = self.multivalue(locs_dbit)
        ixn_loc["mtId"]         = self.multivalue(locs_mtid)
        ixn_loc["advertiseLocatorAsPrefix"] = self.multivalue(locs_adv)
        ixn_loc["routeMetric"]  = self.multivalue(locs_rt_metric)
        ixn_loc["redistribution"] = self.multivalue(locs_redist)
        ixn_loc["routeOrigin"]  = self.multivalue(locs_origin)
        ixn_loc["enableXFlag"]  = self.multivalue(locs_xflag)
        ixn_loc["enableRFlag"]  = self.multivalue(locs_rflag)
        ixn_loc["enableNFlag"]  = self.multivalue(locs_nflag)

        total_sids = len(all_sids)
        if total_sids == 0:
            return

        # sidCount is kInteger64 (not a multivalue) so must be uniform
        unique_counts = set(sid_counts)
        if len(unique_counts) > 1:
            self.logger.warning(
                "IsisSrv6: locators have unequal End SID counts %s; "
                "sidCount must be uniform in IxNetwork; using max=%d",
                sid_counts, max(unique_counts),
            )
        ixn_loc["sidCount"] = max(unique_counts)

        # ONE EndSIDList entry; total rows = locatorCount x sidCount
        ixn_sid = self.create_node_elemet(ixn_loc, "isisSRv6EndSIDList")
        ixn_sid["sid"]              = self.multivalue(all_sids)
        ixn_sid["endPointFunction"] = self.multivalue(all_behaviors)
        ixn_sid["cFlag"]            = self.multivalue(all_c_flags)

        if any_structure:
            ixn_sid["locatorBlockLength"]               = self.multivalue(all_lb)
            ixn_sid["locatorNodeLength"]                = self.multivalue(all_ln)
            ixn_sid["functionLength"]                   = self.multivalue(all_fn_lens)
            ixn_sid["argumentLength"]                   = self.multivalue(all_arg_lens)
            ixn_sid["includeSRv6SIDStructureSubSubTlv"] = self.multivalue(
                [True] * total_sids
            )

    def config_adj_sids(self, otg_adj_sids, ixn_isis_iface, otg_locators,
                        c_flag_hint=False):
        """Create isisSRv6AdjSIDList entries under an IS-IS interface."""
        if not otg_adj_sids:
            return
        for otg_adj in otg_adj_sids:
            locator_choice = otg_adj.get("locator") or "auto"
            resolved_loc = self._resolve_locator(locator_choice, otg_adj, otg_locators)
            if resolved_loc is None:
                self.logger.warning(
                    "IsisSrv6: could not resolve locator for adj SID (locator=%s); skipped",
                    locator_choice,
                )
                continue

            loc_addr   = resolved_loc.get("locator") or "::"
            prefix_len = resolved_loc.get("prefix_length") or 128
            sid_structure = resolved_loc.get("sid_structure")
            has_structure = sid_structure is not None
            fn_len  = sid_structure.get("function_length")  if has_structure else 0
            arg_len = sid_structure.get("argument_length") if has_structure else 0

            function_hex = otg_adj.get("function") or "0000"
            assembled = self._assemble_sid(
                loc_addr, prefix_len, function_hex, "0000", fn_len, arg_len
            )

            behavior_otg = otg_adj.get("endpoint_behavior") or "end_x"
            behavior_ixn = self._ADJ_SID_BEHAVIOR.get(behavior_otg, 5)

            c_flag = otg_adj.get("c_flag")
            if c_flag is None:
                c_flag = c_flag_hint

            ixn_adj = self.create_node_elemet(ixn_isis_iface, "isisSRv6AdjSIDList")
            ixn_adj["ipv6AdjSid"]       = self.multivalue(assembled)
            ixn_adj["endPointFunction"] = self.multivalue(behavior_ixn)
            ixn_adj["cFlag"]            = self.multivalue(c_flag)
            ixn_adj["bFlag"]            = self.multivalue(otg_adj.get("b_flag") or False)
            ixn_adj["sFlag"]            = self.multivalue(otg_adj.get("s_flag") or False)
            ixn_adj["pFlag"]            = self.multivalue(otg_adj.get("p_flag") or False)
            ixn_adj["weight"]           = self.multivalue(otg_adj.get("weight") or 0)
            ixn_adj["algorithm"]        = self.multivalue(otg_adj.get("algorithm") or 0)

            if has_structure:
                lb = sid_structure.get("locator_block_length")
                ln = sid_structure.get("locator_node_length")
                ixn_adj["locatorBlockLength"] = self.multivalue(lb)
                ixn_adj["locatorNodeLength"]  = self.multivalue(ln)
                ixn_adj["functionLength"]     = self.multivalue(fn_len)
                ixn_adj["argumentLength"]     = self.multivalue(arg_len)
                ixn_adj["includeSRv6SIDStructureSubSubTlv"] = self.multivalue(True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble_sid(locator, prefix_len, function_hex, argument_hex,
                      function_length, argument_length):
        """Assemble a 128-bit SID IPv6 address from locator + function + argument.

        The locator occupies the top prefix_len bits.  The function field
        immediately follows (function_length bits), then the argument
        (argument_length bits).  All remaining bits are zero.

        Example (F3216 format):
            locator=fc00:0:1::, prefix_len=48, function=0001, fn_len=16, arg_len=0
            => fc00:0:1:1::

        When function_length=0 (no sid_structure), the bit width is inferred from
        the length of the function_hex string (4 hex digits = 16 bits).
        """
        try:
            loc_int = int(ipaddress.IPv6Address(locator))
            fn_int  = int(function_hex, 16) if function_hex else 0
            arg_int = int(argument_hex, 16) if argument_hex else 0
            # Infer function width from hex string when no explicit structure
            fn_bits  = function_length if function_length else (len(function_hex) * 4 if function_hex else 0)
            arg_bits = argument_length if argument_length else (len(argument_hex) * 4 if argument_hex and arg_int else 0)
            # Function bits sit immediately after the prefix, then argument
            fn_shift  = 128 - prefix_len - fn_bits
            arg_shift = 128 - prefix_len - fn_bits - arg_bits
            sid_int   = loc_int | (fn_int << fn_shift) | (arg_int << arg_shift)
            return str(ipaddress.IPv6Address(sid_int))
        except Exception as exc:
            raise ValueError(
                "IsisSrv6: failed to assemble SID from locator=%s prefix_len=%s "
                "function=%s argument=%s: %s" % (
                    locator, prefix_len, function_hex, argument_hex, exc
                )
            )

    def _resolve_locator(self, locator_choice, otg_adj, otg_locators):
        """Return the OTG locator object for an adjacency SID.

        'auto' => first locator in the router's srv6_locators list.
        Anything else is treated as a locator_name reference.
        """
        if not otg_locators:
            return None
        if locator_choice == "auto":
            return otg_locators[0] if len(otg_locators) > 0 else None
        # custom_locator_reference case
        ref_name = otg_adj.get("custom_locator_reference")
        for loc in otg_locators:
            if loc.get("locator_name") == ref_name:
                return loc
        return None
