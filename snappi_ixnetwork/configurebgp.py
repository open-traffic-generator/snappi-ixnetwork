# import re
# import socket, struct
# from collections import namedtuple
#
#
# class ConfigureBgp(object):
#     _BGP_AS_SET_MODE = {
#         "do_not_include_as": "dontincludelocalas",
#         "include_as_seq": "includelocalasasasseq",
#         "include_as_set": "includelocalasasasset",
#         "include_as_seq_confed": "includelocalasasasseqconfederation",
#         "include_as_set_confed": "includelocalasasassetconfederation",
#         "prepend_as_to_first_segment": "prependlocalastofirstsegment",
#     }
#
#     _BGP_AS_MODE = {
#         "do_not_include_local_as": "dontincludelocalas",
#         "include_as_seq": "includelocalasasasseq",
#         "include_as_set": "includelocalasasasset",
#         "include_as_confed_seq": "includelocalasasasseqconfederation",
#         "include_as_confed_set": "includelocalasasassetconfederation",
#         "prepend_to_first_segment": "prependlocalastofirstsegment",
#     }
#
#     _BGP_SEG_TYPE = {
#         "as_seq": "asseq",
#         "as_set": "asset",
#         "as_confed_seq": "asseqconfederation",
#         "as_confed_set": "assetconfederation",
#     }
#
#     _BGP_COMMUNITY_TYPE = {
#         "manual_as_number": "manual",
#         "no_export": "noexport",
#         "no_advertised": "noadvertised",
#         "no_export_subconfed": "noexport_subconfed",
#         "llgr_stale": "llgr_stale",
#         "no_llgr": "no_llgr",
#     }
#
#     _BGP_SR_TE = {
#         "policy_type": {"ixn_attr": "policyType", "default": "ipv4"},
#         "distinguisher": {"ixn_attr": "distinguisher", "default": "1"},
#         "color": {"ixn_attr": "policyColor", "default": "101"},
#         "ipv4_endpoint": {"ixn_attr": "endPointV4", "default": "0.0.0.0"},
#         "ipv6_endpoint": {
#             "ixn_attr": "endPointV6",
#             "default": "0:0:0:0:0:0:0:0",
#         },
#     }
#
#     _SRTE_NEXT_HOP = {
#         "next_hop_mode": {
#             "ixn_attr": "setNextHop",
#             "default": "sameaslocalip",
#             "enum_map": {"local_ip": "sameaslocalip", "manual": "manually"},
#         },
#         "next_hop_address_type": {
#             "ixn_attr": "setNextHopIpType",
#             "default": "ipv4",
#         },
#         "ipv4_address": {"ixn_attr": "ipv4NextHop", "default": "0.0.0.0"},
#         "ipv6_address": {"ixn_attr": "ipv6NextHop", "default": "::"},
#     }
#
#     _SRTE_ADDPATH = {"path_id": {"ixn_attr": "addPathId", "default": "1"}}
#
#     _SRTE_AS_PATH = {
#         "override_peer_as_set_mode": {
#             "ixn_attr": "overridePeerAsSetMode",
#             "default": False,
#         },
#         "as_set_mode": {
#             "ixn_attr": "asSetMode",
#             "default": "includelocalasasasseq",
#             "enum_map": _BGP_AS_MODE,
#         },
#     }
#
#     _SRTE_ASPATH_SEGMENT = {
#         "segment_type": {
#             "ixn_attr": "segmentType",
#             "default": "asset",
#             "enum_map": _BGP_SEG_TYPE,
#         }
#     }
#
#     _REMOTE_ENDPOINT_SUB_TLV = {
#         "as_number": {"ixn_attr": "as4Number", "default": "0"},
#         "address_family": {"ixn_attr": "addressFamily", "default": "ipv4"},
#         "ipv4_address": {
#             "ixn_attr": "remoteEndpointIPv4",
#             "default": "0.0.0.0",
#         },
#         "ipv6_address": {"ixn_attr": "remoteEndpointIPv6", "default": "::"},
#     }
#
#     _PREFERENCE_SUB_TLV = {
#         "preference": {"ixn_attr": "prefValue", "default": "0"}
#     }
#
#     _BINDING_SUB_TLV = {
#         "binding_sid_type": {
#             "ixn_attr": "bindingSIDType",
#             "default": "nobinding",
#             "enum_map": {
#                 "no_binding": "nobinding",
#                 "four_octet_sid": "sid4",
#                 "ipv6_sid": "ipv6sid",
#             },
#         },
#         "four_octet_sid": {"ixn_attr": "SID4Octet", "default": "0"},
#         "bsid_as_mpls_label": {"ixn_attr": "useAsMPLSLabel", "default": False},
#         "ipv6_sid": {"ixn_attr": "IPv6SID", "default": "::"},
#         "s_flag": {"ixn_attr": "sflag", "default": False},
#         "i_flag": {"ixn_attr": "iflag", "default": False},
#         "remaining_flag_bits": {
#             "ixn_attr": "remainingBits",
#             "default": "0x01",
#         },
#     }
#
#     _ENLP_SUB_TLV = {
#         "explicit_null_label_policy": {
#             "ixn_attr": "ENLPValue",
#             "default": "4",
#             "enum_map": {
#                 "reserved_enlp": "0",
#                 "push_ipv4_enlp": "1",
#                 "push_ipv6_enlp": "2",
#                 "push_ipv4_ipv6_enlp": "3",
#                 "do_not_push_enlp": "4",
#             },
#         }
#     }
#
#     _POLICIES_SEGMENT_LIST = {
#         "segment_weight": {"ixn_attr": "weight", "default": "200"}
#     }
#
#     _SEGMENTS = {
#         "segment_type": {
#             "ixn_attr": "segmentType",
#             "default": "mplssid",
#             "enum_map": {"mpls_sid": "mplssid", "ipv6_sid": "ipv6sid"},
#         },
#         "mpls_label": {"ixn_attr": "label", "default": "16"},
#         "mpls_tc": {"ixn_attr": "trafficClass", "default": "0"},
#         "mpls_ttl": {"ixn_attr": "timeToLive", "default": "255"},
#         "v_flag": {"ixn_attr": "vflag", "default": False},
#         "remaining_flag_bits": {
#             "ixn_attr": "remainingBits",
#             "default": "0x01",
#         },
#         "ipv6_sid": {"ixn_attr": "ipv6SID", "default": "::"},
#     }
#
#     def __init__(self, ngpf):
#         self._ngpf = ngpf
#         self._api = ngpf._api
#         self.update = ngpf.update
#         self.configure_value = ngpf.configure_value
#         self.get_xpath = ngpf.get_xpath
#         self.select_node = ngpf.select_node
#         self.select_child_node = ngpf.select_child_node
#
#     def configure_bgpv4(self, ixn_parent, bgpv4, ixn_dg):
#         ixn_bgpv4 = ixn_parent.BgpIpv4Peer
#         self._api._remove(ixn_bgpv4, [bgpv4])
#         bgp_name = bgpv4.get("name")
#         name = self._api.special_char(bgp_name)
#         args = {
#             "Name": name,
#         }
#         ixn_bgpv4.find(Name="^%s$" % name)
#         if len(ixn_bgpv4) == 0:
#             ixn_bgpv4.add(**args)[-1]
#         else:
#             self.update(ixn_bgpv4, **args)
#         as_type = "internal"
#         if bgpv4.get("as_type") is not None and bgpv4.get("as_type") == "ebgp":
#             as_type = "external"
#         bgp_xpath = self.get_xpath(ixn_bgpv4.href)
#         self._api.set_ixn_cmp_object(bgpv4, ixn_bgpv4.href, bgp_xpath)
#         self.configure_value(bgp_xpath, "type", as_type)
#         as_bytes = bgpv4.get("as_number_width")
#         as_bytes_list = (
#             [as_bytes] if not isinstance(as_bytes, list) else as_bytes
#         )
#         as_number = bgpv4.get("as_number")
#         as_number_list = (
#             [as_number] if not isinstance(as_number, list) else as_number
#         )
#         for index, as_number in enumerate(as_number_list):
#             as_byte = as_bytes_list[index]
#             if as_byte == "two":
#                 self.configure_value(bgp_xpath, "localAs2Bytes", as_number)
#             elif as_byte == "four":
#                 self.configure_value(bgp_xpath, "enable4ByteAs", True)
#                 self.configure_value(bgp_xpath, "localAs4Bytes", as_number)
#             else:
#                 msg = "Please configure supported [two, four] as_number_width"
#                 raise Exception(msg)
#         dut_address = bgpv4.get("dut_address")
#         if dut_address is not None:
#             self.configure_value(bgp_xpath, "dutIp", dut_address)
#
#         as_number_set_mode = bgpv4.get("as_number_set_mode")
#         if as_number_set_mode:
#             self.configure_value(
#                 bgp_xpath,
#                 "asSetMode",
#                 as_number_set_mode,
#                 enum_map=ConfigureBgp._BGP_AS_SET_MODE,
#             )
#         # self._configure_pattern(ixn_dg.RouterData.RouterId, bgpv4.router_id)
#         advanced = bgpv4.get("advanced")
#         if advanced is not None:
#             self.configure_value(
#                 bgp_xpath, "holdTimer", advanced.get("hold_time_interval")
#             )
#             self.configure_value(
#                 bgp_xpath,
#                 "keepaliveTimer",
#                 advanced.get("keep_alive_interval"),
#             )
#             self.configure_value(bgp_xpath, "md5Key", advanced.get("md5_key"))
#             self.configure_value(
#                 bgp_xpath, "updateInterval", advanced.get("update_interval")
#             )
#             self.configure_value(bgp_xpath, "ttl", advanced.time_to_live)
#         sr_te_policies = bgpv4.get("sr_te_policies")
#         if sr_te_policies is not None:
#             self._configure_sr_te(ixn_bgpv4, bgp_xpath, sr_te_policies)
#         self._bgp_route_builder(ixn_dg, ixn_bgpv4, bgpv4)
#         return ixn_bgpv4
#
#     def _bgp_route_builder(self, ixn_dg, ixn_bgp, bgp):
#         bgpv4_routes = bgp.get("bgpv4_routes")
#         bgpv6_routes = bgp.get("bgpv6_routes")
#         if bgpv4_routes is not None and len(bgpv4_routes) > 0:
#             for route_range in bgpv4_routes:
#                 self._configure_bgpv4_route(ixn_dg, ixn_bgp, route_range)
#         if bgpv6_routes is not None and len(bgpv6_routes) > 0:
#             for route_range in bgpv6_routes:
#                 self._configure_bgpv6_route(ixn_dg, ixn_bgp, route_range)
#
#     def _configure_bgpv4_route(self, ixn_dg, ixn_bgp, route_range):
#         ixn_ng = ixn_dg.NetworkGroup
#         route_name = route_range.get("name")
#         name = self._api.special_char(route_name)
#         args = {
#             "Name": name,
#         }
#         ixn_ng.find(Name="^%s$" % name)
#         if len(ixn_ng) == 0:
#             self.stop_topology()
#             ixn_ng.add(**args)[-1]
#             ixn_pool = ixn_ng.Ipv4PrefixPools.add()
#         else:
#             self.update(ixn_ng, **args)
#             ixn_pool = ixn_ng.Ipv4PrefixPools.find()
#         ixn_pool.Connector.find().ConnectedTo = ixn_bgp.href
#         pool_infos = self.select_node(
#             ixn_pool.href,
#             children=["bgpIPRouteProperty", "bgpV6IPRouteProperty"],
#         )
#         pool_xpath = pool_infos["xpath"]
#         addresses = route_range.get("addresses")
#         route_len = len(addresses)
#         if len(addresses) > 0:
#             ixn_ng.Multiplier = route_len
#             route_addresses = RouteAddresses()
#             for address in addresses:
#                 # below properties will set to default when
#                 # route_address is instantiated
#                 route_addresses.address = address.get("address")
#                 route_addresses.step = address.get("step")
#                 route_addresses.prefix = address.get("prefix")
#                 route_addresses.count = address.get("count")
#             self.configure_value(
#                 pool_xpath, "networkAddress", route_addresses.address
#             )
#             self.configure_value(
#                 pool_xpath, "prefixAddrStep", route_addresses.step
#             )
#             self.configure_value(
#                 pool_xpath, "prefixLength", route_addresses.prefix
#             )
#             self.configure_value(
#                 pool_xpath, "numberOfAddressesAsy", route_addresses.count
#             )
#         if "bgpIPRouteProperty" in pool_infos:
#             ixn_bgp_property = ixn_pool.BgpIPRouteProperty.find()
#             property_xpath = pool_infos["bgpIPRouteProperty"][0]["xpath"]
#         else:
#             ixn_bgp_property = ixn_pool.BgpV6IPRouteProperty.find()
#             property_xpath = pool_infos["bgpV6IPRouteProperty"][0]["xpath"]
#         next_hop_address = route_range.get("next_hop_address")
#         if next_hop_address:
#             self.configure_value(
#                 property_xpath,
#                 "ipv4NextHop",
#                 next_hop_address,
#                 multiplier=route_len,
#             )
#         if route_name is not None:
#             ixn_bgp_property.Name = route_name
#             self._api.set_ixn_cmp_object(
#                 route_range, ixn_pool.href, pool_xpath, multiplier=route_len
#             )
#             self._api.set_device_encap(route_range, "ipv4")
#             self._api.set_route_objects(
#                 ixn_bgp_property, route_range, multiplier=route_len
#             )
#         advanced = route_range.get("advanced")
#         if (
#             advanced is not None
#             and advanced.get("multi_exit_discriminator") is not None
#         ):
#             self.configure_value(
#                 property_xpath, "enableMultiExitDiscriminator", True
#             )
#             self.configure_value(
#                 property_xpath,
#                 "multiExitDiscriminator",
#                 advanced.get("multi_exit_discriminator"),
#                 multiplier=route_len,
#             )
#         if advanced is not None:
#             self.configure_value(
#                 property_xpath,
#                 "origin",
#                 advanced.get("origin"),
#                 multiplier=route_len,
#             )
#         as_path = route_range.get("as_path")
#         if as_path is not None:
#             self._config_bgp_as_path(as_path, ixn_bgp_property, route_len)
#         communities = route_range.get("communities")
#         if communities:
#             self._config_bgp_community(
#                 communities, ixn_bgp_property, route_len
#             )
#
#     def configure_bgpv6(self, ixn_parent, bgpv6, ixn_dg):
#         ixn_bgpv6 = ixn_parent.BgpIpv6Peer
#         self._api._remove(ixn_bgpv6, [bgpv6])
#         bgp_name = bgpv6.get("name")
#         name = self._api.special_char(bgp_name)
#         args = {
#             "Name": name,
#         }
#         ixn_bgpv6.find(Name="^%s$" % name)
#         if len(ixn_bgpv6) == 0:
#             ixn_bgpv6.add(**args)[-1]
#         else:
#             self.update(ixn_bgpv6, **args)
#         as_type = "internal"
#         if bgpv6.get("as_type") is not None and bgpv6.get("as_type") == "ebgp":
#             as_type = "external"
#         bgp_xpath = self.get_xpath(ixn_bgpv6.href)
#         self._api.set_ixn_cmp_object(bgpv6, ixn_bgpv6.href, bgp_xpath)
#         self.configure_value(bgp_xpath, "type", as_type)
#         as_bytes = bgpv6.get("as_number_width")
#         as_bytes_list = (
#             [as_bytes] if not isinstance(as_bytes, list) else as_bytes
#         )
#         as_number = bgpv6.get("as_number")
#         as_number_list = (
#             [as_number] if not isinstance(as_number, list) else as_number
#         )
#         for index, as_number in enumerate(as_number_list):
#             as_byte = as_bytes_list[index]
#             if as_byte == "two":
#                 self.configure_value(bgp_xpath, "localAs2Bytes", as_number)
#             elif as_byte == "four":
#                 self.configure_value(bgp_xpath, "enable4ByteAs", True)
#                 self.configure_value(bgp_xpath, "localAs4Bytes", as_number)
#             else:
#                 msg = "Please configure supported [two, four] as_number_width"
#                 raise Exception(msg)
#         dut_address = bgpv6.get("dut_address")
#         if dut_address is not None:
#             self.configure_value(bgp_xpath, "dutIp", dut_address)
#         as_number_set_mode = bgpv6.get("as_number_set_mode")
#         if as_number_set_mode is not None:
#             self.configure_value(
#                 bgp_xpath,
#                 "asSetMode",
#                 as_number_set_mode,
#                 enum_map=ConfigureBgp._BGP_AS_SET_MODE,
#             )
#         # self._configure_pattern(ixn_dg.RouterData.RouterId, bgpv4.router_id)
#         advanced = bgpv6.get("advanced")
#         if advanced is not None:
#             self.configure_value(
#                 bgp_xpath, "holdTimer", advanced.get("hold_time_interval")
#             )
#             self.configure_value(
#                 bgp_xpath,
#                 "keepaliveTimer",
#                 advanced.get("keep_alive_interval"),
#             )
#             self.configure_value(bgp_xpath, "md5Key", advanced.get("md5_key"))
#             self.configure_value(
#                 bgp_xpath, "updateInterval", advanced.get("update_interval")
#             )
#             self.configure_value(
#                 bgp_xpath, "ttl", advanced.get("time_to_live")
#             )
#         sr_te_policies = bgpv6.get("sr_te_policies")
#         if sr_te_policies:
#             self._configure_sr_te(ixn_bgpv6, bgp_xpath, sr_te_policies)
#         self._bgp_route_builder(ixn_dg, ixn_bgpv6, bgpv6)
#         return ixn_bgpv6
#
#     def _configure_bgpv6_route(self, ixn_dg, ixn_bgp, route_range):
#         ixn_ng = ixn_dg.NetworkGroup
#         route_name = route_range.get("name")
#         name = self._api.special_char(route_name)
#         args = {
#             "Name": name,
#         }
#         ixn_ng.find(Name="^%s$" % name)
#         if len(ixn_ng) == 0:
#             self.stop_topology()
#             ixn_ng.add(**args)[-1]
#             ixn_pool = ixn_ng.Ipv6PrefixPools.add()
#         else:
#             self.update(ixn_ng, **args)
#             ixn_pool = ixn_ng.Ipv6PrefixPools.find()
#         ixn_pool.Connector.find().ConnectedTo = ixn_bgp.href
#         pool_infos = self.select_node(
#             ixn_pool.href,
#             children=["bgpIPRouteProperty", "bgpV6IPRouteProperty"],
#         )
#         pool_xpath = pool_infos["xpath"]
#         addresses = route_range.get("addresses")
#         route_len = len(addresses)
#         if len(addresses) > 0:
#             ixn_ng.Multiplier = route_len
#             route_addresses = RouteAddresses()
#             for address in addresses:
#                 route_addresses.address = address.get("address")
#                 route_addresses.step = address.get("step")
#                 route_addresses.prefix = address.get("prefix")
#                 route_addresses.count = address.get("count")
#             self.configure_value(
#                 pool_xpath, "networkAddress", route_addresses.address
#             )
#             self.configure_value(
#                 pool_xpath, "prefixAddrStep", route_addresses.step
#             )
#             self.configure_value(
#                 pool_xpath, "prefixLength", route_addresses.prefix
#             )
#             self.configure_value(
#                 pool_xpath, "numberOfAddressesAsy", route_addresses.count
#             )
#         if self._api.get_device_encap(ixn_dg.Name) == "ipv4":
#             ixn_bgp_property = ixn_pool.BgpIPRouteProperty.find()
#             property_xpath = pool_infos["bgpIPRouteProperty"][0]["xpath"]
#         else:
#             ixn_bgp_property = ixn_pool.BgpV6IPRouteProperty.find()
#             property_xpath = pool_infos["bgpV6IPRouteProperty"][0]["xpath"]
#         next_hop_address = route_range.get("next_hop_address")
#         if next_hop_address is not None:
#             self.configure_value(
#                 property_xpath,
#                 "ipv6NextHop",
#                 next_hop_address,
#                 multiplier=route_len,
#             )
#         if route_name is not None:
#             ixn_bgp_property.Name = route_name
#             self._api.set_ixn_cmp_object(
#                 route_range, ixn_pool.href, pool_xpath, multiplier=route_len
#             )
#             self._api.set_device_encap(route_range, "ipv6")
#             self._api.set_route_objects(
#                 ixn_bgp_property, route_range, multiplier=route_len
#             )
#         advanced = route_range.get("advanced")
#         if (
#             advanced is not None
#             and advanced.get("multi_exit_discriminator") is not None
#         ):
#             self.configure_value(
#                 property_xpath, "enableMultiExitDiscriminator", True
#             )
#             self.configure_value(
#                 property_xpath,
#                 "multiExitDiscriminator",
#                 advanced.get("multi_exit_discriminator"),
#                 multiplier=route_len,
#             )
#         if advanced is not None:
#             self.configure_value(
#                 property_xpath,
#                 "origin",
#                 advanced.get("origin"),
#                 multiplier=route_len,
#             )
#         as_path = route_range.get("as_path")
#         if as_path is not None:
#             self._config_bgp_as_path(as_path, ixn_bgp_property, route_len)
#         communities = route_range.get("communities")
#         if communities:
#             self._config_bgp_community(
#                 communities, ixn_bgp_property, route_len
#             )
#
#     def _config_bgp_as_path(self, as_path, ixn_bgp_property, multiplier):
#         as_path_segments = as_path.get("as_path_segments")
#         property_xpath = self.get_xpath(ixn_bgp_property.href)
#         as_set_mode = as_path.get("as_set_mode")
#         if as_set_mode is not None or len(as_path_segments) > 0:
#             self.configure_value(property_xpath, "enableAsPathSegments", True)
#             self.configure_value(
#                 property_xpath,
#                 "asSetMode",
#                 as_set_mode,
#                 enum_map=ConfigureBgp._BGP_AS_MODE,
#                 multiplier=multiplier,
#             )
#             self.configure_value(
#                 property_xpath,
#                 "OverridePeerAsSetMode",
#                 as_path.get("override_peer_as_set_mode"),
#                 multiplier=multiplier,
#             )
#             if len(as_path_segments) > 0:
#                 ixn_bgp_property.NoOfASPathSegmentsPerRouteRange = len(
#                     as_path_segments
#                 )
#                 ixn_segments = ixn_bgp_property.BgpAsPathSegmentList.find()
#                 for seg_index, segment in enumerate(as_path_segments):
#                     ixn_segment = ixn_segments[seg_index]
#                     ixn_segment.SegmentType.Single(
#                         ConfigureBgp._BGP_SEG_TYPE[segment.get("segment_type")]
#                     )
#                     as_numbers = segment.get("as_numbers")
#                     if as_numbers is not None:
#                         ixn_segment.NumberOfAsNumberInSegment = len(as_numbers)
#                         as_numbers_info = self.select_child_node(
#                             ixn_segment.href, "bgpAsNumberList"
#                         )
#                         for as_index, as_number in enumerate(as_numbers):
#                             as_num_xpath = as_numbers_info[as_index]["xpath"]
#                             self.configure_value(
#                                 as_num_xpath,
#                                 "asNumber",
#                                 as_number,
#                                 multiplier=multiplier,
#                             )
#
#     def _config_bgp_community(self, communities, ixn_bgp_property, multiplier):
#         if len(communities) == 0:
#             ixn_bgp_property.EnableCommunity.Single(False)
#             return
#         ixn_bgp_property.EnableCommunity.Single(True)
#         ixn_bgp_property.NoOfCommunities = len(communities)
#         communities_info = self.select_child_node(
#             ixn_bgp_property.href, "bgpCommunitiesList"
#         )
#         for index, community in enumerate(communities):
#             community_xpath = communities_info[index]["xpath"]
#             community_type = community.get("community_type")
#             if community_type is not None:
#                 self.configure_value(
#                     community_xpath,
#                     "type",
#                     community_type,
#                     enum_map=ConfigureBgp._BGP_COMMUNITY_TYPE,
#                     multiplier=multiplier,
#                 )
#             self.configure_value(
#                 community_xpath,
#                 "asNumber",
#                 community.get("as_number"),
#                 multiplier=multiplier,
#             )
#             self.configure_value(
#                 community_xpath,
#                 "lastTwoOctets",
#                 community.get("as_custom"),
#                 multiplier=multiplier,
#             )
#
#     def _configure_sr_te(self, ixn_bgp, bgp_xpath, sr_te_list):
#         if sr_te_list is None or len(sr_te_list) == 0:
#             return
#         self.configure_value(bgp_xpath, "capabilitySRTEPoliciesV4", True)
#         self.configure_value(bgp_xpath, "capabilitySRTEPoliciesV6", True)
#         ixn_bgp.NumberSRTEPolicies = len(sr_te_list)
#         if re.search("bgpIpv4Peer", ixn_bgp.href) is not None:
#             ixn_sr_te = ixn_bgp.BgpSRTEPoliciesListV4
#         else:
#             ixn_sr_te = ixn_bgp.BgpSRTEPoliciesListV6
#         sr_te_xpath = self.get_xpath(ixn_sr_te.href)
#         self._configure_attributes(
#             ConfigureBgp._BGP_SR_TE, sr_te_list, sr_te_xpath
#         )
#         next_hops = []
#         add_paths = []
#         as_paths = []
#         communities = []
#         for sr_te in sr_te_list:
#             if sr_te.get("next_hop") is not None:
#                 next_hops.append(sr_te.next_hop)
#             if sr_te.get("add_path") is not None:
#                 add_paths.append(sr_te.add_path)
#             if sr_te.get("as_path") is not None:
#                 as_paths.append(sr_te.as_path)
#             if sr_te.get("communities") is not None:
#                 communities.append(sr_te.communities)
#
#         active_list = self._process_nodes(next_hops)
#         if active_list != []:
#             self.configure_value(sr_te_xpath, "enableNextHop", active_list)
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._SRTE_NEXT_HOP, next_hops, sr_te_xpath
#             )
#
#         active_list = self._process_nodes(add_paths)
#         if active_list != []:
#             self.configure_value(sr_te_xpath, "enableAddPath", active_list)
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._SRTE_ADDPATH, add_paths, sr_te_xpath
#             )
#
#         active_list = self._process_nodes(as_paths)
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._SRTE_AS_PATH, as_paths, sr_te_xpath
#             )
#             self._configure_srte_aspath_segment(as_paths, ixn_sr_te)
#         self._configure_tlvs(ixn_sr_te, sr_te_list)
#
#     def _get_symmetric_nodes(self, parent_list, node_name):
#         NodesInfo = namedtuple(
#             "NodesInfo", ["max_len", "active_list", "symmetric_nodes"]
#         )
#         nodes_list = []
#         max_len = 0
#         for parent in parent_list:
#             nodes = getattr(parent, node_name)
#             node_len = len(nodes)
#             if node_len > max_len:
#                 max_len = node_len
#             nodes_list.append(nodes)
#         symmetric_nodes = []
#         active_list = []
#         for nodes in nodes_list:
#             if len(nodes) == max_len:
#                 for node in nodes:
#                     active_list.append(node.active)
#                     symmetric_nodes.append(node)
#             else:
#                 for index in range(0, max_len):
#                     node = nodes[0]
#                     if index < len(nodes):
#                         node = nodes[index]
#                         active_list.append(node.active)
#                         symmetric_nodes.append(node)
#                     else:
#                         active_list.append(False)
#                         symmetric_nodes.append(node)
#         return NodesInfo(max_len, active_list, symmetric_nodes)
#
#     def _get_symetric_tab_nodes(self, parent_list, node_name):
#         TabNodesInfo = namedtuple(
#             "TabNodesInfo", ["max_len", "symmetric_nodes_list", "actives_list"]
#         )
#         max_len = 0
#         symmetric_nodes_list = []
#         actives_list = []
#         is_enable = False
#         for parent in parent_list:
#             nodes = getattr(parent, node_name)
#             if nodes is None:
#                 continue
#             is_enable = True
#             node_len = len(nodes)
#             if node_len > max_len:
#                 for index in range(max_len, node_len):
#                     symmetric_nodes_list.append(
#                         [nodes[index]] * len(parent_list)
#                     )
#                     actives_list.append([False] * len(parent_list))
#                 max_len = node_len
#         if is_enable:
#             for parent_idx, parent in enumerate(parent_list):
#                 nodes = getattr(parent, node_name)
#                 for node_idx, node in enumerate(nodes):
#                     symmetric_nodes_list[node_idx][parent_idx] = node
#                     actives_list[node_idx][parent_idx] = True
#         return TabNodesInfo(max_len, symmetric_nodes_list, actives_list)
#
#     def _configure_srte_aspath_segment(self, as_paths, ixn_sr_te):
#         nodes_list_info = self._get_symetric_tab_nodes(
#             as_paths, "as_path_segments"
#         )
#         if nodes_list_info.max_len == 0:
#             return
#         ixn_sr_te.EnableAsPathSegments.Single(True)
#         ixn_sr_te.NoOfASPathSegmentsPerRouteRange = nodes_list_info.max_len
#         ixn_segments = ixn_sr_te.BgpAsPathSegmentList
#         ixn_segments.find()
#         segments_info = self.select_node(
#             ixn_sr_te.refresh().href, children=["bgpAsPathSegmentList"]
#         )
#         for seg_idx, segment in enumerate(
#             segments_info["bgpAsPathSegmentList"]
#         ):
#             segment_xpath = segment["xpath"]
#             ixn_segment = ixn_segments[seg_idx]
#             segment_nodes = nodes_list_info.symmetric_nodes_list[seg_idx]
#             self.configure_value(
#                 segment_xpath,
#                 "enableASPathSegment",
#                 nodes_list_info.actives_list[seg_idx],
#             )
#             self._configure_attributes(
#                 ConfigureBgp._SRTE_ASPATH_SEGMENT, segment_nodes, segment_xpath
#             )
#             configure_as_number = False
#             for segment_node in segment_nodes:
#                 as_numbers = getattr(segment_node, "as_numbers")
#                 if as_numbers is not None:
#                     configure_as_number = True
#                     if not isinstance(as_numbers, list):
#                         raise Exception("as_numbers must be list")
#             if configure_as_number is True:
#                 as_numbers_list = self._get_symetric_tab_nodes(
#                     segment_nodes, "as_numbers"
#                 )
#                 ixn_segment.NumberOfAsNumberInSegment = as_numbers_list.max_len
#                 numbers_info = self.select_node(
#                     ixn_segment.href, children=["bgpAsNumberList"]
#                 )
#                 for num_idx, number in enumerate(
#                     numbers_info["bgpAsNumberList"]
#                 ):
#                     number_xpath = number["xpath"]
#                     self.configure_value(
#                         number_xpath,
#                         "enableASNumber",
#                         as_numbers_list.actives_list[num_idx],
#                     )
#                     self.configure_value(
#                         number_xpath,
#                         "asNumber",
#                         as_numbers_list.symmetric_nodes_list[num_idx],
#                     )
#
#     def _configure_tlvs(self, ixn_sr_te, sr_te_list):
#         nodes_info = self._get_symmetric_nodes(sr_te_list, "tunnel_tlvs")
#         if int(nodes_info.max_len) > 2:
#             raise Exception(
#                 "Value {0} for SR TE Policy Number of Tunnel TLVs is "
#                 "greater than maximal value 2".format(nodes_info.max_len)
#             )
#         if re.search("bgpSRTEPoliciesListV4", ixn_sr_te.href) is not None:
#             ixn_sr_te.NumberOfTunnelsV4 = nodes_info.max_len
#             ixn_tunnel = ixn_sr_te.BgpSRTEPoliciesTunnelEncapsulationListV4
#         else:
#             ixn_sr_te.NumberOfTunnelsV6 = nodes_info.max_len
#             ixn_tunnel = ixn_sr_te.BgpSRTEPoliciesTunnelEncapsulationListV6
#         tunnel_xpath = self.get_xpath(ixn_tunnel.href)
#         self.configure_value(tunnel_xpath, "active", nodes_info.active_list)
#         tunnel_tlvs = nodes_info.symmetric_nodes
#
#         remote_endpoint_sub_tlv = []
#         preference_sub_tlv = []
#         binding_sub_tlv = []
#         explicit_null_label_policy_sub_tlv = []
#         for tunnel_tlv in tunnel_tlvs:
#             if tunnel_tlv.get("remote_endpoint_sub_tlv") is not None:
#                 remote_endpoint_sub_tlv.append(
#                     tunnel_tlv.remote_endpoint_sub_tlv
#                 )
#             if tunnel_tlv.get("preference_sub_tlv") is not None:
#                 preference_sub_tlv.append(tunnel_tlv.preference_sub_tlv)
#             if tunnel_tlv.get("binding_sub_tlv") is not None:
#                 binding_sub_tlv.append(tunnel_tlv.binding_sub_tlv)
#             if (
#                 tunnel_tlv.get("explicit_null_label_policy_sub_tlv")
#                 is not None
#             ):
#                 explicit_null_label_policy_sub_tlv.append(
#                     tunnel_tlv.explicit_null_label_policy_sub_tlv
#                 )
#
#         active_list = self._process_nodes(remote_endpoint_sub_tlv)
#         if active_list != []:
#             self.configure_value(
#                 tunnel_xpath, "enRemoteEndPointTLV", active_list
#             )
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._REMOTE_ENDPOINT_SUB_TLV,
#                 remote_endpoint_sub_tlv,
#                 tunnel_xpath,
#             )
#
#         active_list = self._process_nodes(preference_sub_tlv)
#         if active_list != []:
#             self.configure_value(tunnel_xpath, "enPrefTLV", active_list)
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._PREFERENCE_SUB_TLV,
#                 preference_sub_tlv,
#                 tunnel_xpath,
#             )
#
#         active_list = self._process_nodes(binding_sub_tlv)
#         if active_list != []:
#             self.configure_value(tunnel_xpath, "enBindingTLV", active_list)
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._BINDING_SUB_TLV, binding_sub_tlv, tunnel_xpath
#             )
#
#         active_list = self._process_nodes(explicit_null_label_policy_sub_tlv)
#         if active_list != []:
#             self.configure_value(tunnel_xpath, "enENLPTLV", active_list)
#         if any(active_list):
#             self._configure_attributes(
#                 ConfigureBgp._ENLP_SUB_TLV,
#                 explicit_null_label_policy_sub_tlv,
#                 tunnel_xpath,
#             )
#         self._configure_tlv_segment(ixn_tunnel, tunnel_tlvs)
#
#     def _configure_tlv_segment(self, ixn_tunnel, tunnel_tlvs):
#         nodes_info = self._get_symmetric_nodes(tunnel_tlvs, "segment_lists")
#         if (
#             re.search(
#                 "bgpSRTEPoliciesTunnelEncapsulationListV4", ixn_tunnel.href
#             )
#             is not None
#         ):
#             ixn_tunnel.NumberOfSegmentListV4 = nodes_info.max_len
#             ixn_segment_list = ixn_tunnel.BgpSRTEPoliciesSegmentListV4
#         else:
#             ixn_tunnel.NumberOfSegmentListV6 = nodes_info.max_len
#             ixn_segment_list = ixn_tunnel.BgpSRTEPoliciesSegmentListV6
#         segment_list_xpath = self.get_xpath(ixn_segment_list.href)
#         self.configure_value(
#             segment_list_xpath, "active", nodes_info.active_list
#         )
#         segment_list = nodes_info.symmetric_nodes
#         if any(nodes_info.active_list):
#             self._configure_attributes(
#                 ConfigureBgp._POLICIES_SEGMENT_LIST,
#                 segment_list,
#                 segment_list_xpath,
#             )
#             self.configure_value(
#                 segment_list_xpath, "enWeight", [True] * len(segment_list)
#             )
#         nodes_info = self._get_symmetric_nodes(segment_list, "segments")
#         if (
#             re.search("bgpSRTEPoliciesSegmentListV4", ixn_segment_list.href)
#             is not None
#         ):
#             ixn_segment_list.NumberOfSegmentsV4 = nodes_info.max_len
#             ixn_segments = ixn_segment_list.BgpSRTEPoliciesSegmentsCollectionV4
#         else:
#             ixn_segment_list.NumberOfSegmentsV6 = nodes_info.max_len
#             ixn_segments = ixn_segment_list.BgpSRTEPoliciesSegmentsCollectionV6
#         segments_xpath = self.get_xpath(ixn_segments.href)
#         self.configure_value(segments_xpath, "active", nodes_info.active_list)
#         segments = nodes_info.symmetric_nodes
#         if any(nodes_info.active_list):
#             self._configure_attributes(
#                 ConfigureBgp._SEGMENTS, segments, segments_xpath
#             )
#
#     def _process_nodes(self, nodes):
#         active_list = []
#         for index, node in enumerate(nodes):
#             active = False
#             if node is None:
#                 if index == 0:
#                     nodes[0] = next(v for v in nodes if v is not None)
#                 else:
#                     nodes[index] = nodes[index - 1]
#             else:
#                 is_config = False
#                 for name, value in node._properties.items():
#                     if value is not None:
#                         is_config = True
#                         break
#                 if is_config is True:
#                     active = True
#             active_list.append(active)
#         return active_list
#
#     def _configure_attributes(self, mapper, parent_list, xpath):
#         for attribute in mapper:
#             attr_mapper = mapper[attribute]
#             ixn_attribute = attr_mapper["ixn_attr"]
#             default_value = attr_mapper["default"]
#             enum_map = attr_mapper.get("enum_map")
#             default_obj = getattr(self, str(default_value), None)
#             config_values = []
#             for parent in parent_list:
#                 config_value = getattr(parent, attribute, None)
#                 if config_value is not None:
#                     if enum_map is None:
#                         config_values.append(str(config_value))
#                     else:
#                         if str(config_value) not in enum_map.keys():
#                             raise Exception(
#                                 "{0} must configure with enum {1}".format(
#                                     attribute, enum_map.keys()
#                                 )
#                             )
#                         config_values.append(enum_map[str(config_value)])
#                 elif default_obj is not None:
#                     config_values.append(default_obj())
#                 else:
#                     config_values.append(default_value)
#             self.configure_value(xpath, ixn_attribute, config_values)
#
#     def stop_topology(self):
#         glob_topo = self._api._globals.Topology.refresh()
#         if glob_topo.Status == "started":
#             self._api._ixnetwork.StopAllProtocols("sync")
#
#
# class RouteAddresses(object):
#
#     _IPv4 = "ipv4"
#     _IPv6 = "ipv6"
#
#     def __init__(self):
#         self._address = []
#         self._count = []
#         self._prefix = []
#         self._step = []
#         self._ip_type = None
#
#     def _comp_value(self, values):
#         com_values = []
#         idx = 0
#         while idx < len(values[0]):
#             for value in values:
#                 com_values.append(value[idx])
#             idx += 1
#         return com_values
#
#     @property
#     def address(self):
#         if isinstance(self._address[0], list):
#             return self._comp_value(self._address)
#         return self._address
#
#     @address.setter
#     def address(self, value):
#         self._address.append(value)
#
#     @property
#     def count(self):
#         if isinstance(self._count[0], list):
#             return self._comp_value(self._count)
#         return self._count
#
#     @count.setter
#     def count(self, value):
#         self._count.append(value)
#
#     @property
#     def prefix(self):
#         if isinstance(self._prefix[0], list):
#             return self._comp_value(self._prefix)
#         return self._prefix
#
#     @prefix.setter
#     def prefix(self, value):
#         self._prefix.append(value)
#
#     @property
#     def step(self):
#         if isinstance(self._step[0], list):
#             return self._comp_value(self._step)
#         return self._step
#
#     @step.setter
#     def step(self, value):
#         self._step.append(value)
#
#     def _get_ip_type(self, addresses):
#         class_name = addresses[0].__class__.__name__
#         if re.search("v4", class_name) is not None:
#             return RouteAddresses._IPv4
#         else:
#             return RouteAddresses._IPv6
#
#     def _address_to_int(self, addr):
#         if self._ip_type == RouteAddresses._IPv4:
#             return struct.unpack("!I", socket.inet_aton(addr))[0]
#         else:
#             hi, lo = struct.unpack(
#                 "!QQ", socket.inet_pton(socket.AF_INET6, addr)
#             )
#             return (hi << 64) | lo
