from snappi_ixnetwork.device.base import Base

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
            }
        },
        "priority": "priority",
        "id": "vlanId"
    }

    _IP = {
        "address": "address",
        "gateway": "gatewayIp",
        "prefix": "prefix"
    }

    def __init__(self, ngpf):
        super(Ethernet, self).__init__()
        self._ngpf = ngpf

    def config(self, ethernet, ixn_dg):
        ixn_eth = self.create_node_elemet(
            ixn_dg, "ethernet", ethernet.get("name")
        )
        self._ngpf.set_device_info(ethernet, ixn_eth)
        self.configure_multivalues(ethernet, ixn_eth, Ethernet._ETHERNET)
        vlans = ethernet.get("vlans")
        if vlans is not None and len(vlans) > 0:
            ixn_eth["enableVlans"] = True
            ixn_eth["vlanCount"] = len(vlans)
            self._configure_vlan(ixn_eth, vlans)
        self._configure_ipv4(ixn_eth, ethernet)
        self._configure_ipv6(ixn_eth, ethernet)

    def _configure_vlan(self, ixn_eth, vlans):
        for vlan in vlans:
            ixn_vlan = self.create_node_elemet(
                ixn_eth, "vlan", vlan.get("name"))
            self.configure_multivalues(vlan, ixn_vlan, Ethernet._VLAN)

    def _configure_ipv4(self, ixn_eth, ethernet):
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
            ixn_ip = self.create_node_elemet(
                ixn_eth, "ipv4", ipv4_address.get("name")
            )
            self._ngpf.set_device_info(ipv4_address, ixn_ip)
            self.configure_multivalues(ipv4_address, ixn_ip, Ethernet._IP)

    def _configure_ipv6(self, ixn_eth, ethernet):
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
            ixn_ip = self.create_node_elemet(
                ixn_eth, "ipv6", ipv6_address.get("name")
            )
            self._ngpf.set_device_info(ipv6_address, ixn_ip)
            self.configure_multivalues(ipv6_address, ixn_ip, Ethernet._IP)

