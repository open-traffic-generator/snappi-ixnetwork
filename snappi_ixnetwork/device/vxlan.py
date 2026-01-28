from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger
from snappi_ixnetwork.device.utils import namedtuple_with_defaults


class VXLAN(Base):
    SourceInterface = namedtuple_with_defaults(
        "SourceInterface", ("ipv4", "ipv6"), ([], [])
    )

    def __init__(self, ngpf):
        super(VXLAN, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._source_interfaces = VXLAN.SourceInterface()

    @property
    def source_interfaces(self):
        return self._source_interfaces

    def config(self, vxlan):
        v4_tunnels = vxlan.get("v4_tunnels")
        if v4_tunnels is not None and len(v4_tunnels) > 0:
            self._config_tunnels(v4_tunnels, "ipv4")

        v6_tunnels = vxlan.get("v6_tunnels")
        if v6_tunnels is not None and len(v6_tunnels) > 0:
            self._config_tunnels(v6_tunnels, "ipv6")

    def _store_source_interface(self, ixn_inter, ip_type):
        if ip_type == "ipv4":
            if ixn_inter not in self._source_interfaces.ipv4:
                self._source_interfaces.ipv4.append(ixn_inter)
        else:
            if ixn_inter not in self._source_interfaces.ipv6:
                self._source_interfaces.ipv6.append(ixn_inter)

    def _config_tunnels(self, tunnels, ip_version):
        """Configure VXLAN tunnels for IPv4 or IPv6.
        
        Args:
            tunnels: List of tunnel configurations
            ip_version: "ipv4" or "ipv6"
        """
        node_name = "vxlan" if ip_version == "ipv4" else "vxlanv6"
        multicast_attr = "{}_multicast".format(ip_version)
        
        for tunnel in tunnels:
            source_interface = tunnel.get("source_interface")
            ixnet_info = self._ngpf.api.ixn_objects.get(source_interface)
            ixn_inter = ixnet_info.ixnobject
            self._ngpf.working_dg = ixnet_info.working_dg
            ip_type = self._ngpf.api.get_device_encap(source_interface)
            if ip_type != ip_version:
                raise TypeError(
                    "source_interface {} should support {}".format(
                        source_interface, ip_version.upper()
                    )
                )
            self._store_source_interface(ixn_inter, ip_type)
            ixn_vxlan = self.create_node_elemet(
                ixn_inter, node_name, tunnel.get("name")
            )
            self._ngpf.set_device_info(tunnel, ixn_vxlan)
            ixn_vxlan["multiplier"] = 1
            ixn_vxlan["vni"] = self.as_multivalue(tunnel, "vni")
            destination_ip_mode = tunnel.destination_ip_mode
            if destination_ip_mode.choice == "unicast":
                ixn_vxlan["enableStaticInfo"] = True
                self._config_v4_unicast(
                    destination_ip_mode.unicast, ixn_vxlan, 
                    v4_tunnel=(ip_version == "ipv4")
                )
            else:
                ixn_vxlan["enableStaticInfo"] = False
                ixn_vxlan[multicast_attr] = self.as_multivalue(
                    destination_ip_mode.multicast, "address"
                )

    def _get_all_info(self, unicast):
        ixn_info_count = 0
        AllInfo = namedtuple_with_defaults(
            "AllInfo",
            (
                "remote_vtep_address",
                "suppress_arp",
                "remote_vm_mac",
                "remote_vm_ipv4",
            ),
            ([], [], [], []),
        )
        all_info = AllInfo()
        vteps = unicast.vteps
        for vtep in vteps:
            remote_vtep_address = vtep.get("remote_vtep_address")
            arp_suppression_cache = vtep.get("arp_suppression_cache")
            if len(arp_suppression_cache) == 0:
                all_info.remote_vtep_address.append(remote_vtep_address)
                all_info.suppress_arp.append(False)
                all_info.remote_vm_mac.append("00:00:00:00:00:00")
                all_info.remote_vm_ipv4.append("0.0.0.0")
                ixn_info_count += 1
                continue
            for cache in arp_suppression_cache:
                all_info.remote_vtep_address.append(remote_vtep_address)
                all_info.suppress_arp.append(True)
                all_info.remote_vm_mac.append(cache.get("remote_vm_mac"))
                all_info.remote_vm_ipv4.append(cache.get("remote_vm_ipv4"))
                ixn_info_count += 1
        return ixn_info_count, all_info

    def _config_v4_unicast(self, unicast, ixn_vxlan, v4_tunnel=True):
        ixn_info_count, all_info = self._get_all_info(unicast)
        ixn_vxlan["staticInfoCount"] = ixn_info_count
        if v4_tunnel is True:
            ixn_unicast = self.create_node_elemet(ixn_vxlan, "vxlanStaticInfo")
            ixn_unicast["remoteVtepIpv4"] = self.multivalue(
                all_info.remote_vtep_address
            )
        else:
            ixn_unicast = self.create_node_elemet(
                ixn_vxlan, "vxlanIPv6StaticInfo"
            )
            ixn_unicast["remoteVtepUnicastIpv6"] = self.multivalue(
                all_info.remote_vtep_address
            )
        ixn_unicast["suppressArp"] = self.multivalue(all_info.suppress_arp)
        ixn_unicast["remoteVmStaticMac"] = self.multivalue(
            all_info.remote_vm_mac
        )
        ixn_unicast["remoteVmStaticIpv4"] = self.multivalue(
            all_info.remote_vm_ipv4
        )
