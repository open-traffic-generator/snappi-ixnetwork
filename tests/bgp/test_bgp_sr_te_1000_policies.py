import pytest
from functools import reduce


def test_bgp_sr_te_1000_policies(api):
    """
    Test BGP SRTE Policy configuration applied properly for 1000 policies

    Validate the configuration against RestPy
    """
    BGPV4_SR_TE = {
        'PolicyType': 'ipv4',
        'Distinguisher': 1,
        'PolicyColor': 1,
        'EndPointV4': '10.10.10.2',
        'SetNextHop': 'manually',
        'SetNextHopIpType': 'ipv4',
        'Ipv4NextHop': '10.10.10.2',
    }
    BGPV4_SR_TE_TUNNEL = {
        'PrefValue': 400,
        'BindingSIDType': 'sid4',
        'SID4Octet': 483001,
        'UseAsMPLSLabel': 'true'
    }

    BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST = {
        'Count': 1000,
        'NumberOfSegmentsV4': 5,
        'EnWeight': 'True',
        'Weight': 1,
    }

    BGPV4_SR_TE_TUNNEL_SEGMENTS = {
        'SegmentType': 'mplssid',
        'Label': [1018001, 432999, 1048333, 1048561, 432001],
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

    # setup ipv6
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
    bgp.as_type = 'ebgp'
    bgp.as_number_set_mode = bgp.DO_NOT_INCLUDE_AS
    bgp.local_address = '10.10.10.1'
    bgp.dut_address = '10.10.10.2'

    # setup bgp advanced
    bgp.advanced.hold_time_interval = 90
    bgp.advanced.keep_alive_interval = 30

    # setup bgp sr te policy
    for i in range(1, 1001):
        policy = bgp.sr_te_policies.bgpsrtepolicy()[-1]
        policy.policy_type = policy.IPV4
        policy.distinguisher = BGPV4_SR_TE['Distinguisher']
        policy.color = i
        policy.ipv4_endpoint = BGPV4_SR_TE['EndPointV4']

        hop = policy.next_hop
        hop.next_hop_mode = hop.MANUAL
        hop.next_hop_address_type = hop.IPV4
        hop.ipv4_address = BGPV4_SR_TE['Ipv4NextHop']

        # setup tunnel tlv
        tunnel = policy.tunnel_tlvs.bgptunneltlv(active=True)[-1]

        # setup tunnel tlv segment lists
        seglist = tunnel.segment_lists.bgpsegmentlist(active=True)[-1]
        seglist.segment_weight = 1

        # setup preference sub tlv
        pref_sub_tlv = tunnel.preference_sub_tlv
        pref_sub_tlv.preference = BGPV4_SR_TE_TUNNEL['PrefValue']

        # setup binding sub tlv
        bind_sub_tlv = tunnel.binding_sub_tlv
        bind_sub_tlv.binding_sid_type = bind_sub_tlv.FOUR_OCTET_SID
        bind_sub_tlv.four_octet_sid = BGPV4_SR_TE_TUNNEL['SID4Octet']
        bind_sub_tlv.bsid_as_mpls_label = True

        # setup segment list segments
        for label in BGPV4_SR_TE_TUNNEL_SEGMENTS['Label']:
            seg = seglist.segments.bgpsegment(active=True)[-1]
            seg.segment_type = seg.MPLS_SID
            seg.mpls_label = label

    api.set_config(config)

    validate_sr_te_config(api,
                          BGPV4_SR_TE,
                          BGPV4_SR_TE_TUNNEL,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS
                          )


def validate_sr_te_config(api,
                          BGPV4_SR_TE,
                          BGPV4_SR_TE_TUNNEL,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS):
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
        if attr == 'PolicyType':
            assert [BGPV4_SR_TE[attr] for i in range(1, 1001)] == getattr(
                bgpv4_sr_te, attr).Values
        elif attr == 'PolicyColor':
            assert [i for i in range(1, 1001)] == (
                [int(value) for value in getattr(bgpv4_sr_te, attr).Values])
        elif attr == 'Distinguisher':
            assert BGPV4_SR_TE[attr] == int((
                getattr(bgpv4_sr_te, attr).Values)[0])
        else:
            assert BGPV4_SR_TE[attr] == (getattr(bgpv4_sr_te, attr).Values)[0]

    bgpv4_sr_te_tunnel = bgpv4_sr_te.BgpSRTEPoliciesTunnelEncapsulationListV4
    for attr in BGPV4_SR_TE_TUNNEL:
        if attr in ['PrefValue', 'SID4Octet']:
            assert [BGPV4_SR_TE_TUNNEL[attr] for i in range(1, 1001)] == (
                [int(value) for value in getattr(
                    bgpv4_sr_te_tunnel, attr).Values])
        else:
            assert [BGPV4_SR_TE_TUNNEL[attr] for i in range(1, 1001)] == (
                getattr(bgpv4_sr_te_tunnel, attr).Values)

    bgpv4_sr_te_tunnel_seg_lists = (
        bgpv4_sr_te_tunnel.BgpSRTEPoliciesSegmentListV4)
    for attr in BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST:
        if attr == 'Weight':
            assert BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == int((
                getattr(bgpv4_sr_te_tunnel_seg_lists, attr).Values)[0])
        else:
            assert BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == (
                getattr(bgpv4_sr_te_tunnel_seg_lists, attr))

    bgpv4_sr_te_tunnel_segments = (
        bgpv4_sr_te_tunnel_seg_lists.BgpSRTEPoliciesSegmentsCollectionV4)
    for attr in BGPV4_SR_TE_TUNNEL_SEGMENTS:
        if attr == 'Label':
            lg = [BGPV4_SR_TE_TUNNEL_SEGMENTS[attr] for i in range(1, 1001)]
            assert reduce(lambda x, y: x + y, lg) == (
                [int(value) for value in getattr(
                    bgpv4_sr_te_tunnel_segments, attr).Values])
        else:
            assert [BGPV4_SR_TE_TUNNEL_SEGMENTS[attr] for i in range(
                1, 5001)] == getattr(bgpv4_sr_te_tunnel_segments, attr).Values


if __name__ == '__main__':
    pytest.main(['-sv', __file__])
