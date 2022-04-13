from snappi_ixnetwork.device.base import Base


class BgpEvpn(Base):
    _VXLAN = {
        "ad_label": "adRouteLabel",
        "replication_type": {
            "ixn_attr": "multicastTunnelType",
            "enum_map": {
                "ingress_replication": "tunneltypeingressreplication"
            }
        }
    }

    _COMMON_ROUTE_TYPE = {
        "as_2octet": "as",
        "as_4octet": "as4",
        "ipv4_address": "ip"
    }

    def __init__(self, ngpf):
        super(BgpEvpn, self).__init__()
        self._ngpf = ngpf
        self._peer_class = None

    def config(self, bgp_peer, ixn_bgpv4):
        eth_segment_info = self.get_symmetric_nodes(
            [bgp_peer], "evpn_ethernet_segments"
        )
        if eth_segment_info.max_len == 0:
            return
        self._peer_class = bgp_peer.__class__.__name__
        if self._peer_class == "BgpV4Peer":
            ixn_bgpv4["ethernetSegmentsCountV4"] = eth_segment_info.max_len
            ixn_eth_segments = self.create_property(
                ixn_bgpv4, "bgpEthernetSegmentV4"
            )
        else:
            raise Exception("TBD")

        # self._config_eth_segment(eth_segment_info, ixn_eth_segments)
        # self._config_evis(eth_segment_info, ixn_bgpv4, ixn_eth_segments)

    def _config_eth_segment(self, eth_segment_info, ixn_eth_segments):
        df_election_info = eth_segment_info.get_tab("df_election")
        ixn_eth_segments["dfElectionTimer"] = df_election_info.get_multivalues(
            "election_timer"
        )


    def _config_evis(self, eth_segment_info, ixn_bgpv4, ixn_eth_segments):
        vxlan_info = eth_segment_info.get_symmetric_nodes("evis")
        ixn_eth_segments["evisCount"] = vxlan_info.max_len
        if self._peer_class == "BgpV4Peer":
            ixn_xvlan = self.create_node_elemet(
                ixn_bgpv4, "bgpIPv4EvpnVXLAN"
            )
        else:
            raise Exception("TBD")
        vxlan_info.config_values(ixn_xvlan, BgpEvpn._VXLAN)
        distinguisher_info = vxlan_info.get_tab("route_distinguisher")
        ixn_xvlan["rdType"] = distinguisher_info.get_multivalues(
            "rd_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
        )
        ixn_xvlan["rdASNumber"] = self.multivalue([
            self.asdot2plain(v) for v in distinguisher_info.get_values("rd_value")
        ])

        exports_info_list = vxlan_info.get_group_nodes("route_target_export")
        if len(exports_info_list) > 0:
            ixn_xvlan["numRtInExportRouteTargetList"] = len(
                exports_info_list
            )
        for exports_info in exports_info_list:
            ixn_exports = self.create_node_elemet(ixn_xvlan, "bgpExportRouteTargetList")
            ixn_exports["targetType"] = exports_info.get_multivalues(
                "rt_type", enum_map=BgpEvpn._COMMON_ROUTE_TYPE
            )





