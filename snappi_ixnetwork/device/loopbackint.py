from snappi_ixnetwork.device.base import Base


class LoopbackInt(Base):
    def __init__(self, ngpf):
        super(LoopbackInt, self).__init__()
        self._ngpf = ngpf
        self._ixn_parent_dgs = []

    def config(self):
        self._ixn_parent_dgs = []
        for device in self._ngpf.api.snappi_config.devices:
            ipv4_loopbacks = device.get("ipv4_loopbacks")
            if ipv4_loopbacks is not None:
                self._config_ipv4_loopbacks(ipv4_loopbacks, device)
            ipv6_loopbacks = device.get("ipv6_loopbacks")
            if ipv6_loopbacks is not None:
                self._config_ipv6_loopbacks(ipv6_loopbacks, device)
        for ix_parent_dg in self._ixn_parent_dgs:
            self._ngpf.compactor.compact(ix_parent_dg.get(
                "deviceGroup"
            ))

    def _create_dg(self, loop_back, device):
        eth_name = loop_back.get("eth_name")
        if eth_name not in self._ngpf.api.ixn_objects.names:
            raise Exception("Ethernet %s not present within configuration"
                            % eth_name)
        ixn_parent_dg = self._ngpf.api.ixn_objects.get_working_dg(
            eth_name
        )
        self._ixn_parent_dgs.append(ixn_parent_dg)
        ixn_dg = self.create_node_elemet(
            ixn_parent_dg, "deviceGroup", "loopback_{}".format(device.get("name"))
        )
        ixn_dg["multiplier"] = 1
        self._ngpf.working_dg = ixn_dg
        return ixn_dg

    def _config_ipv4_loopbacks(self, ipv4_loopbacks, device):
        for ipv4_loopback in ipv4_loopbacks:
            ixn_dg = self._create_dg(ipv4_loopback, device)
            ixn_v4lb = self.create_node_elemet(
                ixn_dg, "ipv4Loopback", ipv4_loopback.get("name")
            )
            self._ngpf.set_device_info(ipv4_loopback, ixn_v4lb)
            ixn_v4lb["address"] = self.as_multivalue(ipv4_loopback, "address")

    def _config_ipv6_loopbacks(self, ipv6_loopbacks, device):
        for ipv6_loopback in ipv6_loopbacks:
            ixn_dg = self._create_dg(ipv6_loopback, device)
            ixn_v4lb = self.create_node_elemet(
                ixn_dg, "ipv6Loopback", ipv6_loopback.get("name")
            )
            self._ngpf.set_device_info(ipv6_loopback, ixn_v4lb)
            ixn_v4lb["address"] = self.as_multivalue(ipv6_loopback, "address")


