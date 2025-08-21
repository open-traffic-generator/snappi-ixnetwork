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

    _P2P_INGRESS_LSPS = {
        "tunnel_id": "tunnelId",
        "lsp_id": "lspId",
        "refresh_interval": "refreshInterval",
        "timeout_multiplier": "timeoutMultiplier",
        "backup_lsp_id": "backupLspId",
        "lsp_switchover_delay": "lspSwitchOverDelayTime",

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
    