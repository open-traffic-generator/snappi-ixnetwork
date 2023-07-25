from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class LoopbackInt(Base):
    def __init__(self, ngpf):
        super(LoopbackInt, self).__init__()
        self._ngpf = ngpf
        self._ixn_parent_dgs = []
        self.logger = get_ixnet_logger(__name__)

    def config(self):
        self._ixn_parent_dgs = []
        for device in self._ngpf.api.snappi_config.devices:
            vxlan_source_int_list = self._get_vxlan_source_ints(device)
            ipv4_loopbacks = device.get("ipv4_loopbacks")
            if ipv4_loopbacks is not None:
                self._config_ipv4_loopbacks(
                    ipv4_loopbacks, device, vxlan_source_int_list
                )
            ipv6_loopbacks = device.get("ipv6_loopbacks")
            if ipv6_loopbacks is not None:
                self._config_ipv6_loopbacks(
                    ipv6_loopbacks, device, vxlan_source_int_list
                )
        return self._ixn_parent_dgs

    def _get_vxlan_source_ints(self, device):
        vxlan_source_int_list = []
        vxlan = device.get("vxlan")
        if vxlan is not None:
            v4_tunnels = vxlan.get("v4_tunnels")
            if v4_tunnels is not None and len(v4_tunnels) > 0:
                for v4_tunnel in v4_tunnels:
                    vxlan_source_int_list.append(
                        v4_tunnel.get("source_interface")
                    )

            v6_tunnels = vxlan.get("v6_tunnels")
            if v6_tunnels is not None and len(v6_tunnels) > 0:
                for v6_tunnel in v6_tunnels:
                    vxlan_source_int_list.append(
                        v6_tunnel.get("source_interface")
                    )
        return vxlan_source_int_list

    def _create_dg(self, loop_back, device):
        self.logger.debug("Configuring DG for loopback interface")
        eth_name = loop_back.get("eth_name")
        if eth_name not in self._ngpf.api.ixn_objects.names:
            raise Exception(
                "Ethernet %s not present within configuration" % eth_name
            )
        ixn_parent_dg = self._ngpf.api.ixn_objects.get_working_dg(eth_name)
        self._ixn_parent_dgs.append(ixn_parent_dg)
        ixn_dg = self.create_node_elemet(
            ixn_parent_dg,
            "deviceGroup",
            "loopback_{}".format(device.get("name")),
        )
        ixn_dg["multiplier"] = 1
        self._ngpf.working_dg = ixn_dg
        self._ngpf.set_device_info(device, ixn_dg)
        return ixn_dg

    def _config_ipv4_loopbacks(
        self, ipv4_loopbacks, device, vxlan_source_int_list
    ):
        self.logger.debug("Configuring IPv4 loopback interface")
        for ipv4_loopback in ipv4_loopbacks:
            ixn_dg = self._create_dg(ipv4_loopback, device)
            name = ipv4_loopback.get("name")
            if name in vxlan_source_int_list:
                ixn_eth = self.create_node_elemet(
                    ixn_dg, "ethernet", "eth {}".format(name)
                )
                ixn_v4 = self.create_node_elemet(ixn_eth, "ipv4", name)
                self._ngpf.set_device_info(ipv4_loopback, ixn_v4)
                ixn_v4["address"] = self.as_multivalue(
                    ipv4_loopback, "address"
                )
            else:
                ixn_v4lb = self.create_node_elemet(
                    ixn_dg, "ipv4Loopback", name
                )
                self._ngpf.set_device_info(ipv4_loopback, ixn_v4lb)
                ixn_v4lb["address"] = self.as_multivalue(
                    ipv4_loopback, "address"
                )

    def _config_ipv6_loopbacks(
        self, ipv6_loopbacks, device, vxlan_source_int_list
    ):
        self.logger.debug("Configuring IPv6 loopback interface")
        for ipv6_loopback in ipv6_loopbacks:
            ixn_dg = self._create_dg(ipv6_loopback, device)
            name = ipv6_loopback.get("name")
            if name in vxlan_source_int_list:
                ixn_eth = self.create_node_elemet(
                    ixn_dg, "ethernet", "eth {}".format(name)
                )
                ixn_v6 = self.create_node_elemet(ixn_eth, "ipv6", name)
                self._ngpf.set_device_info(ipv6_loopback, ixn_v6)
                ixn_v6["address"] = self.as_multivalue(
                    ipv6_loopback, "address"
                )
            else:
                ixn_v4lb = self.create_node_elemet(
                    ixn_dg, "ipv6Loopback", ipv6_loopback.get("name")
                )
                self._ngpf.set_device_info(ipv6_loopback, ixn_v4lb)
                ixn_v4lb["address"] = self.as_multivalue(
                    ipv6_loopback, "address"
                )
