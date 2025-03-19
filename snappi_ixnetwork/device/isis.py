from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Isis(Base):
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

    _ROUTER_AUTH = {
        "ignore_receive_md5": "ignoreReceiveMD5",
        "area_auth": {
            "ixn_attr": "areaAuthenticationType",
            "enum_map": {"md5": "mD5", "password": "password"},    # noqa
        },
        "domain_auth": {
            "ixn_attr": "domainAuthenticationType",
            "enum_map": {"md5": "mD5", "password": "password"},    # noqa
        },
    }

    _INTERFACES = {
        "metric": "interfaceMetric",
        "network_type": {
            "ixn_attr": "networkType",
            "enum_map": {"broadcast": "broadcast", "point_to_point": "pointPoint"}, # noqa
        },
        "level_type": {
            "ixn_attr": "levelType",
            "enum_map": {"level_1": "level1", "level2": "pointPoint", "level_1_2": "l1L2"}, # noqa
        },
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

    # _MULTI_TOPOLOGY_IDS = {
    #     "mt_id": "",
    #     "link_metric": "",
    # }

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

    _AUTHENTICATION = {
        "auth_type": {
            "ixn_attr": "authType",
            "enum_map": {"md5": "mD5", "password": "password"},
        },
    }

    _INTERFACE_ADVANCED = {
        "auto_adjust_mtu": "autoAdjustMTU",
        "auto_adjust_area": "autoAdjustArea",
        "auto_adjust_supported_protocols": "autoAdjustSupportedProtocols",
        # "enable_3way_handshake": "",
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

    def __init__(self, ngpf):
        super(Isis, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._system_id = None

    def config(self, device):
        self.logger.debug("Configuring ISIS")
        isis = device.get("isis")
        if isis is None:
            return
        self._system_id = isis.get("system_id")
        self._config_ethernet_interfaces(device)

    def _is_valid(self, ethernet_name):
        is_valid = True
        if is_valid:
            self.logger.debug("Isis validation success")
        else:
            self.logger.debug("Isis validation failure")
        return is_valid
    
    def _config_ethernet_interfaces(self, device):
        self.logger.debug("Configuring Isis interfaces")
        isis = device.get("isis")
        ethernet_interfaces = isis.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return
        for ethernet_interface in ethernet_interfaces:
            ethernet_name = ethernet_interface.get("eth_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            if not self._is_valid(ethernet_name):
                continue
            # self._config_isisInf(device, ethernet_interface)