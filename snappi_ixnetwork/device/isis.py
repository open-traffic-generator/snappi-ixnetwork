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

    # endPointFunction uses IANA SRv6 Endpoint Behavior Code Points (RFC 8986 + IANA registry).
    # IxNetwork NGPF expects integer values for this multivalue field.
    _SRV6_END_POINT_FUNCTION = {
        "end_point_function": {
            "ixn_attr": "endPointFunction",
            "default_value": 1,
            "enum_map": {
                # End SID behaviors (IANA codes)
                "end":                    1,   # End (no PSP, no USP)
                "end_with_psp":           2,   # End with PSP
                "end_with_usp":           3,   # End with USP
                "end_with_psp_usp":       4,   # End with PSP+USP
                "end_with_usd":           27,  # End with USD
                "end_with_psp_usd":       28,  # End with PSP+USD
                "end_with_usp_usd":       29,  # End with USP+USD
                "end_with_psp_usp_usd":   30,  # End with PSP+USP+USD
                "end_dt4":                18,  # End.DT4
                "end_dt6":                17,  # End.DT6
                "end_dt46":               19,  # End.DT46
                # Adj SID behaviors (IANA codes)
                "end_x":                  5,   # End.X (no PSP, no USP)
                "end_x_with_psp":         6,   # End.X with PSP
                "end_x_with_usp":         7,   # End.X with USP
                "end_x_with_psp_usp":     8,   # End.X with PSP+USP
                "end_x_with_usd":         31,  # End.X with USD
                "end_x_with_psp_usd":     32,  # End.X with PSP+USD
                "end_x_with_usp_usd":     33,  # End.X with USP+USD
                "end_x_with_psp_usp_usd": 34,  # End.X with PSP+USP+USD
                "end_dx4":                16,  # End.DX4
                "end_dx6":                15,  # End.DX6
            },
        }
    }

    def __init__(self, ngpf):
        super(Isis, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._system_id = None
        self._isis_router_name = None
        self._isis_interface_name = None
        self._srv6_locator_map = {}

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
            self._config_isis_interface(interface, ixn_isis)
            ixn_isis_router = self.create_node_elemet(
                self._ngpf.working_dg, "isisL3Router", isis.get("name")
            )
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

    def _config_isis_interface(self, interface, ixn_isis):
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
        #TBD 
        # Adjacency Sids
        self._configure_adjacency_sids(interface, ixn_isis)     

    # TBD 
    def _configure_multi_topo_id(self, interface, ixn_isis):
        "Configuring multiple topology IDs"
    
    # TBD 
    def _configure_traffic_engineering(self, interface, ixn_isis):
        "Configuring Traffic Engineering"

    def _configure_adjacency_sids(self, interface, ixn_isis):
        "Configuring SRv6 Adjacency SIDs (isisSRv6AdjSIDList) on an ISIS interface"
        srv6_adj_sids = interface.get("srv6_adjacency_sids")
        if srv6_adj_sids is None or len(srv6_adj_sids) == 0:
            return
        self.logger.debug("Configuring SRv6 Adjacency SIDs")
        ep_map = Isis._SRV6_END_POINT_FUNCTION["end_point_function"]["enum_map"]
        ixn_isis["enableIPv6SID"] = self.multivalue(True)
        ixn_adj_sid_list = self.create_node(ixn_isis, "isisSRv6AdjSIDList")
        for adj_sid in srv6_adj_sids:
            ixn_adj_sid = self.add_element(ixn_adj_sid_list)
            # Construct full SID from locator reference + function
            locator_choice = adj_sid.get("locator")
            function_hex = adj_sid.get("function")
            sid = self._resolve_adj_sid(
                locator_choice,
                adj_sid.get("custom_locator_reference"),
                function_hex,
            )
            if sid is not None:
                ixn_adj_sid["ipv6AdjSid"] = self.multivalue(sid)
            # Endpoint behavior
            ep = adj_sid.get("endpoint_behavior")
            if ep is not None and ep in ep_map:
                ixn_adj_sid["endPointFunction"] = self.multivalue(ep_map[ep])
            # Scalar fields
            for snappi_attr, ixn_attr in [
                ("algorithm", "algorithm"),
                ("weight", "weight"),
                ("b_flag", "bFlag"),
                ("s_flag", "sFlag"),
                ("p_flag", "pFlag"),
                ("c_flag", "cFlag"),
            ]:
                val = adj_sid.get(snappi_attr)
                if val is not None:
                    ixn_adj_sid[ixn_attr] = self.multivalue(val)
            # SID structure lengths
            sid_struct = adj_sid.get("sid_structure")
            if sid_struct is not None:
                for snappi_attr, ixn_attr in [
                    ("locator_block_length", "locatorBlockLength"),
                    ("locator_node_length", "locatorNodeLength"),
                    ("function_length", "functionLength"),
                    ("argument_length", "argumentLength"),
                ]:
                    val = sid_struct.get(snappi_attr)
                    if val is not None:
                        ixn_adj_sid[ixn_attr] = self.multivalue(val)

    def _resolve_adj_sid(self, locator_choice, custom_locator_ref, function_hex):
        "Resolve full IPv6 Adj SID from locator reference + function hex."
        if not function_hex:
            return None
        locator_info = None
        if locator_choice == "custom_locator_reference" and custom_locator_ref:
            locator_info = self._srv6_locator_map.get(custom_locator_ref)
        else:
            # 'auto' or None: use the first available locator
            if self._srv6_locator_map:
                locator_info = next(iter(self._srv6_locator_map.values()))
        if locator_info is None:
            return None
        return self._construct_srv6_sid(
            locator_info["prefix"],
            locator_info["block_len"],
            locator_info["node_len"],
            function_hex,
            locator_info.get("func_len", 16),
        )

    def _construct_srv6_sid(
        self, locator_prefix, block_len, node_len,
        function_hex, func_len, argument_hex=None, arg_len=0
    ):
        "Construct full 128-bit SRv6 SID from locator prefix and function hex."
        try:
            locator_len = block_len + node_len
            net = ipaddress.IPv6Network(
                "{}/{}".format(locator_prefix, locator_len), strict=False
            )
            loc_int = int(net.network_address)
            func_int = int(function_hex, 16)
            shift = 128 - locator_len - func_len
            sid_int = loc_int | (func_int << shift)
            if argument_hex and arg_len > 0:
                arg_int = int(argument_hex, 16)
                arg_shift = 128 - locator_len - func_len - arg_len
                sid_int |= (arg_int << arg_shift)
            return str(ipaddress.IPv6Address(sid_int))
        except Exception as e:
            self.logger.warning("Failed to construct SRv6 SID: %s" % e)
            return None

    def _configure_srv6(self, isis, ixn_isis_router):
        "Main SRv6 entry point reading isis.segment_routing"
        sr = isis.get("segment_routing")
        if sr is None:
            return
        # Router capability SRv6 flags
        rc = sr.get("router_capability")
        if rc is not None:
            self._configure_srv6_router_capability(rc, ixn_isis_router)
        # SRv6 locators
        srv6_locators = sr.get("srv6_locators")
        if srv6_locators is not None and len(srv6_locators) > 0:
            ixn_isis_router["enableSR"] = True  # plain bool, not multivalue
            ixn_isis_router["locatorCount"] = len(srv6_locators)
            self._configure_srv6_locator_list(srv6_locators, ixn_isis_router)

    def _configure_srv6_router_capability(self, rc, ixn_isis_router):
        "Configure SRv6 capability flags in isisL3Router"
        srv6_cap = rc.get("srv6_capability")
        if srv6_cap is None:
            return
        self.logger.debug("Configuring SRv6 router capability")
        c_flag = srv6_cap.get("c_flag")
        if c_flag is not None:
            ixn_isis_router["cFlagOfSRv6Cap"] = self.multivalue(c_flag)
        o_flag = srv6_cap.get("o_flag")
        if o_flag is not None:
            ixn_isis_router["oFlagOfSRv6CapTlv"] = self.multivalue(o_flag)

    def _configure_srv6_locator_list(self, srv6_locators, ixn_isis_router):
        "Configure isisSRv6LocatorEntryList under isisL3Router"
        self.logger.debug("Configuring SRv6 Locators")
        self._srv6_locator_map = {}
        ixn_locator_list = self.create_node(
            ixn_isis_router, "isisSRv6LocatorEntryList"
        )
        for locator in srv6_locators:
            locator_name = locator.get("locator_name")
            locator_prefix = locator.get("locator")
            ixn_locator = self.add_element(ixn_locator_list)
            if locator_name is not None:
                ixn_locator["locatorName"] = [locator_name]
            if locator_prefix is not None:
                ixn_locator["locator"] = self.multivalue(locator_prefix)
            # Scalar locator fields
            for snappi_attr, ixn_attr in [
                ("prefix_length", "prefixLength"),
                ("metric", "metric"),
                ("algorithm", "algorithm"),
                ("d_flag", "dBit"),
            ]:
                val = locator.get(snappi_attr)
                if val is not None:
                    ixn_locator[ixn_attr] = self.multivalue(val)
            # MT IDs
            mt_ids = locator.get("mt_id")
            if mt_ids is not None and len(mt_ids) > 0:
                ixn_locator["mtId"] = self.multivalue(mt_ids[0])
            # SID structure: derive locatorSize and propagate lengths to end SIDs
            block_len = 48
            node_len = 16
            func_len = 16
            arg_len = 0
            sid_struct = locator.get("sid_structure")
            if sid_struct is not None:
                block_len = sid_struct.get("locator_block_length") or 48
                node_len = sid_struct.get("locator_node_length") or 16
                func_len = sid_struct.get("function_length") or 16
                arg_len = sid_struct.get("argument_length") or 0
                ixn_locator["locatorSize"] = self.multivalue(block_len + node_len)
            # Advertise locator as prefix
            alp = locator.get("advertise_locator_as_prefix")
            if alp is not None:
                ixn_locator["advertiseLocatorAsPrefix"] = self.multivalue(True)
                redist = alp.get("redistribution_type") or "up"
                ixn_locator["redistribution"] = self.multivalue(redist)
                route_origin = alp.get("route_origin") or "internal"
                ixn_locator["routeOrigin"] = self.multivalue(route_origin)
                route_metric = alp.get("route_metric")
                if route_metric is not None:
                    ixn_locator["routeMetric"] = self.multivalue(route_metric)
                # Note: enableNFlag/enableRFlag/enableXFlag are not supported
                # on isisSRv6LocatorEntryList in all IxNetwork server versions.
                # Those flags are omitted to avoid JSON import errors.
            # Cache for adj SID resolution
            if locator_name is not None and locator_prefix is not None:
                self._srv6_locator_map[locator_name] = {
                    "prefix": locator_prefix,
                    "block_len": block_len,
                    "node_len": node_len,
                    "func_len": func_len,
                    "arg_len": arg_len,
                }
            # End SIDs
            end_sids = locator.get("end_sids")
            if end_sids is not None and len(end_sids) > 0:
                ixn_locator["sidCount"] = len(end_sids)
                self._configure_srv6_end_sid_list(
                    end_sids, ixn_locator, locator_prefix,
                    block_len, node_len, func_len, arg_len,
                )

    def _configure_srv6_end_sid_list(
        self, end_sids, ixn_locator, locator_prefix,
        block_len, node_len, func_len, arg_len
    ):
        "Configure isisSRv6EndSIDList under a locator entry"
        self.logger.debug("Configuring SRv6 End SIDs")
        ep_map = Isis._SRV6_END_POINT_FUNCTION["end_point_function"]["enum_map"]
        ixn_end_sid_list = self.create_node(ixn_locator, "isisSRv6EndSIDList")
        for end_sid in end_sids:
            ixn_end_sid = self.add_element(ixn_end_sid_list)
            # Construct full SID from locator prefix + function hex
            function_hex = end_sid.get("function")
            argument_hex = end_sid.get("argument")
            if locator_prefix and function_hex:
                sid = self._construct_srv6_sid(
                    locator_prefix, block_len, node_len,
                    function_hex, func_len, argument_hex, arg_len,
                )
                if sid is not None:
                    ixn_end_sid["sid"] = self.multivalue(sid)
            # Endpoint behavior
            ep = end_sid.get("endpoint_behavior")
            if ep is not None and ep in ep_map:
                ixn_end_sid["endPointFunction"] = self.multivalue(ep_map[ep])
            # C-Flag
            c_flag = end_sid.get("c_flag")
            if c_flag is not None:
                ixn_end_sid["cFlag"] = self.multivalue(c_flag)
            # SID structure lengths (from parent locator)
            ixn_end_sid["locatorBlockLength"] = self.multivalue(block_len)
            ixn_end_sid["locatorNodeLength"] = self.multivalue(node_len)
            ixn_end_sid["functionLength"] = self.multivalue(func_len)
            ixn_end_sid["argumentLength"] = self.multivalue(arg_len)

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
        self._configure_srv6(otg_isis_router, ixn_isis_router)
        
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