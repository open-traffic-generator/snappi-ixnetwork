import pytest


def test_bgp_sr_te_policy_v4v6(api):
    """
    Test BGP SRTE Policy V4V6 configuration applied properly on ixNetwork

    Validate the configuration against RestPy
    """

    BGPV4_SR_TE = {
        'PolicyType': 'ipv4',
        'Distinguisher': '2',
        'PolicyColor': '2',
        'EndPointV4': '10.10.10.1',
        'SetNextHop': 'manually',
        'SetNextHopIpType': 'ipv4',
        'Ipv4NextHop': '10.10.10.1',
        'OverridePeerAsSetMode': 'true',
        'AsSetMode': 'includelocalasasasseq',
        'AddPathId': '2'
    }
    BGPV4_SR_TE_TUNNEL = {
        'As4Number': '100',
        'AddressFamily': 'ipv4',
        'RemoteEndpointIPv4': '1.1.1.4',
        'PrefValue': '400',
        'BindingSIDType': 'sid4',
        'SID4Octet': '483001',
        'UseAsMPLSLabel': 'true',
        'EnENLPTLV': 'true',
        'ENLPValue': '2',
        'Iflag': 'true',
        'Sflag': 'true',
        'RemainingBits': '1'
    }

    BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST = {
        'Count': 1,
        'NumberOfSegmentsV4': 5,
        'EnWeight': 'True',
        'Weight': '1',
    }

    BGPV4_SR_TE_TUNNEL_SEGMENTS = {
        'SegmentType': ['mplssid', 'mplssid', 'mplssid', 'mplssid', 'mplssid'],
        'Label': ['1018001', '432999', '1048333', '1048561', '432001'],
        'TimeToLive': ['64', '64', '64', '64', '64'],
        'TrafficClass': ['2', '2', '2', '2', '2'],
    }

    BGPV6_SR_TE = {
        'PolicyType': 'ipv6',
        'Distinguisher': '3',
        'PolicyColor': '3',
        'EndPointV6': '2000::2',
        'SetNextHop': 'manually',
        'SetNextHopIpType': 'ipv6',
        'Ipv6NextHop': '2000::2',
        'OverridePeerAsSetMode': 'true',
        'AsSetMode': 'includelocalasasasseq',
    }

    BGPV6_SR_TE_TUNNEL = {
        'As4Number': '100',
        'AddressFamily': 'ipv6',
        'RemoteEndpointIPv6': '2000::2',
        'PrefValue': '400',
        'BindingSIDType': 'sid4',
        'SID4Octet': '483001',
        'UseAsMPLSLabel': 'true',
        'EnENLPTLV': 'true',
        'ENLPValue': '2',
        'Iflag': 'false',
        'Sflag': 'false',
        'RemainingBits': '1'
    }

    BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST = {
        'Count': 1,
        'NumberOfSegmentsV6': 5,
        'EnWeight': 'True',
        'Weight': '1',
    }

    BGPV6_SR_TE_TUNNEL_SEGMENTS = {
        'SegmentType': ['mplssid', 'mplssid', 'mplssid', 'mplssid', 'mplssid'],
        'Label': ['1018001', '432999', '1048333', '1048561', '432001'],
        'TimeToLive': ['64', '64', '64', '64', '64'],
        'TrafficClass': ['2', '2', '2', '2', '2'],
    }

    config = api.config()

    # setup port container
    p1 = config.ports.port(name='p1')[-1]

    # setup device container
    d = config.devices.device(name='d', container_name=p1.name)[-1]

    # setup ethernet
    eth = d.ethernet
    eth.name = 'e'
    eth.mac = '00:01:00:00:00:01'

    # setup ipv4
    ip = eth.ipv4
    ip.name = 'i4'
    ip.address = '10.10.10.1'
    ip.gateway = '10.10.10.2'
    ip.prefix = 32

    # setup bgp basic
    bgp = ip.bgpv4
    bgp.name = 'b4'
    bgp.router_id = '193.0.0.1'
    bgp.as_number = 65511
    bgp.as_number_set_mode = bgp.DO_NOT_INCLUDE_AS
    bgp.local_address = '10.10.10.1'
    bgp.dut_address = '10.10.10.2'

    # setup bgp advanced
    bgp.advanced.hold_time_interval = 90
    bgp.advanced.keep_alive_interval = 30

    # setup bgp sr te policy
    policy = bgp.sr_te_policies.bgpsrtepolicy()[-1]
    policy.policy_type = policy.IPV4
    policy.distinguisher = BGPV4_SR_TE['Distinguisher']
    policy.color = BGPV4_SR_TE['PolicyColor']
    policy.ipv4_endpoint = BGPV4_SR_TE['EndPointV4']

    hop = policy.next_hop
    hop.next_hop_mode = hop.MANUAL
    hop.next_hop_address_type = hop.IPV4
    hop.ipv4_address = BGPV4_SR_TE['Ipv4NextHop']

    path = policy.add_path
    path.path_id = BGPV4_SR_TE['AddPathId']

    as_path = policy.as_path
    as_path.override_peer_as_set_mode = True
    as_path.as_set_mode = as_path.INCLUDE_AS_SEQ

    # setup tunnel tlv
    tunnel = policy.tunnel_tlvs.bgptunneltlv(active=True)[-1]
    tunnel.active = True

    # setup tunnel tlv segment lists
    seglist = tunnel.segment_lists.bgpsegmentlist(active=True)[-1]
    seglist.segment_weight = int(BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST['Weight'])

    # setup remote endpoint tlv
    endpoint_tlv = tunnel.remote_endpoint_sub_tlv
    endpoint_tlv.as_number = BGPV4_SR_TE_TUNNEL['As4Number']
    endpoint_tlv.address_family = endpoint_tlv.IPV4
    endpoint_tlv.ipv4_address = BGPV4_SR_TE_TUNNEL['RemoteEndpointIPv4']

    # setup preference sub tlv
    pref_sub_tlv = tunnel.preference_sub_tlv
    pref_sub_tlv.preference = BGPV4_SR_TE_TUNNEL['PrefValue']

    # setup binding sub tlv
    bind_sub_tlv = tunnel.binding_sub_tlv
    bind_sub_tlv.binding_sid_type = bind_sub_tlv.FOUR_OCTET_SID
    bind_sub_tlv.four_octet_sid = BGPV4_SR_TE_TUNNEL['SID4Octet']
    bind_sub_tlv.bsid_as_mpls_label = True
    bind_sub_tlv.s_flag = True
    bind_sub_tlv.i_flag = True
    bind_sub_tlv.remaining_flag_bits = '0x01'

    # setup explicit null label policy sub tlv
    enlp_sub_tlv = tunnel.explicit_null_label_policy_sub_tlv
    enlp_sub_tlv.explicit_null_label_policy = enlp_sub_tlv.PUSH_IPV6_ENLP

    # setup segment list segments
    for label in BGPV4_SR_TE_TUNNEL_SEGMENTS['Label']:
        seg = seglist.segments.bgpsegment(active=True)[-1]
        seg.segment_type = seg.MPLS_SID
        seg.mpls_label = int(label)
        seg.mpls_ttl = 64
        seg.mpls_tc = 2


