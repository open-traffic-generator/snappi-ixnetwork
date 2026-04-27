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

    _SRGB_RANGE = {
        "starting_sid": "startSIDLabel",
        "range": "sIDCount",
    }

    _SRLB_RANGE = {
        "starting_sid": "startSIDLabel",
        "range": "sIDCount",
    }

    _SRV6_NODE_MSD = {
        "include_max_sl": "includeMaximumSLTLV",
        "max_sl": "maxSL",
        "include_max_end_pop_srh": "includeMaximumEndPopSrhTLV",
        "max_end_pop_srh": "maxEndPopSrh",
        "include_max_t_insert": "includeMaximumTInsertSrhTLV",
        "max_t_insert": "maxTInsert",
        "include_max_h_encaps": "includeMaximumHEncapMsd",
        "max_h_encaps": "maxHEncapMsd",
        "include_max_end_d_srh": "includeMaximumEndDSrhTLV",
        "max_end_d_srh": "maxEndD",
    }

    _SRV6_LOCATOR = {
        "algorithm": "algorithm",
        "metric": "metric",
        "d_flag": "dBit",
        "mt_id": "mtId",
    }

    _SRV6_LOCATOR_REDISTRIBUTION = {
        "redistribution_type": {
            "ixn_attr": "redistribution",
            "default_value": "up",
            "enum_map": {"up": "up", "down": "down"},
        }
    }

    _SRV6_LOCATOR_ADVERTISE_AS_PREFIX = {
        "route_metric": "routeMetric",
    }

    _SRV6_LOCATOR_ROUTE_ORIGIN = {
        "route_origin": {
            "ixn_attr": "routeOrigin",
            "default_value": "internal",
            "enum_map": {"internal": "internal", "external": "external"},
        }
    }

    # snappi endpoint_behavior → IxNetwork endPointFunction integer code (RFC 8986)
    _SRV6_ENDPOINT_FUNCTION = {
        "end": 1,
        "end_with_psp": 1,
        "end_with_usp": 1,
        "end_with_psp_usp": 1,
        "end_with_usd": 1,
        "end_with_psp_usd": 1,
        "end_with_usp_usd": 1,
        "end_with_psp_usp_usd": 1,
        "end_dt4": 14,
        "end_dt6": 12,
        "end_dt46": 13,
    }

    # snappi endpoint_behavior → IxNetwork Flags byte (PSP=0x80, USP=0x40, USD=0x20)
    _SRV6_ENDPOINT_FLAGS = {
        "end": 0,
        "end_with_psp": 0x80,
        "end_with_usp": 0x40,
        "end_with_psp_usp": 0xC0,
        "end_with_usd": 0x20,
        "end_with_psp_usd": 0xA0,
        "end_with_usp_usd": 0x60,
        "end_with_psp_usp_usd": 0xE0,
        "end_dt4": 0,
        "end_dt6": 0,
        "end_dt46": 0,
    }

    _PREFIX_ATTR_FLAGS = {
        "x_flag": "enableXFlag",
        "r_flag": "enableRFlag",
        "n_flag": "enableNFlag",
    }

    _PREFIX_SID_FLAGS = {
        "r_flag": "rFlag",
        "n_flag": "nFlag",
        "p_flag": "pFlag",
        "e_flag": "eFlag",
        "l_flag": "lFlag",
    }

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
        # Adjacency Sids
        self._configure_adjacency_sids(interface, ixn_isis)     

    # IB-TESTING
    def _configure_multi_topo_id(self, interface, ixn_isis):
        "Configuring multiple topology IDs"
        mt_ids = interface.get("multi_topology_ids")
        if mt_ids is None or len(mt_ids) == 0:
            return
        self.logger.debug("Configuring %d multi-topology ID(s)" % len(mt_ids))
        ixn_isis["enableMT"] = self.multivalue(True)
        ixn_isis["noOfMtIds"] = len(mt_ids)
        for mt in mt_ids:
            ixn_mt = self.create_node_elemet(ixn_isis, "isisMTIDList")
            ixn_mt["mtId"] = self.multivalue(mt.get("mt_id"))
            ixn_mt["linkMetric"] = self.multivalue(mt.get("link_metric"))

    # IB-TESTING
    def _configure_traffic_engineering(self, interface, ixn_isis):
        "Configuring Traffic Engineering"
        te_items = interface.get("traffic_engineering")
        if te_items is None or len(te_items) == 0:
            return
        self.logger.debug("Configuring %d traffic engineering profile(s)" % len(te_items))
        ixn_isis["noOfTeProfile"] = len(te_items)
        for te in te_items:
            ixn_te = self.create_node_elemet(
                ixn_isis, "isisTrafficEngineeringProfileList"
            )
            self.configure_multivalues(te, ixn_te, Isis._TRAFFIC_ENGINEERING)
            pb = te.get("priority_bandwidths")
            if pb is not None:
                self.configure_multivalues(pb, ixn_te, Isis._PRIORITY_BANDWIDTHS)

    # IB-TESTING            
    def _configure_adjacency_sids(self, interface, ixn_isis):
        "Configuring Adjacency sids"
        adj_sids = interface.get("adjacency_sids")
        if adj_sids is None or len(adj_sids) == 0:
            return
        self.logger.debug("Configuring %d adjacency SID(s)" % len(adj_sids))
        ixn_isis["enableAdjSID"] = self.multivalue(True)
        ixn_isis["adjSidCount"] = len(adj_sids)
        # IxNetwork exposes adj SID attributes as multivalues on the isisL3
        # node; configure from the first adjacency SID entry.
        adj_sid = adj_sids[0]
        choice = adj_sid.get("choice")
        if choice == "sid_values":
            sid_values = adj_sid.get("sid_values")
            if sid_values is not None and len(sid_values) > 0:
                ixn_isis["adjSID"] = self.multivalue(sid_values[0])
        else:
            # sid_indices (default)
            sid_indices = adj_sid.get("sid_indices")
            if sid_indices is not None and len(sid_indices) > 0:
                ixn_isis["adjSID"] = self.multivalue(sid_indices[0])
        b_flag = adj_sid.get("b_flag")
        if b_flag is not None:
            ixn_isis["bFlag"] = self.multivalue(b_flag)
        f_flag = adj_sid.get("f_flag")
        if f_flag is not None:
            ixn_isis["fFlag"] = self.multivalue(f_flag)
        l_flag = adj_sid.get("l_flag")
        if l_flag is not None:
            ixn_isis["lFlag"] = self.multivalue(l_flag)
        s_flag = adj_sid.get("s_flag")
        if s_flag is not None:
            ixn_isis["sFlag"] = self.multivalue(s_flag)
        p_flag = adj_sid.get("p_flag")
        if p_flag is not None:
            ixn_isis["pFlag"] = self.multivalue(p_flag)
        weight = adj_sid.get("weight")
        if weight is not None:
            ixn_isis["weight"] = self.multivalue(weight)

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
            self._configure_sr_capability(segment_routing, ixn_isis_router)
            srv6_locators = segment_routing.get("srv6_locators")
            if srv6_locators is not None and len(srv6_locators) > 0:
                self._configure_srv6_locators(srv6_locators, ixn_isis_router)
        
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

    def _configure_sr_capability(self, sr, ixn_isis_router):
        "Configuring ISIS Segment Routing capability on the router"
        self.logger.debug("Configuring ISIS SR capability")
        ixn_isis_router["enableSR"] = self.multivalue(True)
        rc = sr.get("router_capability")
        if rc is None:
            return
        # Router Capability ID (rtrcapId)
        choice = rc.get("choice")
        if choice == "custom_router_cap_id":
            custom_id = rc.get("custom_router_cap_id")
            if custom_id is not None:
                ixn_isis_router["rtrcapId"] = self.multivalue(custom_id)
        # S-bit and D-bit
        s_bit = rc.get("s_bit")
        if s_bit is not None:
            ixn_isis_router["sBit"] = self.multivalue(s_bit == "flood")
        d_bit = rc.get("d_bit")
        if d_bit is not None:
            ixn_isis_router["dBit"] = self.multivalue(d_bit == "down")
        # SR capability (SRGB + I/V flags)
        sr_cap = rc.get("sr_capability")
        if sr_cap is not None:
            self._configure_srgb_ranges(sr_cap, ixn_isis_router)
        # SR algorithms
        algorithms = rc.get("algorithms")
        if algorithms is not None and len(algorithms) > 0:
            self._configure_sr_algorithms(algorithms, ixn_isis_router)
        # SRLB ranges
        srlb_ranges = rc.get("srlb_ranges")
        if srlb_ranges is not None and len(srlb_ranges) > 0:
            self._configure_srlb_ranges(srlb_ranges, ixn_isis_router)
        # SRv6 node capability
        srv6_cap = rc.get("srv6_capability")
        if srv6_cap is not None:
            self._configure_srv6_node_capability(srv6_cap, ixn_isis_router)

    def _configure_srgb_ranges(self, sr_cap, ixn_isis_router):
        "Configuring SRGB ranges"
        srgb_ranges = sr_cap.get("srgb_ranges")
        if srgb_ranges is None or len(srgb_ranges) == 0:
            return
        self.logger.debug("Configuring %d SRGB range(s)" % len(srgb_ranges))
        ixn_isis_router["sRGBRangeCount"] = len(srgb_ranges)
        for srgb in srgb_ranges:
            ixn_srgb = self.create_node_elemet(
                ixn_isis_router, "isisSRGBRangeSubObjectsList"
            )
            self.configure_multivalues(srgb, ixn_srgb, Isis._SRGB_RANGE)
        # I-flag (IPv4 MPLS) and V-flag (IPv6 MPLS) from SR capability flags
        flags = sr_cap.get("flags")
        if flags is not None:
            ipv4_mpls = flags.get("ipv4_mpls")
            if ipv4_mpls is not None:
                ixn_isis_router["ipv4Flag"] = self.multivalue(ipv4_mpls)
            ipv6_mpls = flags.get("ipv6_mpls")
            if ipv6_mpls is not None:
                ixn_isis_router["ipv6Flag"] = self.multivalue(ipv6_mpls)

    def _configure_srlb_ranges(self, srlb_ranges, ixn_isis_router):
        "Configuring SRLB ranges"
        self.logger.debug("Configuring %d SRLB range(s)" % len(srlb_ranges))
        ixn_isis_router["advertiseSRLB"] = self.multivalue(True)
        ixn_isis_router["srlbDescriptorCount"] = len(srlb_ranges)
        for srlb in srlb_ranges:
            ixn_srlb = self.create_node_elemet(
                ixn_isis_router, "isisSRLBDescriptorList"
            )
            self.configure_multivalues(srlb, ixn_srlb, Isis._SRLB_RANGE)

    def _configure_sr_algorithms(self, algorithms, ixn_isis_router):
        "Configuring SR algorithms"
        self.logger.debug("Configuring %d SR algorithm(s)" % len(algorithms))
        ixn_isis_router["sRAlgorithmCount"] = len(algorithms)
        for algo_value in algorithms:
            ixn_algo = self.create_node_elemet(
                ixn_isis_router, "isisSRAlgorithmList"
            )
            ixn_algo["isisSrAlgorithm"] = self.multivalue(algo_value)

    def _configure_srv6_node_capability(self, srv6_cap, ixn_isis_router):
        "Configuring SRv6 node capability"
        self.logger.debug("Configuring SRv6 node capability")
        o_flag = srv6_cap.get("o_flag")
        if o_flag is not None:
            ixn_isis_router["oFlagOfSRv6Cap"] = self.multivalue(o_flag)
        c_flag = srv6_cap.get("c_flag")
        if c_flag is not None:
            ixn_isis_router["cFlagOfSRv6Cap"] = self.multivalue(c_flag)
        node_msds = srv6_cap.get("node_msds")
        if node_msds is not None:
            ixn_isis_router["advertiseNodeMsd"] = self.multivalue(True)
            self.configure_multivalues(
                node_msds, ixn_isis_router, Isis._SRV6_NODE_MSD
            )

    def _configure_srv6_locators(self, srv6_locators, ixn_isis_router):
        "Configuring SRv6 locators"
        self.logger.debug("Configuring %d SRv6 locator(s)" % len(srv6_locators))
        ixn_isis_router["locatorCount"] = len(srv6_locators)
        for locator in srv6_locators:
            ixn_locator = self.create_node_elemet(
                ixn_isis_router, "isisSRv6LocatorEntryList", locator.get("name")
            )
            ixn_locator["locator"] = self.multivalue(locator.get("locator"))
            ixn_locator["prefixLength"] = self.multivalue(
                locator.get("prefix_length")
            )
            self.configure_multivalues(locator, ixn_locator, Isis._SRV6_LOCATOR)
            self.configure_multivalues(
                locator, ixn_locator, Isis._SRV6_LOCATOR_REDISTRIBUTION
            )
            # Advertise locator as prefix
            advertise = locator.get("advertise_locator_as_prefix")
            if advertise is not None:
                ixn_locator["advertiseLocatorAsPrefix"] = self.multivalue(True)
                self.configure_multivalues(
                    advertise, ixn_locator, Isis._SRV6_LOCATOR_ADVERTISE_AS_PREFIX
                )
                self.configure_multivalues(
                    advertise, ixn_locator, Isis._SRV6_LOCATOR_ROUTE_ORIGIN
                )
            # End SIDs
            end_sids = locator.get("end_sids")
            if end_sids is not None and len(end_sids) > 0:
                ixn_locator["sidCount"] = len(end_sids)
                for end_sid in end_sids:
                    self._configure_srv6_end_sid(end_sid, ixn_locator)

    def _configure_srv6_end_sid(self, end_sid, ixn_locator):
        "Configuring SRv6 End SID"
        ixn_end_sid = self.create_node_elemet(ixn_locator, "isisSRv6EndSIDList")
        ixn_end_sid["sid"] = self.multivalue(end_sid.get("sid"))
        behavior = end_sid.get("endpoint_behavior")
        if behavior is not None:
            func_code = Isis._SRV6_ENDPOINT_FUNCTION.get(behavior, 1)
            flags_val = Isis._SRV6_ENDPOINT_FLAGS.get(behavior, 0)
            ixn_end_sid["endPointFunction"] = self.multivalue(func_code)
            ixn_end_sid["flags"] = self.multivalue(flags_val)
        c_flag = end_sid.get("c_flag")
        if c_flag is not None:
            ixn_end_sid["cFlag"] = self.multivalue(c_flag)
        sid_structure = end_sid.get("sid_structure")
        if sid_structure is not None:
            ixn_end_sid["includeSRv6SIDStructureSubSubTlv"] = self.multivalue(True)
            ixn_end_sid["locatorBlockLength"] = self.multivalue(
                sid_structure.get("lb_length")
            )
            ixn_end_sid["locatorNodeLength"] = self.multivalue(
                sid_structure.get("ln_length")
            )
            ixn_end_sid["functionLength"] = self.multivalue(
                sid_structure.get("function_length")
            )
            ixn_end_sid["argumentLength"] = self.multivalue(
                sid_structure.get("argument_length")
            )

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
        # Prefix attribute flags
        prefix_attr_enabled = otg_route.get("prefix_attr_enabled")
        if prefix_attr_enabled:
            ixn_route["includePrefixAttrFlags"] = self.multivalue(True)
            self.configure_multivalues(otg_route, ixn_route, Isis._PREFIX_ATTR_FLAGS)
        # Prefix SIDs (only first SID mapped per IxNetwork route property)
        prefix_sids = otg_route.get("prefix_sids")
        if prefix_sids is not None and len(prefix_sids) > 0:
            self._configure_prefix_sid(prefix_sids[0], ixn_route)

    def _configure_prefix_sid(self, prefix_sid, ixn_route):
        "Configuring ISIS Prefix SID on a route range"
        self.logger.debug("Configuring Prefix SID")
        ixn_route["configureSIDIndexLabel"] = self.multivalue(True)
        choice = prefix_sid.get("choice")
        if choice == "sid_values":
            sid_values = prefix_sid.get("sid_values")
            if sid_values is not None and len(sid_values) > 0:
                ixn_route["sIDIndexLabel"] = self.multivalue(sid_values[0])
        else:
            # sid_indices (default)
            sid_indices = prefix_sid.get("sid_indices")
            if sid_indices is not None and len(sid_indices) > 0:
                ixn_route["sIDIndexLabel"] = self.multivalue(sid_indices[0])
        self.configure_multivalues(prefix_sid, ixn_route, Isis._PREFIX_SID_FLAGS)
        algorithm = prefix_sid.get("algorithm")
        if algorithm is not None:
            ixn_route["algorithm"] = self.multivalue(algorithm)
