from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Ethernet(Base):
    _ETHERNET = {
        "mac": "mac",
        "mtu": "mtu",
    }

    _VLAN = {
        "tpid": {
            "ixn_attr": "tpid",
            "enum_map": {
                "x8100": "ethertype8100",
                "x88a8": "ethertype88a8",
                "x9100": "ethertype9100",
                "x9200": "ethertype9200",
                "x9300": "ethertype9300",
            },
        },
        "priority": "priority",
        "id": "vlanId",
    }

    _IP = {"address": "address", "gateway": "gatewayIp", "prefix": "prefix"}

    _GATEWAY_MAC = {
        "gateway_mac": "manualGatewayMac",
    }

    def __init__(self, ngpf):
        super(Ethernet, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)

    def config(self, ethernet, ixn_dg):
        ixn_eth = self.create_node_elemet(
            ixn_dg, "ethernet", ethernet.get("name")
        )
        self._ngpf.set_device_info(ethernet, ixn_eth)
        self.configure_multivalues(ethernet, ixn_eth, Ethernet._ETHERNET)
        vlans = ethernet.get("vlans")
        if vlans is not None and len(vlans) > 0:
            ixn_eth["enableVlans"] = self.multivalue(True)
            ixn_eth["vlanCount"] = len(vlans)
            self._configure_vlan(ixn_eth, vlans)
        self._configure_ipv4(ixn_eth, ethernet)
        self._configure_ipv6(ixn_eth, ethernet)

    def _configure_vlan(self, ixn_eth, vlans):
        self.logger.debug("Configuring VLAN")
        for vlan in vlans:
            ixn_vlan = self.create_node_elemet(
                ixn_eth, "vlan", vlan.get("name")
            )
            self.configure_multivalues(vlan, ixn_vlan, Ethernet._VLAN)

    def _configure_ipv4(self, ixn_eth, ethernet):
        self.logger.debug("Configuring IPv4 interface")
        ipv4_addresses = ethernet.get("ipv4_addresses")
        if ipv4_addresses is None:
            return

        eth_name = ethernet.name
        if eth_name not in self._ngpf.ether_v4gateway_map:
            self._ngpf.ether_v4gateway_map[eth_name] = []

        for ipv4_address in ipv4_addresses:
            self._ngpf.ether_v4gateway_map[eth_name].append(
                ipv4_address.gateway
            )
            if self._ngpf.is_ip_allowed == False:
                ixn_ip = None
                self._ngpf.set_device_info(ipv4_address, ixn_ip)
            else:
                ixn_ip = self.create_node_elemet(
                    ixn_eth, "ipv4", ipv4_address.get("name")
                )
                self._ngpf.set_device_info(ipv4_address, ixn_ip)
                self.configure_multivalues(ipv4_address, ixn_ip, Ethernet._IP)
                if ipv4_address.gateway_mac.choice == "value":
                    self.configure_multivalues_with_choice(
                        ipv4_address, ixn_ip, Ethernet._GATEWAY_MAC
                    )

    def _configure_ipv6(self, ixn_eth, ethernet):
        self.logger.debug("Configuring IPv6 interface")
        ipv6_addresses = ethernet.get("ipv6_addresses")
        if ipv6_addresses is None:
            return

        eth_name = ethernet.name
        if eth_name not in self._ngpf.ether_v6gateway_map:
            self._ngpf.ether_v6gateway_map[eth_name] = []

        for ipv6_address in ipv6_addresses:
            self._ngpf.ether_v6gateway_map[eth_name].append(
                ipv6_address.gateway
            )
            if self._ngpf.is_ip_allowed == False:
                ixn_ip = None
                self._ngpf.set_device_info(ipv6_address, ixn_ip)
            else:
                ixn_ip = self.create_node_elemet(
                    ixn_eth, "ipv6", ipv6_address.get("name")
                )
                self._ngpf.set_device_info(ipv6_address, ixn_ip)
                self.configure_multivalues(ipv6_address, ixn_ip, Ethernet._IP)
                if ipv6_address.gateway_mac.choice == "value":
                    self.configure_multivalues_with_choice(
                        ipv6_address, ixn_ip, Ethernet._GATEWAY_MAC
                    )