############################
    # setup ipv6
    ip6 = eth.ipv6
    ip6.name = 'i6'
    ip6.address = '2000::1'
    ip6.gateway = '2000::2'
    ip6.prefix = 64

    # setup bgp basic
    bgp6 = ip6.bgpv6
    bgp6.name = 'b6'
    bgp6.router_id = '193.0.0.1'
    bgp6.as_number = 65511
    bgp6.as_number_set_mode = bgp6.DO_NOT_INCLUDE_AS
    bgp6.local_address = '2000::1'
    bgp6.dut_address = '2000::2'

    # setup bgp advanced
    bgp6.advanced.hold_time_interval = 90
    bgp6.advanced.keep_alive_interval = 30

    # setup bgp sr te policy
    policy = bgp6.sr_te_policies.bgpsrtepolicy()[-1]
    policy.policy_type = policy.IPV6
    policy.distinguisher = BGPV6_SR_TE['Distinguisher']
    policy.color = BGPV6_SR_TE['PolicyColor']
    policy.ipv6_endpoint = BGPV6_SR_TE['EndPointV6']

    hop = policy.next_hop
    hop.next_hop_mode = hop.MANUAL
    hop.next_hop_address_type = hop.IPV6
    hop.ipv6_address = BGPV6_SR_TE['Ipv6NextHop']

    as_path = policy.as_path
    as_path.override_peer_as_set_mode = True
    as_path.as_set_mode = as_path.INCLUDE_AS_SEQ

    # setup tunnel tlv
    tunnel = policy.tunnel_tlvs.bgptunneltlv(active=True)[-1]

    # setup tunnel tlv segment lists
    seglist = tunnel.segment_lists.bgpsegmentlist(active=True)[-1]
    seglist.segment_weight = int(BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST['Weight'])

    # setup remote endpoint tlv
    endpoint_tlv = tunnel.remote_endpoint_sub_tlv
    endpoint_tlv.as_number = BGPV6_SR_TE_TUNNEL['As4Number']
    endpoint_tlv.address_family = endpoint_tlv.IPV6
    endpoint_tlv.ipv6_address = BGPV6_SR_TE_TUNNEL['RemoteEndpointIPv6']

    # setup preference sub tlv
    pref_sub_tlv = tunnel.preference_sub_tlv
    pref_sub_tlv.preference = BGPV6_SR_TE_TUNNEL['PrefValue']

    # setup binding sub tlv
    bind_sub_tlv = tunnel.binding_sub_tlv
    bind_sub_tlv.binding_sid_type = bind_sub_tlv.FOUR_OCTET_SID
    bind_sub_tlv.four_octet_sid = BGPV6_SR_TE_TUNNEL['SID4Octet']
    bind_sub_tlv.bsid_as_mpls_label = True
    bind_sub_tlv.s_flag = False
    bind_sub_tlv.i_flag = False
    bind_sub_tlv.remaining_flag_bits = '0x01'

    # setup explicit null label policy sub tlv
    enlp_sub_tlv = tunnel.explicit_null_label_policy_sub_tlv
    enlp_sub_tlv.explicit_null_label_policy = enlp_sub_tlv.PUSH_IPV6_ENLP

    # setup segment list segments
    for label in BGPV6_SR_TE_TUNNEL_SEGMENTS['Label']:
        seg = seglist.segments.bgpsegment(active=True)[-1]
        seg.segment_type = seg.MPLS_SID
        seg.mpls_label = int(label)
        seg.mpls_ttl = 64
        seg.mpls_tc = 2

    api.set_config(config)

    validate_sr_te_config(api,
                          BGPV4_SR_TE,
                          BGPV4_SR_TE_TUNNEL,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS,
                          BGPV6_SR_TE,
                          BGPV6_SR_TE_TUNNEL,
                          BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV6_SR_TE_TUNNEL_SEGMENTS
                          )


