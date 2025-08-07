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
        #TBD 
        # Adjacency Sids
        self._configure_adjacency_sids(interface, ixn_isis)     

    # TBD 
    def _configure_multi_topo_id(self, interface, ixn_isis):
        "Configuring multiple topology IDs"
    
    # TBD 
    def _configure_traffic_engineering(self, interface, ixn_isis):
        "Configuring Traffic Engineering"

    # TBD 
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