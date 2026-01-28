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
                self._config_loopbacks(
                    ipv4_loopbacks, device, vxlan_source_int_list, "ipv4"
                )
            ipv6_loopbacks = device.get("ipv6_loopbacks")
            if ipv6_loopbacks is not None:
                self._config_loopbacks(
                    ipv6_loopbacks, device, vxlan_source_int_list, "ipv6"
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

    def _config_loopbacks(
        self, loopbacks, device, vxlan_source_int_list, ip_version
    ):
        """Configure loopback interfaces for IPv4 or IPv6.
        
        Args:
            loopbacks: List of loopback configurations
            device: Device configuration
            vxlan_source_int_list: List of VXLAN source interface names
            ip_version: "ipv4" or "ipv6"
        """
        self.logger.debug("Configuring %s loopback interface" % ip_version.upper())
        node_name = ip_version
        loopback_node_name = "{}Loopback".format(ip_version)
        
        for loopback in loopbacks:
            ixn_dg = self._create_dg(loopback, device)
            name = loopback.get("name")
            if name in vxlan_source_int_list:
                ixn_eth = self.create_node_elemet(
                    ixn_dg, "ethernet", "eth {}".format(name)
                )
                ixn_ip = self.create_node_elemet(ixn_eth, node_name, name)
                self._ngpf.set_device_info(loopback, ixn_ip)
                ixn_ip["address"] = self.as_multivalue(
                    loopback, "address"
                )
            else:
                ixn_lb = self.create_node_elemet(
                    ixn_dg, loopback_node_name, name
                )
                self._ngpf.set_device_info(loopback, ixn_lb)
                ixn_lb["address"] = self.as_multivalue(
                    loopback, "address"
                )
