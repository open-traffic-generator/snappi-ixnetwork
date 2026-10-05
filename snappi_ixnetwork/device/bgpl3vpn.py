from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.device.bgpevpn import BgpEvpn
from snappi_ixnetwork.device.utils import convert_as_values
from snappi_ixnetwork.logger import get_ixnet_logger


class BgpL3vpn(Base):
    """BGP/MPLS Layer 3 VPN (RFC 4364) - ``Bgp.L3vpn.Vrf`` mapping.

    See ``ai-snappi-ixnetwork/docs/design_snappi_ixnetwork_bgp_l3vpn.md``
    for the full design. Open Question 1 (multiple VRFs on one peer) is
    resolved as of 2026-09-29, confirmed against a live IxNetwork session -
    it is not supported: adding a second ``BgpVrf``/``BgpV6Vrf`` under the
    same peer is rejected by the real server with "BGP VRF and BGP VRF are
    not allowed to share the same stack." This is an IxNetwork NGPF
    emulation limitation, not an RFC 4364 restriction - a real PE carries
    every VRF's routes over one MP-BGP session. Section 3c's separate
    mixed-AFI question (can a single VRF on a V6Peer carry ``v4_routes``, or
    vice versa) is unrelated to this and still open.
    """

    # Same "as"/"as4"/"ip" enum bgpevpn.py already uses for its own RD
    # (BgpEvpn._config_evis) and RT (BgpEvpn._set_target) fields - RD and RT
    # share the same IxNetwork type enum, confirmed by that existing reuse.
    _ROUTE_TYPE_ENUM = BgpEvpn._COMMON_ROUTE_TYPE

    def __init__(self, ngpf):
        super(BgpL3vpn, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)

    def config(self, bgp_peer, ixn_bgp, vrf_node_type, bgp):
        """Configure ``bgp_peer.l3vpn_vrfs`` under *ixn_bgp*.

        *vrf_node_type* is ``"bgpVrf"`` for a ``bgpIpv4Peer`` parent or
        ``"bgpV6Vrf"`` for a ``bgpIpv6Peer`` parent - both are real,
        symmetric IxNetwork classes (design doc Section 2 preamble). *bgp*
        is the owning ``Bgp`` instance, used to reuse
        ``_configure_route_range_pool`` without a circular import between
        this module and ``bgp.py``.
        """
        vrfs = bgp_peer.get("l3vpn_vrfs")
        if not vrfs:
            return
        if len(vrfs) > 1:
            raise Exception(
                "%d l3vpn_vrfs configured on peer %r, but real IxNetwork "
                "does not support more than one BgpVrf/BgpV6Vrf per peer "
                "(confirmed live: \"BGP VRF and BGP VRF are not allowed to "
                "share the same stack\"). Model multiple VRFs (FR-V3) as "
                "separate BGP peer sessions, each with exactly one "
                "l3vpn_vrfs entry, instead."
                % (len(vrfs), bgp_peer.get("name"))
            )
        for vrf in vrfs:
            ixn_vrf = self.create_node_elemet(
                ixn_bgp, vrf_node_type, vrf.get("name")
            )
            self._config_vrf(vrf, ixn_vrf)
            self._config_vrf_routes(vrf, ixn_vrf, bgp)

    def _config_vrf(self, vrf, ixn_vrf):
        rt_export = vrf.get("route_target_export")
        if rt_export:
            ixn_vrf["numRtInExportRouteTargetList"] = len(rt_export)
            for rt in rt_export:
                ixn_export = self.create_node_elemet(
                    ixn_vrf, "bgpExportRouteTargetList"
                )
                self._set_target(ixn_export, rt)
        rt_import = vrf.get("route_target_import")
        if rt_import:
            # Matches BgpEvpn._config_evis's own precedent for the sibling
            # EVPN RT lists - not multivalue-wrapped there either.
            ixn_vrf["importRtListSameAsExportRtList"] = False
            ixn_vrf["numRtInImportRouteTargetList"] = len(rt_import)
            for rt in rt_import:
                ixn_import = self.create_node_elemet(
                    ixn_vrf, "bgpImportRouteTargetList"
                )
                self._set_target(ixn_import, rt)

    def _config_vrf_routes(self, vrf, ixn_vrf, bgp):
        """Build each of the VRF's route ranges, connected to *ixn_vrf*
        itself (not the peer) - confirmed 2026-09-29 against a live
        IxNetwork session: the GUI wires a VRF-attached route range's
        ``Ipv4PrefixPools.Connector.ConnectedTo`` at the ``BgpVrf`` object,
        not the peer. See design doc Section 3 / Open Question 1.
        """
        v4_routes = vrf.get("v4_routes")
        if v4_routes:
            for route in v4_routes:
                ixn_routes = bgp._configure_route_range_pool(
                    route, ixn_vrf, "ipv4PrefixPools", "bgpL3VpnRouteProperty"
                )
                for ixn_route in ixn_routes:
                    self._config_vpn_route_property(
                        route, ixn_route, route.get("mpls_labels")
                    )
        v6_routes = vrf.get("v6_routes")
        if v6_routes:
            for route in v6_routes:
                ixn_routes = bgp._configure_route_range_pool(
                    route,
                    ixn_vrf,
                    "ipv6PrefixPools",
                    "bgpV6L3VpnRouteProperty",
                )
                mpls_labels = route.get("service_binding").get("mpls_labels")
                for ixn_route in ixn_routes:
                    self._config_vpn_route_property(
                        route, ixn_route, mpls_labels
                    )

    def _config_vpn_route_property(self, route, ixn_route, mpls_labels):
        # route_distinguisher and mpls_labels are both carried on the route
        # range itself (required fields), not on the parent vrf - see
        # bgpl3vpnv4routerange.yaml / bgpl3vpnv6routerange.yaml.
        self._set_distinguisher(ixn_route, route.get("route_distinguisher"))
        self._set_label(ixn_route, mpls_labels)

    def _set_distinguisher(self, ixn_obj, rd):
        rd_type = rd.get("rd_type") or "as_2octet"
        rd_value = rd.get("rd_value") or "65101:1"
        ixn_type = BgpL3vpn._ROUTE_TYPE_ENUM.get(rd_type, "as")
        converted = convert_as_values([ixn_type], [rd_value])
        ixn_obj["distinguisherType"] = self.multivalue(
            rd_type, BgpL3vpn._ROUTE_TYPE_ENUM
        )
        ixn_obj["distinguisherAsNumber"] = self.multivalue(
            converted.as_num[0]
        )
        ixn_obj["distinguisherAssignedNumber"] = self.multivalue(
            converted.assign_num[0]
        )
        ixn_obj["distinguisherIpAddress"] = self.multivalue(
            converted.ip_addr[0]
        )

    def _set_target(self, ixn_obj, rt):
        rt_type = rt.get("rt_type") or "as_2octet"
        rt_value = rt.get("rt_value") or "65101:1"
        ixn_type = BgpL3vpn._ROUTE_TYPE_ENUM.get(rt_type, "as")
        converted = convert_as_values([ixn_type], [rt_value])
        ixn_obj["targetType"] = self.multivalue(
            rt_type, BgpL3vpn._ROUTE_TYPE_ENUM
        )
        ixn_obj["targetAsNumber"] = self.multivalue(converted.as_num[0])
        ixn_obj["targetAs4Number"] = self.multivalue(converted.as4_num[0])
        ixn_obj["targetIpAddress"] = self.multivalue(converted.ip_addr[0])
        ixn_obj["targetAssignedNumber"] = self.multivalue(
            converted.assign_num[0]
        )

    def _set_label(self, ixn_obj, mpls_label):
        ixn_obj["labelStart"] = self.multivalue(mpls_label.get("start"))
        ixn_obj["labelEnd"] = self.multivalue(mpls_label.get("max"))
        ixn_obj["labelStep"] = self.multivalue(mpls_label.get("step"))
