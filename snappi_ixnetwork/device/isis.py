from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Isis(Base):
    _ISIS = {
        "system_id": "systemId",
    }

    _NETWORK_TYPE = {
        "network_type": {
            "ixn_attr": "networkType",
            "enum_map": {"broadcast": "broadcast", "point_to_point": "pointpoint"}, # noqa
        },
    }

    _LEVEL_TYPE = {
        "level_type": {
            "ixn_attr": "levelType",
            "enum_map": {"level_1": "level1", "level_2": "level2", "level_1_2": "l1l2"}, # noqa
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
            "enum_map": {"internal": "internal", "external": "external"},
        }
    }

    _REDISTRIBUTION_TYPE = {
        "redistribution_type": {
            "ixn_attr": "redistribution",
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

    # Array of objects
    _MULTI_TOPOLOGY_IDS = {
        "mt_id": "mtId",
        "link_metric": "linkMetric",
    }

    # TBD
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
        # "p2p_hellos_to_unicast_mac": "",
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

    # TBD
    _ADJACENCY_SIDS = {}

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
        for interface in interfaces:
            ethernet_name = interface.get("eth_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            if not self._is_valid(ethernet_name):
                continue
            ixn_eth = self._ngpf.api.ixn_objects.get_object(ethernet_name)
            ixn_isis = self.create_node_elemet(
                ixn_eth, "isisL3Interface", isis.get("name")
            )
            self._ngpf.set_device_info(isis, ixn_isis)
            self._config_isis_interface(interface, ixn_isis)
            ixn_isis_router = self.create_node_elemet(
                self._ngpf.working_dg, "isisL3Router", isis.get("name")
            )
            # TODO : system ID, map interface and router
            self._config_isis_router(isis, ixn_isis_router)
            self._add_isis_route_range(isis, ixn_isis_router, ixn_isis)
            


    def _is_valid(self, ethernet_name):
        is_valid = True
        if is_valid:
            self.logger.debug("Isis validation success")
        else:
            self.logger.debug("Isis validation failure")
        return is_valid

    def _config_isis_interface(self, interface, ixn_isis):
        self.logger.debug("Configuring Isis interfaces")        
        # Metric
        metric = interface.get("metric")
        ixn_isis["interfaceMetric"] = self.multivalue(metric)
        # Network Type
        network_type = interface.get("network_type")
        self.configure_multivalues(network_type, ixn_isis, Isis._NETWORK_TYPE)
        # Level Type
        level_type = interface.get("level_type")
        self.configure_multivalues(level_type, ixn_isis, Isis._LEVEL_TYPE)
        # L1 Settings
        l1_settings = interface.get("l1_settings")
        if l1_settings is None:
            return
        self.logger.debug("priority %s hello_interval %s dead_interval %s " % (l1_settings.priority, l1_settings.hello_interval, l1_settings.dead_interval)) # noqa
        self.configure_multivalues(l1_settings, ixn_isis, Isis._L1_SETTINGS)
        # L2 Settings
        l2_settings = interface.get("l2_settings")
        if l2_settings is None:
            return
        self.logger.debug("priority %s hello_interval %s dead_interval %s " % (l2_settings.priority, l2_settings.hello_interval, l2_settings.dead_interval)) # noqa
        self.configure_multivalues(l2_settings, ixn_isis, Isis._L2_SETTINGS)
        # Multiple Topology IDs
        self._configure_multi_topo_id(interface, ixn_isis)
        # Traffic Engineering
        self._configure_traffic_engineering(interface, ixn_isis)
        # Authentication
        auth = interface.get("authentication")
        if auth is None:
            return
        self.logger.debug("authentication %s " % (auth.auth_type))
        self.configure_multivalues(auth, ixn_isis, Isis._AUTH_TYPE)
        # Advanced
        advanced = interface.get("advanced")
        if advanced is None:
            return
        self.logger.debug("auto_adjust_mtu %s auto_adjust_area %s auto_adjust_supported_protocols %s enable_3way_handshake %s p2p_hellos_to_unicast_mac %s " % (advanced.auto_adjust_mtu, advanced.auto_adjust_area, advanced.auto_adjust_supported_protocols, advanced.enable_3way_handshake, advanced.p2p_hellos_to_unicast_mac)) # noqa
        self.configure_multivalues(advanced, ixn_isis, Isis._ADVANCED_INTERFACE) # noqa
        # Link Protection
        link_protection = interface.get("link_protection")
        if link_protection is None:
            return
        self.logger.debug("")
        self.configure_multivalues(link_protection, ixn_isis, Isis._LINK_PROTECTION) # noqa
        # srlg values
        srlg_vals = interface.get("srlg_values")
        srlg_count =  len(srlg_vals)
        if srlg_count > 0:
            self.logger.debug("srlg values")
            ixn_isis["enableSRLG"] = True
            ixn_isis["srlgCount"] = srlg_count
            #TBD 
        # Adjacency Sids
        self._configure_adjacency_sids(interface, ixn_isis)     

    # TBD [array]
    def _configure_multi_topo_id(self, interface, ixn_isis):
        "Configuring multiple topology IDs"
    
    # TBD [array]
    def _configure_traffic_engineering(self, interface, ixn_isis):
        "Configuring Traffic Engineering"

    # TBD [array]
    def _configure_adjacency_sids(self, interface, ixn_isis):
        "Configuring Adjacency sids"  

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
        
    def _configure_isis_router_basic(self, otg_router_basic, ixn_isis_router):
        "Configuring ISIS router basic"
        ipv4_te_router_id = otg_router_basic.get("ipv4_te_router_id")
        if ipv4_te_router_id is not None:
            ixn_isis_router["enableTE"] = True
            ixn_isis_router["tERouterId"] = ipv4_te_router_id
        else:
            ixn_isis_router["enableTE"] = False
        hostname = otg_router_basic.get("hostname")
        if hostname is not None:
            ixn_isis_router["enableHostName"] = True
            ixn_isis_router["hostName"] = hostname
        else:
            ixn_isis_router["enableHostName"] = False 
        ixn_isis_router["discardLSPs"] = otg_router_basic.get("learned_lsp_filter") # noqa
        ixn_isis_router["enableWideMetric"] = otg_router_basic.get("enableWideMetric") # noqa

    def _configure_isis_router_advanced(self, otg_router_advanced, ixn_isis_router): # noqa
        "Configuring ISIS router advanced"
        ixn_isis_router["enableHelloPadding"] = otg_router_advanced.get("enable_hello_padding") # noqa
        ixn_isis_router["maxAreaAddresses"] = otg_router_advanced.get("max_area_addresses") # noqa
        # TBD join strings
        ixn_isis_router["areaAddresses"] = otg_router_advanced.get("area_addresses") # noqa
        ixn_isis_router["lSPRefreshRate"] = otg_router_advanced.get("lsp_refresh_rate") # noqa
        ixn_isis_router["lSPLifetime"] = otg_router_advanced.get("lsp_lifetime") # noqa
        ixn_isis_router["pSNPInterval"] = otg_router_advanced.get("psnp_interval") # noqa
        ixn_isis_router["cSNPInterval"] = otg_router_advanced.get("csnp_interval") # noqa
        ixn_isis_router["maxLSPSize"] = otg_router_advanced.get("max_lsp_size") # noqa
        ixn_isis_router["lSPorMGroupPDUMinTransmissionInterval"] = otg_router_advanced.get("lsp_mgroup_min_trans_interval") # noqa
        ixn_isis_router["attached"] = otg_router_advanced.get("enable_attached_bit") # noqa
        
    def _configure_isis_router_auth(self, otg_router_auth, ixn_isis_router): # noqa
        "Configuring ISIS router authentication"
        self.configure_multivalues(otg_router_auth, ixn_isis_router, Isis._ROUTER_AUTH) # noqa

    def _add_isis_route_range(self, otg_isis_router, ixn_isis_router, ixn_isis):
        "Configuring ISIS route range"
        