def validate_sr_te_config(api,
                          BGPV4_SR_TE,
                          BGPV4_SR_TE_TUNNEL,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS,
                          BGPV6_SR_TE,
                          BGPV6_SR_TE_TUNNEL,
                          BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV6_SR_TE_TUNNEL_SEGMENTS):
    """
    Validate BGP SRTE Config
    """

    ixnetwork = api._ixnetwork
    bgpv4 = (ixnetwork.Topology.find().DeviceGroup.find().
             Ethernet.find().Ipv4.find().BgpIpv4Peer.find())

    assert (bgpv4.CapabilitySRTEPoliciesV4.Values)[0] == 'true'

    bgpv4_sr_te = (ixnetwork.Topology.find().DeviceGroup.find().
                   Ethernet.find().Ipv4.find().BgpIpv4Peer.find().
                   BgpSRTEPoliciesListV4)
    for attr in BGPV4_SR_TE:
        assert BGPV4_SR_TE[attr] == (getattr(bgpv4_sr_te, attr).Values)[0]

    bgpv4_sr_te_tunnel = bgpv4_sr_te.BgpSRTEPoliciesTunnelEncapsulationListV4
    # import pdb;pdb.set_trace()
    for attr in BGPV4_SR_TE_TUNNEL:
        assert BGPV4_SR_TE_TUNNEL[attr] == (
            getattr(bgpv4_sr_te_tunnel, attr).Values)[0]

    bgpv4_sr_te_tunnel_seg_lists = (
        bgpv4_sr_te_tunnel.BgpSRTEPoliciesSegmentListV4)
    for attr in BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST:
        if attr == 'Weight':
            assert BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == (
                getattr(bgpv4_sr_te_tunnel_seg_lists, attr).Values)[0]
        else:
            assert BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == (
                getattr(bgpv4_sr_te_tunnel_seg_lists, attr))

    bgpv4_sr_te_tunnel_segments = (
        bgpv4_sr_te_tunnel_seg_lists.BgpSRTEPoliciesSegmentsCollectionV4)
    for attr in BGPV4_SR_TE_TUNNEL_SEGMENTS:
        assert BGPV4_SR_TE_TUNNEL_SEGMENTS[attr] == (
            getattr(bgpv4_sr_te_tunnel_segments, attr).Values)

    # bgpv6
    bgpv6 = (ixnetwork.Topology.find().DeviceGroup.find().
             Ethernet.find().Ipv6.find().BgpIpv6Peer.find())
    assert (bgpv6.CapabilitySRTEPoliciesV6.Values)[0] == 'true'

    bgpv6_sr_te = (ixnetwork.Topology.find().DeviceGroup.find().
                   Ethernet.find().Ipv6.find().BgpIpv6Peer.find().
                   BgpSRTEPoliciesListV6)
    for attr in BGPV6_SR_TE:
        assert BGPV6_SR_TE[attr] == (getattr(bgpv6_sr_te, attr).Values)[0]

    bgpv6_sr_te_tunnel = bgpv6_sr_te.BgpSRTEPoliciesTunnelEncapsulationListV6
    for attr in BGPV6_SR_TE_TUNNEL:
        assert BGPV6_SR_TE_TUNNEL[attr] == (
            getattr(bgpv6_sr_te_tunnel, attr).Values)[0]

    bgpv6_sr_te_tunnel_seg_lists = (
        bgpv6_sr_te_tunnel.BgpSRTEPoliciesSegmentListV6)
    for attr in BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST:
        if attr == 'Weight':
            assert BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == (
                getattr(bgpv6_sr_te_tunnel_seg_lists, attr).Values)[0]
        else:
            assert BGPV6_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == (
                getattr(bgpv6_sr_te_tunnel_seg_lists, attr))

    bgpv6_sr_te_tunnel_segments = (
        bgpv6_sr_te_tunnel_seg_lists.BgpSRTEPoliciesSegmentsCollectionV6)
    for attr in BGPV6_SR_TE_TUNNEL_SEGMENTS:
        assert BGPV6_SR_TE_TUNNEL_SEGMENTS[attr] == (
            getattr(bgpv6_sr_te_tunnel_segments, attr).Values)


if __name__ == '__main__':
    pytest.main(['-sv', __file__])
