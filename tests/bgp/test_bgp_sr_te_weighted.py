import pytest


def test_bgp_sr_te_weighted(api):
    """
    Test BGP SRTE Policy configuration applied properly
    1) 2 policies with different weights
    2) BSID as MPLS label

    Validate the configuration against RestPy
    """
    BGPV4_SR_TE_TUNNEL = {
        'BindingSIDType': 'ipv6sid',
        'IPv6SID': '3000::1',
    }

    BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST = {
        'Weight': ['1', '4'],
    }

    BGPV4_SR_TE_TUNNEL_SEGMENTS = {
        'Label': ['16002', '16004', '16005', '16004'],
        'Vflag': ['true', 'true', 'false', 'false'],
        'RemainingBits': ['1', '1', '0', '0']

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
    policy.distinguisher = 1
    policy.color = 20
    policy.ipv4_endpoint = '1.1.1.4'

    # setup tunnel tlv
    tunnel = policy.tunnel_tlvs.bgptunneltlv(active=True)[-1]

    bind_sub_tlv = tunnel.binding_sub_tlv
    bind_sub_tlv.binding_sid_type = bind_sub_tlv.IPV6_SID
    bind_sub_tlv.ipv6_sid = "3000::1"

    # setup tunnel tlv segment lists
    seglist1 = tunnel.segment_lists.bgpsegmentlist(active=True)[-1]
    seglist1.segment_weight = int(
        BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST['Weight'][0])

    seglist2 = tunnel.segment_lists.bgpsegmentlist(active=True)[-1]
    seglist2.segment_weight = int(
        BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST['Weight'][1])

    # setup segment list segments
    for label in BGPV4_SR_TE_TUNNEL_SEGMENTS['Label'][0:2]:
        seg = seglist1.segments.bgpsegment(active=True)[-1]
        seg.segment_type = seg.MPLS_SID
        seg.mpls_label = label
        seg.v_flag = True
        seg.remaining_flag_bits = '0x01'

    for label in BGPV4_SR_TE_TUNNEL_SEGMENTS['Label'][2:]:
        seg = seglist2.segments.bgpsegment(active=True)[-1]
        seg.segment_type = seg.MPLS_SID
        seg.mpls_label = label

    api.set_config(config)

    validate_sr_te_config(api,
                          BGPV4_SR_TE_TUNNEL,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS
                          )


def validate_sr_te_config(api,
                          BGPV4_SR_TE_TUNNEL,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST,
                          BGPV4_SR_TE_TUNNEL_SEGMENTS):
    """
    Validate BGP SRTE Attributes Config
    """

    ixnetwork = api._ixnetwork
    bgpv4 = (ixnetwork.Topology.find().DeviceGroup.find().
             Ethernet.find().Ipv4.find().BgpIpv4Peer.find())

    assert (bgpv4.CapabilitySRTEPoliciesV4.Values)[0] == 'true'

    bgpv4_sr_te = (ixnetwork.Topology.find().DeviceGroup.find().
                   Ethernet.find().Ipv4.find().BgpIpv4Peer.find().
                   BgpSRTEPoliciesListV4)

    bgpv4_sr_te_tunnel = bgpv4_sr_te.BgpSRTEPoliciesTunnelEncapsulationListV4
    for attr in BGPV4_SR_TE_TUNNEL:
        assert BGPV4_SR_TE_TUNNEL[attr] == getattr(
            bgpv4_sr_te_tunnel, attr).Values[0]

    bgpv4_sr_te_tunnel_seg_lists = (
        bgpv4_sr_te_tunnel.BgpSRTEPoliciesSegmentListV4)
    for attr in BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST:
        assert BGPV4_SR_TE_TUNNEL_SEGMENTS_LIST[attr] == (
            getattr(bgpv4_sr_te_tunnel_seg_lists, attr).Values)

    bgpv4_sr_te_tunnel_segments = (
        bgpv4_sr_te_tunnel_seg_lists.BgpSRTEPoliciesSegmentsCollectionV4)
    for attr in BGPV4_SR_TE_TUNNEL_SEGMENTS:
        assert BGPV4_SR_TE_TUNNEL_SEGMENTS[attr] == (
            getattr(bgpv4_sr_te_tunnel_segments, attr).Values)


if __name__ == '__main__':
    pytest.main(['-sv', __file__])

