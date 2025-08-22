from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Rsvp(Base):
    _BGP = {
        "neighbor_ip": "dutIp",
    }

    _RESERVATION_STYLE = {
        "reservation_style": {
            "ixn_attr": "reservationStyle",
            "default_value": "shared_explicit",
            "enum_map": {
                "shared_explicit": "se",
                "fixed_filter": "ff",
                "auto": "auto",
            },
        },
    }

    _PREPEND_NEIGHBOR_IP_TYPE = {
        "prepend_neighbor_ip": {
            "ixn_attr": "prependDutToEro",
            "default_value": "prepend_loose",
            "enum_map": {
                "dont_prepend": "dontprepend",
                "prepend_loose": "prependloose",
                "prepend_strict": "prependstrict",
            },
        },
    }

    _ERO_SUBOBJECT_TYPE = {
        "type": {
            "ixn_attr": "type",
            "default_value": "ipv4",
            "enum_map": {
                "ipv4": "ip",
                "as_number": "as",
            },
        },
    }

    _ERO_SUBOBJECT_HOP_TYPE = {
        "hop_type": {
            "ixn_attr": "looseFlag",
            "default_value": "loose",
            "enum_map": {
                "strict": "false",
                "loose": "true",
            },
        },
    } 

    def __init__(self, ngpf):
        super(Rsvp, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._rsvp_router_name = None

    def config(self, device):
        self.logger.debug("Configuring RSVP")
        rsvp = device.get("rsvp")
        if rsvp is None:
            return
        self._rsvp_router_name = rsvp.get("name")
        self._add_rsvp_router(rsvp)

    def _add_rsvp_router(self, rsvp):
        self.logger.debug("Configuring RSVP Router")
        interfaces = rsvp.get("ipv4_interfaces")
        if interfaces is None:
            return
        self._configure_rsvp_interfaces(interfaces, rsvp.name)
        lsp_ip_interfaces = rsvp.get("lsp_ipv4_interfaces")
        if lsp_ip_interfaces is None:
            return
        self._configure_rsvp_lsps(lsp_ip_interfaces, rsvp.name)
    
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

    def _configure_rsvp_interfaces(self, interfaces, rsvp_name):
        self.logger.debug("Configuring RSVP Interfaces")
        for interface in interfaces:
            ipv4_name = interface.get("ipv4_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ipv4_name
            )
            if not self._is_valid(ipv4_name):
                continue
            ixn_ipv4 = self._ngpf.api.ixn_objects.get_object(ipv4_name)
            ixn_rsvp = self.create_node_elemet(
                ixn_ipv4, "rsvpteIf", rsvp_name
            )
            self._ngpf.set_device_info(interface, ixn_rsvp)
            neighbor_ip = interface.get("neighbor_ip")
            ixn_rsvp["dutIp"] = self.multivalue(neighbor_ip)
            label_space_start = interface.get("label_space_start")
            ixn_rsvp["labelSpaceStart"] = self.multivalue(label_space_start)
            label_space_end = interface.get("label_space_end")
            ixn_rsvp["labelSpaceEnd"] = self.multivalue(label_space_end)
            enable_refresh_reduction = interface.get("enable_refresh_reduction")  # noqa
            ixn_rsvp["enableRefreshReduction"] = self.multivalue(enable_refresh_reduction)  # noqa
            summary_refresh_interval = interface.get("summary_refresh_interval")  # noqa
            ixn_rsvp["summaryRefreshInterval"] = self.multivalue(summary_refresh_interval)  # noqa
            send_bundle = interface.get("send_bundle")  
            ixn_rsvp["enableBundleMessageSending"] = self.multivalue(send_bundle)  # noqa
            bundle_threshold = interface.get("bundle_threshold")  
            ixn_rsvp["bundleMessageThresholdTime"] = self.multivalue(bundle_threshold)  # noqa
            enable_hello = interface.get("enable_hello")  
            ixn_rsvp["enableHelloExtension"] = self.multivalue(enable_hello)  # noqa
            hello_interval = interface.get("hello_interval")  
            ixn_rsvp["helloInterval"] = self.multivalue(hello_interval)  # noqa
            timeout_multiplier = interface.get("timeout_multiplier")  
            ixn_rsvp["helloTimeoutMultiplier"] = self.multivalue(timeout_multiplier)  # noqa
            
    def _configure_rsvp_lsps(self, lsp_interfaces, rsvp_name):
        self.logger.debug("Configuring RSVP LSP IPv4 Interfaces")
        for interface in lsp_interfaces:
            ipv4_name = interface.get("ipv4_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ipv4_name
            )
            if not self._is_valid(ipv4_name):
                continue
            ixn_ipv4 = self._ngpf.api.ixn_objects.get_object(ipv4_name)
            ixn_rsvp = self.create_node_elemet(
                ixn_ipv4, "rsvpteLsps", rsvp_name + "-" + "Lsps"
            )
            self._ngpf.set_device_info(interface, ixn_rsvp)
            if interface.get("p2p_egress_ipv4_lsps") is not None:
                self._configure_p2p_egress_lsps(ixn_rsvp, interface, rsvp_name)
            else:
                ixn_rsvp["enableP2PEgress"] = self.multivalue(False)
            p2p_ingress_lsp = interface.get("p2p_ingress_ipv4_lsps")
            if p2p_ingress_lsp is not None:
                ingress_lsp_count = len(p2p_ingress_lsp)
                if ingress_lsp_count > 0:
                    ixn_rsvp["ingressP2PLsps"] = self.multivalue(ingress_lsp_count) # noqa
                    self._configure_p2p_ingress_lsps(ixn_rsvp, p2p_ingress_lsp, rsvp_name)  # noqa
            
    def _configure_p2p_egress_lsps(self, ixn_rsvp, p2p_egress_lsps, rsvp_name):
        self.logger.debug("Configuring RSVP P2P Egress IPv4 Interfaces")
        ixn_rsvp_egress_lsp = self.create_node_elemet( 
            ixn_rsvp, "rsvpP2PEgressLsps", rsvp_name + "-" + "egress" + "Lsps" # noqa
        )
        self._ngpf.set_device_info(p2p_egress_lsps, ixn_rsvp_egress_lsp)
        refresh_interval = p2p_egress_lsps.get("refresh_interval")
        ixn_rsvp_egress_lsp["refreshInterval"] = self.multivalue(refresh_interval) # noqa
        timeout_multiplier = p2p_egress_lsps.get("timeout_multiplier")
        ixn_rsvp_egress_lsp["timeoutMultiplier"] = self.multivalue(timeout_multiplier) # noqa
        reservation_style = p2p_egress_lsps.get("reservation_style")
        mapped_type = Rsvp._RESERVATION_STYLE["reservation_style"]["enum_map"][reservation_style]   # noqa
        ixn_rsvp_egress_lsp["reservationStyle"] = self.multivalue(mapped_type)
        enable_fixed_label = p2p_egress_lsps.get("enable_fixed_label")
        ixn_rsvp_egress_lsp["enableFixedLabelForReservations"] = self.multivalue(enable_fixed_label) # noqa
        fixed_label_value = p2p_egress_lsps.get("fixed_label_value")
        ixn_rsvp_egress_lsp["labelValue"] = self.multivalue(fixed_label_value) # noqa


    def _configure_p2p_ingress_lsps(self, ixn_rsvp, p2p_ingress_lsps, rsvp_name): # noqa
        self.logger.debug("Configuring RSVP P2P Ingress IPv4 Interfaces")
        ixn_rsvp_ingress_lsp = self.create_node_elemet( 
            ixn_rsvp, "rsvpP2PIngressLsps", rsvp_name + "-" + "ingress" + "Lsps" # noqa
        )
        self._ngpf.set_device_info(p2p_ingress_lsps, ixn_rsvp_ingress_lsp)
        for ingress_lsp in p2p_ingress_lsps:
            lsp_name = rsvp_name + "-" + ingress_lsp.get("remote_address") + "-" + ingress_lsp.get("tunnel_id") + "-" + ingress_lsp.get("lsp_id") # noqa
            ixn_rsvp_ingress_lsp["name"] = self.multivalue(lsp_name)
            remote_address = ingress_lsp.get("remote_address")
            ixn_rsvp_ingress_lsp["remoteIp"] = self.multivalue(remote_address)
            tunnel_id = ingress_lsp.get("tunnel_id")
            ixn_rsvp_ingress_lsp["tunnelId"] = self.multivalue(tunnel_id)
            lsp_id = ingress_lsp.get("lsp_id")
            ixn_rsvp_ingress_lsp["lspId"] = self.multivalue(lsp_id)
            refresh_interval = ingress_lsp.get("refresh_interval")
            ixn_rsvp_ingress_lsp["refreshInterval"] = self.multivalue(refresh_interval) # noqa
            timeout_multiplier = ingress_lsp.get("timeout_multiplier")
            ixn_rsvp_ingress_lsp["timeoutMultiplier"] = self.multivalue(timeout_multiplier) # noqa
            backup_lsp_id = ingress_lsp.get("backup_lsp_id")
            ixn_rsvp_ingress_lsp["backupLspId"] = self.multivalue(backup_lsp_id) # noqa
            lsp_switchover_delay = ingress_lsp.get("lsp_switchover_delay")
            ixn_rsvp_ingress_lsp["lspSwitchOverDelayTime"] = self.multivalue(lsp_switchover_delay) # noqa
            session_attribute = ingress_lsp.get("session_attribute")
            if session_attribute is not None:
                auto_generate_session_name = session_attribute.get("auto_generate_session_name") # noqa
                ixn_rsvp_ingress_lsp["autoGenerateSessionName"] = self.multivalue(auto_generate_session_name) # noqa
                session_name = session_attribute.get("session_name") 
                ixn_rsvp_ingress_lsp["sessionName"] = self.multivalue(session_name) # noqa
                setup_priority = session_attribute.get("setup_priority") 
                ixn_rsvp_ingress_lsp["setupPriority"] = self.multivalue(setup_priority) # noqa
                holding_priority = session_attribute.get("holding_priority") 
                ixn_rsvp_ingress_lsp["holdingPriority"] = self.multivalue(holding_priority) # noqa
                local_protection_desired = session_attribute.get("local_protection_desired") # noqa
                ixn_rsvp_ingress_lsp["localProtectionDesired"] = self.multivalue(local_protection_desired) # noqa
                label_recording_desired = session_attribute.get("label_recording_desired") # noqa
                ixn_rsvp_ingress_lsp["labelRecordingDesired"] = self.multivalue(label_recording_desired) # noqa
                se_style_desired = session_attribute.get("se_style_desired") # noqa
                ixn_rsvp_ingress_lsp["seStyleDesired"] = self.multivalue(se_style_desired) # noqa
                bandwidth_protection_desired = session_attribute.get("bandwidth_protection_desired") # noqa
                ixn_rsvp_ingress_lsp["bandwidthProtectionDesired"] = self.multivalue(bandwidth_protection_desired) # noqa
                node_protection_desired = session_attribute.get("node_protection_desired") # noqa
                ixn_rsvp_ingress_lsp["nodeProtectionDesired"] = self.multivalue(node_protection_desired) # noqa
                resource_affinity_type = session_attribute.get("resource_affinities") # noqa
                if resource_affinity_type is not None:
                    exclude_any = resource_affinity_type.get("exclude_any") 
                    ixn_rsvp_ingress_lsp["excludeAny"] = self.multivalue(exclude_any) # noqa
                    include_any = resource_affinity_type.get("include_any") 
                    ixn_rsvp_ingress_lsp["includeAny"] = self.multivalue(include_any) # noqa
                    include_all = resource_affinity_type.get("include_all") 
                    ixn_rsvp_ingress_lsp["includeAll"] = self.multivalue(include_all) # noqa
            tspec = ingress_lsp.get("tspec")
            if tspec is not None:
                token_bucket_rate = tspec.get("token_bucket_rate") 
                ixn_rsvp_ingress_lsp["tokenBucketRate"] = self.multivalue(token_bucket_rate) # noqa
                token_bucket_size = tspec.get("token_bucket_size") 
                ixn_rsvp_ingress_lsp["tokenBucketSize"] = self.multivalue(token_bucket_size) # noqa
                peak_data_rate = tspec.get("peak_data_rate") 
                ixn_rsvp_ingress_lsp["peakDataRate"] = self.multivalue(peak_data_rate) # noqa
                minimum_policed_unit = tspec.get("minimum_policed_unit") # noqa
                ixn_rsvp_ingress_lsp["minimumPolicedUnit"] = self.multivalue(minimum_policed_unit) # noqa
                maximum_policed_unit = tspec.get("maximum_policed_unit") # noqa
                ixn_rsvp_ingress_lsp["maximumPacketSize"] = self.multivalue(maximum_policed_unit) # noqa
            fast_reroute = ingress_lsp.get("fast_reroute")
            if fast_reroute is not None:
                setup_priority = fast_reroute.get("setup_priority") 
                ixn_rsvp_ingress_lsp["setupPriority"] = self.multivalue(setup_priority) # noqa
                holding_priority = fast_reroute.get("holding_priority") 
                ixn_rsvp_ingress_lsp["holdingPriority"] = self.multivalue(holding_priority) # noqa
                hop_limit = fast_reroute.get("hop_limit") 
                ixn_rsvp_ingress_lsp["hopLimit"] = self.multivalue(hop_limit)
                bandwidth = fast_reroute.get("bandwidth") 
                ixn_rsvp_ingress_lsp["bandwidth"] = self.multivalue(bandwidth)
                exclude_any = fast_reroute.get("exclude_any") 
                ixn_rsvp_ingress_lsp["fastRerouteExcludeAny"] = self.multivalue(exclude_any) # noqa
                include_any = fast_reroute.get("include_any") 
                ixn_rsvp_ingress_lsp["fastRerouteIncludeAny"] = self.multivalue(include_any) # noqa
                include_all = fast_reroute.get("include_all") 
                ixn_rsvp_ingress_lsp["fastRerouteIncludeAll"] = self.multivalue(include_all) # noqa
                one_to_one_backup_desired = fast_reroute.get("one_to_one_backup_desired") # noqa
                ixn_rsvp_ingress_lsp["oneToOneBackupDesired"] = self.multivalue(one_to_one_backup_desired) # noqa
                facility_backup_desired = fast_reroute.get("facility_backup_desired") # noqa
                ixn_rsvp_ingress_lsp["facilityBackupDesired"] = self.multivalue(facility_backup_desired) # noqa
            ero = ingress_lsp.get("ero")
            if ero is not None:
                prepend_neighbor_ip = ero.get("prepend_neighbor_ip")
                mapped_level = Rsvp._PREPEND_NEIGHBOR_IP_TYPE["prepend_neighbor_ip"]["enum_map"][prepend_neighbor_ip]   # noqa
                ixn_rsvp_ingress_lsp["prependDutToEro"] = self.multivalue(mapped_level) # noqa
                prefix_length = ero.get("prefix_length") 
                ixn_rsvp_ingress_lsp["prefixLength"] = self.multivalue(prefix_length) # noqa
                # TBD: ERO Sub-objects




