"""
B2B tests for get_states(bgp_prefixes) — IxNetwork backend implementation
of OTG learned-prefix state (AS-path, next-hop, origin, MED, communities).

Topology (all tests)
--------------------
  Port tx ──── Port rx
  Device tx_dev          Device rx_dev
    eth1 (00:00:00:11)     eth2 (00:00:00:22)
    ipv4_1 10.1.1.1/24 ←→  ipv4_2 10.1.1.2/24
    [ipv6_1 2001:db8::1/64 ← → ipv6_2 2001:db8::2/64  (dual-stack tests)]

  bgpv4_peer1 ←iBGP→ bgpv4_peer2  (AS 65001)
  [bgpv6_peer1 ←iBGP→ bgpv6_peer2  (dual-stack tests)]

Route ranges
------------
  rr1  100.1.0.0/24 x 5   AS-path [100,200]  comm 1:2  MED 50  origin egp
  rr2  200.1.0.0/24 x 5   AS-path [300,400]  comm 3:4  MED 60  origin egp
  rr1v6  4000::/64 x 5    AS-path [500,600]  origin igp
  rr2v6  5000::/64 x 5    AS-path [700,800]  origin igp

  rr3  100.1.0.0/24 x 5   (eBGP / 4-byte AS config only)
                          AS-path as_seq [100,200] + as_set [300,400]
                                  + as_seq [4200000000]
                          comm 1:2, 65535:65535, no_export
                          MED 70  origin incomplete

The parsing logic these tests exercise end-to-end is also covered offline,
without a chassis, in test_bgp_prefix_parsers.py.
"""
import pytest


# ---------------------------------------------------------------------------
# Shared config builders
# ---------------------------------------------------------------------------

def _build_v4_config(api, b2b_raw_config):
    """Return b2b_raw_config wired for two iBGP peers with IPv4 route ranges
    that carry AS-path, community, MED and origin attributes."""
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = (
        b2b_raw_config.devices.device(name="tx_dev")
        .device(name="rx_dev")
    )

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name = p1.name
    eth2.connection.port_name = p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    eth1.name, eth2.name = "eth1", "eth2"

    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ipv4_1", "ipv4_2"
    ip1.address, ip1.gateway, ip1.prefix = "10.1.1.1", "10.1.1.2", 24
    ip2.address, ip2.gateway, ip2.prefix = "10.1.1.2", "10.1.1.1", 24

    bgp1, bgp2 = d1.bgp, d2.bgp
    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"

    i1, i2 = bgp1.ipv4_interfaces.add(), bgp2.ipv4_interfaces.add()
    i1.ipv4_name, i2.ipv4_name = ip1.name, ip2.name

    peer1, peer2 = i1.peers.add(), i2.peers.add()
    peer1.name, peer2.name = "bgpv4_peer1", "bgpv4_peer2"
    peer1.peer_address, peer1.as_type, peer1.as_number = "10.1.1.2", "ibgp", 65001
    peer2.peer_address, peer2.as_type, peer2.as_number = "10.1.1.1", "ibgp", 65001
    # Enable IxNetwork to capture IPv4 unicast routes in learnedInfo.
    # Without this flag the FilterIpV4Unicast Multivalue stays False and
    # GetIPv4LearnedInfo returns no data.
    peer1.learned_information_filter.unicast_ipv4_prefix = True
    peer2.learned_information_filter.unicast_ipv4_prefix = True

    # rr1: advertised by peer1, learned by peer2
    rr1 = peer1.v4_routes.add(name="rr1")
    rr1.addresses.add(address="100.1.0.0", prefix=24, count=5, step=1)
    seg1 = rr1.as_path.segments.add()
    seg1.type = seg1.AS_SEQ
    seg1.as_numbers = [100, 200]
    c1 = rr1.communities.add()
    c1.type = c1.MANUAL_AS_NUMBER
    c1.as_number, c1.as_custom = 1, 2
    rr1.advanced.multi_exit_discriminator = 50
    rr1.advanced.origin = rr1.advanced.EGP

    # rr2: advertised by peer2, learned by peer1
    rr2 = peer2.v4_routes.add(name="rr2")
    rr2.addresses.add(address="200.1.0.0", prefix=24, count=5, step=1)
    seg2 = rr2.as_path.segments.add()
    seg2.type = seg2.AS_SEQ
    seg2.as_numbers = [300, 400]
    c2 = rr2.communities.add()
    c2.type = c2.MANUAL_AS_NUMBER
    c2.as_number, c2.as_custom = 3, 4
    rr2.advanced.multi_exit_discriminator = 60
    rr2.advanced.origin = rr2.advanced.EGP

    return b2b_raw_config


def _build_rich_attrs_config(api, b2b_raw_config):
    """Return b2b_raw_config wired for **eBGP with 4-byte AS numbers** and a
    route range carrying several AS-path segments and several communities.

    Deliberately different from _build_v4_config on every axis the parsers
    have to handle:

    ==================  ====================  =========================
    axis                _build_v4_config      here
    ==================  ====================  =========================
    session type        iBGP, AS 65001        eBGP, AS 4200000001/2
    as_number_width     default ("four")      explicit "four", 4-byte AS
    AS-path segments    1 (as_seq)            3 (as_seq, as_set, as_seq)
    communities         1 (manual)            3 (2 manual + no_export)
    origin              egp                   incomplete
    ==================  ====================  =========================

    ``as_set_mode`` is left at its OTG default (``do_not_include_local_as``)
    so the learned AS path is exactly what is configured -- the local AS is
    not prepended, which keeps the assertions deterministic.
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = (
        b2b_raw_config.devices.device(name="tx_dev")
        .device(name="rx_dev")
    )

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name = p1.name
    eth2.connection.port_name = p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    eth1.name, eth2.name = "eth1", "eth2"

    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ipv4_1", "ipv4_2"
    ip1.address, ip1.gateway, ip1.prefix = "10.1.1.1", "10.1.1.2", 24
    ip2.address, ip2.gateway, ip2.prefix = "10.1.1.2", "10.1.1.1", 24

    bgp1, bgp2 = d1.bgp, d2.bgp
    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"

    i1, i2 = bgp1.ipv4_interfaces.add(), bgp2.ipv4_interfaces.add()
    i1.ipv4_name, i2.ipv4_name = ip1.name, ip2.name

    peer1, peer2 = i1.peers.add(), i2.peers.add()
    peer1.name, peer2.name = "bgpv4_peer1", "bgpv4_peer2"
    # eBGP with 4-byte AS numbers on both sides.  as_number_width is set
    # explicitly even though "four" is already the OTG default, so the test
    # keeps testing 4-byte encoding if that default ever changes.
    peer1.peer_address, peer1.as_type = "10.1.1.2", "ebgp"
    peer2.peer_address, peer2.as_type = "10.1.1.1", "ebgp"
    peer1.as_number, peer2.as_number = 4200000001, 4200000002
    peer1.as_number_width = peer2.as_number_width = "four"
    peer1.learned_information_filter.unicast_ipv4_prefix = True
    peer2.learned_information_filter.unicast_ipv4_prefix = True

    # rr3: advertised by peer1, learned by peer2.
    rr3 = peer1.v4_routes.add(name="rr3")
    rr3.addresses.add(address="100.1.0.0", prefix=24, count=5, step=1)

    seg_a = rr3.as_path.segments.add()
    seg_a.type = seg_a.AS_SEQ
    seg_a.as_numbers = [100, 200]
    seg_b = rr3.as_path.segments.add()
    seg_b.type = seg_b.AS_SET
    seg_b.as_numbers = [300, 400]
    # A 4-byte ASN inside the path, to prove asplain 4-byte values survive
    # the round trip through the learned-info AS Path column.
    seg_c = rr3.as_path.segments.add()
    seg_c.type = seg_c.AS_SEQ
    seg_c.as_numbers = [4200000000]

    c1 = rr3.communities.add()
    c1.type = c1.MANUAL_AS_NUMBER
    c1.as_number, c1.as_custom = 1, 2
    c2 = rr3.communities.add()
    c2.type = c2.MANUAL_AS_NUMBER
    c2.as_number, c2.as_custom = 65535, 65535
    c3 = rr3.communities.add()
    c3.type = c3.NO_EXPORT

    rr3.advanced.multi_exit_discriminator = 70
    rr3.advanced.origin = rr3.advanced.INCOMPLETE

    return b2b_raw_config


def _build_two_byte_as_config(api, b2b_raw_config):
    """Return b2b_raw_config using ``as_number_width = "two"``.

    2-byte AS numbers take a different branch in ``Bgp._config_as_number``
    (``localAs2Bytes`` rather than ``enable4ByteAs`` + ``localAs4Bytes``),
    and the default is "four", so this path is otherwise untested.
    """
    config = _build_v4_config(api, b2b_raw_config)
    for device in config.devices:
        for interface in device.bgp.ipv4_interfaces:
            for peer in interface.peers:
                peer.as_number_width = "two"
                peer.as_number = 65001
    return config


def _build_dual_stack_config(api, b2b_raw_config):
    """Return b2b_raw_config with both IPv4 and IPv6 BGP peers and routes."""
    config = _build_v4_config(api, b2b_raw_config)

    d1, d2 = [d for d in config.devices]

    eth1 = d1.ethernets[0]
    eth2 = d2.ethernets[0]

    ip6_1, ip6_2 = eth1.ipv6_addresses.add(), eth2.ipv6_addresses.add()
    ip6_1.name, ip6_2.name = "ipv6_1", "ipv6_2"
    ip6_1.address, ip6_1.gateway, ip6_1.prefix = "2001:db8::1", "2001:db8::2", 64
    ip6_2.address, ip6_2.gateway, ip6_2.prefix = "2001:db8::2", "2001:db8::1", 64

    bgp1, bgp2 = d1.bgp, d2.bgp

    i6_1, i6_2 = bgp1.ipv6_interfaces.add(), bgp2.ipv6_interfaces.add()
    i6_1.ipv6_name, i6_2.ipv6_name = ip6_1.name, ip6_2.name

    p6_1, p6_2 = i6_1.peers.add(), i6_2.peers.add()
    p6_1.name, p6_2.name = "bgpv6_peer1", "bgpv6_peer2"
    p6_1.peer_address, p6_1.as_type, p6_1.as_number = "2001:db8::2", "ibgp", 65001
    p6_2.peer_address, p6_2.as_type, p6_2.as_number = "2001:db8::1", "ibgp", 65001
    # Enable IxNetwork to capture IPv6 unicast routes in learnedInfo.
    p6_1.learned_information_filter.unicast_ipv6_prefix = True
    p6_2.learned_information_filter.unicast_ipv6_prefix = True

    # rr1v6: advertised by bgpv6_peer1, learned by bgpv6_peer2
    rr1v6 = p6_1.v6_routes.add(name="rr1v6")
    rr1v6.addresses.add(address="4000::", prefix=64, count=5, step=1)
    seg6_1 = rr1v6.as_path.segments.add()
    seg6_1.type = seg6_1.AS_SEQ
    seg6_1.as_numbers = [500, 600]
    rr1v6.advanced.origin = rr1v6.advanced.IGP

    # rr2v6: advertised by bgpv6_peer2, learned by bgpv6_peer1
    rr2v6 = p6_2.v6_routes.add(name="rr2v6")
    rr2v6.addresses.add(address="5000::", prefix=64, count=5, step=1)
    seg6_2 = rr2v6.as_path.segments.add()
    seg6_2.type = seg6_2.AS_SEQ
    seg6_2.as_numbers = [700, 800]
    rr2v6.advanced.origin = rr2v6.advanced.IGP

    return config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _segments_of(prefix):
    """Flatten a learned prefix's AS path to ``[(type, [asn, ...]), ...]``."""
    return [(s.type, list(s.as_numbers)) for s in prefix.as_path.segments]


def _communities_of(prefix):
    """Flatten a learned prefix's communities to comparable tuples.

    ``as_number``/``as_custom`` are ``None`` for well-known communities.
    """
    return [
        (c.type, c.as_number, c.as_custom) for c in prefix.communities
    ]


def _bgpv4_routes_exchanged(api, expected_rx=1):
    """Return True once at least *expected_rx* routes have been received
    across all BGPv4 sessions.  Ensures route UPDATEs have completed
    before querying learned-info."""
    req = api.metrics_request()
    req.bgpv4.column_names = ["session_state", "routes_received"]
    results = api.get_metrics(req)
    total_rx = sum(
        (m.routes_received or 0) for m in results.bgpv4_metrics
    )
    return total_rx >= expected_rx


def _bgpv4_sessions_up(api, expected_count=2):
    """Return True once exactly *expected_count* BGPv4 sessions report 'up'.

    Uses an empty peer_names list so that protocolmetrics returns all
    BGPv4 device-group rows.  Passing peer *names* (not device names)
    would cause the Device-Group filter inside protocolmetrics to drop
    every row, leaving an empty result regardless of session state.
    """
    req = api.metrics_request()
    req.bgpv4.column_names = ["session_state"]
    results = api.get_metrics(req)
    return (
        len(results.bgpv4_metrics) == expected_count
        and all(m.session_state == "up" for m in results.bgpv4_metrics)
    )


def _bgpv6_sessions_up(api, expected_count=2):
    """Return True once exactly *expected_count* BGPv6 sessions report 'up'."""
    req = api.metrics_request()
    req.bgpv6.column_names = ["session_state"]
    results = api.get_metrics(req)
    return (
        len(results.bgpv6_metrics) == expected_count
        and all(m.session_state == "up" for m in results.bgpv6_metrics)
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_bgp_prefix_states_ipv4_b2b(api, b2b_raw_config, utils):
    """
    Verify IPv4 unicast learned-prefix state is returned per BGP peer.

    bgpv4_peer2 should learn rr1 (100.1.0.0/24 × 5) with AS-path [100,200],
    community 1:2, MED 50 and origin EGP from bgpv4_peer1.
    """
    config = _build_v4_config(api, b2b_raw_config)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _bgpv4_sessions_up(api),
        "BGPv4 sessions to come up",
        timeout_seconds=30,
    )
    # Allow a moment for route UPDATEs to be fully exchanged before
    # querying learned info.
    utils.wait_for(
        lambda: _bgpv4_routes_exchanged(api, expected_rx=5),
        "BGPv4 routes to be received",
        timeout_seconds=30,
    )

    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = ["bgpv4_peer2"]
    states = api.get_states(req)

    assert len(states.bgp_prefixes) == 1
    peer_state = states.bgp_prefixes[0]
    assert peer_state.bgp_peer_name == "bgpv4_peer2"

    prefixes = peer_state.ipv4_unicast_prefixes
    assert len(prefixes) == 5

    # Spot-check the first returned prefix
    p = prefixes[0]
    assert p.ipv4_address.startswith("100.1.0.")
    assert p.prefix_length == 24
    assert p.origin == "egp"
    assert p.multi_exit_discriminator == 50

    # AS-path must carry exactly one AS_SEQ segment [100, 200]
    segs = p.as_path.segments
    assert len(segs) == 1
    assert segs[0].type == "as_seq"
    assert segs[0].as_numbers == [100, 200]

    # Assert the whole community list, not just that a match exists -- a
    # spurious extra entry or a mis-parsed as_custom would pass an any().
    assert _communities_of(p) == [("manual_as_number", 1, 2)]

    # Every prefix in the range must carry the same attributes, and the
    # addresses must be the five distinct /24s that were advertised.
    assert sorted(x.ipv4_address for x in prefixes) == [
        "100.1.%d.0" % n for n in range(5)
    ]
    for other in prefixes:
        assert other.prefix_length == 24
        assert other.origin == "egp"
        assert other.multi_exit_discriminator == 50
        assert _segments_of(other) == [("as_seq", [100, 200])]
        assert _communities_of(other) == [("manual_as_number", 1, 2)]


def test_bgp_prefix_states_all_peers_b2b(api, b2b_raw_config, utils):
    """
    Empty bgp_peer_names must return learned-prefix state for every
    configured peer.
    """
    config = _build_v4_config(api, b2b_raw_config)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _bgpv4_sessions_up(api),
        "BGPv4 sessions to come up",
        timeout_seconds=30,
    )
    utils.wait_for(
        lambda: _bgpv4_routes_exchanged(api, expected_rx=5),
        "BGPv4 routes to be received",
        timeout_seconds=30,
    )

    req = api.states_request()
    req.choice = "bgp_prefixes"
    # Leave bgp_peer_names empty → should return both peers
    states = api.get_states(req)

    peer_names_returned = {s.bgp_peer_name for s in states.bgp_prefixes}
    assert "bgpv4_peer1" in peer_names_returned
    assert "bgpv4_peer2" in peer_names_returned
    assert len(states.bgp_prefixes) == 2


def test_bgp_prefix_states_ipv6_b2b(api, b2b_raw_config, utils):
    """
    Verify IPv6 unicast learned-prefix state is returned for BGPv6 peers
    in a dual-stack configuration.

    bgpv6_peer2 should learn rr1v6 (4000::/64 × 5) with AS-path [500,600]
    and origin IGP from bgpv6_peer1.
    """
    config = _build_dual_stack_config(api, b2b_raw_config)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _bgpv6_sessions_up(api),
        "BGPv6 sessions to come up",
        timeout_seconds=30,
    )

    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = ["bgpv6_peer2"]
    states = api.get_states(req)

    assert len(states.bgp_prefixes) == 1
    peer_state = states.bgp_prefixes[0]
    assert peer_state.bgp_peer_name == "bgpv6_peer2"

    prefixes = peer_state.ipv6_unicast_prefixes
    assert len(prefixes) == 5

    p = prefixes[0]
    assert p.ipv6_address.lower().startswith("4000:")
    assert p.prefix_length == 64
    assert p.origin == "igp"

    segs = p.as_path.segments
    assert len(segs) == 1
    assert segs[0].type == "as_seq"
    assert segs[0].as_numbers == [500, 600]


def test_bgp_prefix_states_multi_segment_multi_community_b2b(
    api, b2b_raw_config, utils
):
    """
    eBGP with 4-byte AS numbers, three AS-path segments and three
    communities must all survive the learned-info round trip.

    This is the counterpart to the offline parser tests in
    test_bgp_prefix_parsers.py: those prove the parsers handle the shapes,
    this proves IxNetwork actually emits them.

    bgpv4_peer2 learns rr3 (100.1.0.0/24 x 5) advertised by bgpv4_peer1:
      AS path      as_seq [100,200] + as_set [300,400] + as_seq [4200000000]
      communities  1:2, 65535:65535, no_export
      MED 70, origin incomplete
    """
    config = _build_rich_attrs_config(api, b2b_raw_config)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _bgpv4_sessions_up(api),
        "BGPv4 eBGP sessions to come up",
        timeout_seconds=30,
    )
    utils.wait_for(
        lambda: _bgpv4_routes_exchanged(api, expected_rx=5),
        "BGPv4 routes to be received",
        timeout_seconds=30,
    )

    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = ["bgpv4_peer2"]
    states = api.get_states(req)

    prefixes = states.bgp_prefixes[0].ipv4_unicast_prefixes
    assert len(prefixes) == 5

    for p in prefixes:
        assert p.prefix_length == 24
        assert p.origin == "incomplete"
        assert p.multi_exit_discriminator == 70
        # Segment order and type must be preserved, and the 4-byte ASN must
        # come back as its asplain value rather than being dropped.
        #
        # The leading [4200000001] is bgpv4_peer1's own AS: over eBGP the
        # advertising speaker prepends it as a separate AS_SEQ segment.
        # That is standard BGP and happens regardless of the route's
        # as_set_mode (which only controls whether the local AS is folded
        # into the *configured* segments), so it is asserted rather than
        # worked around.
        assert _segments_of(p) == [
            ("as_seq", [4200000001]),
            ("as_seq", [100, 200]),
            ("as_set", [300, 400]),
            ("as_seq", [4200000000]),
        ]
        # Both manual communities plus the well-known NO_EXPORT.  Compared
        # as a set because the learned-info column order is not contractual.
        assert set(_communities_of(p)) == {
            ("manual_as_number", 1, 2),
            ("manual_as_number", 65535, 65535),
            ("no_export", None, None),
        }


def test_bgp_prefix_states_two_byte_as_b2b(api, b2b_raw_config, utils):
    """
    ``as_number_width = "two"`` must not change the learned-prefix result.

    The 2-byte branch of Bgp._config_as_number (``localAs2Bytes``) is
    otherwise untested, since "four" is the OTG default.
    """
    config = _build_two_byte_as_config(api, b2b_raw_config)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _bgpv4_sessions_up(api),
        "BGPv4 sessions to come up with 2-byte AS",
        timeout_seconds=30,
    )
    utils.wait_for(
        lambda: _bgpv4_routes_exchanged(api, expected_rx=5),
        "BGPv4 routes to be received",
        timeout_seconds=30,
    )

    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = ["bgpv4_peer2"]
    states = api.get_states(req)

    prefixes = states.bgp_prefixes[0].ipv4_unicast_prefixes
    assert len(prefixes) == 5
    for p in prefixes:
        assert _segments_of(p) == [("as_seq", [100, 200])]
        assert _communities_of(p) == [("manual_as_number", 1, 2)]
        assert p.origin == "egp"
        assert p.multi_exit_discriminator == 50


def test_bgp_prefix_states_filter_b2b(api, b2b_raw_config, utils):
    """
    ipv4_unicast_filters must narrow the result to matching prefixes only.

    A filter for address 100.1.0.0 / prefix_length 24 applied to
    bgpv4_peer2 (which learns 5 prefixes: 100.1.0.0–100.1.4.0 /24)
    should return exactly 1 matching prefix.
    """
    config = _build_v4_config(api, b2b_raw_config)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _bgpv4_sessions_up(api),
        "BGPv4 sessions to come up",
        timeout_seconds=30,
    )
    utils.wait_for(
        lambda: _bgpv4_routes_exchanged(api, expected_rx=5),
        "BGPv4 routes to be received",
        timeout_seconds=30,
    )

    # Unfiltered: expect 5 prefixes
    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = ["bgpv4_peer2"]
    unfiltered = api.get_states(req)
    assert len(unfiltered.bgp_prefixes[0].ipv4_unicast_prefixes) == 5

    # Filtered: only 100.1.0.0/24
    req2 = api.states_request()
    req2.bgp_prefixes.bgp_peer_names = ["bgpv4_peer2"]
    filt = req2.bgp_prefixes.ipv4_unicast_filters.add()
    filt.addresses = ["100.1.0.0"]
    filt.prefix_length = 24
    filtered = api.get_states(req2)

    filtered_prefixes = filtered.bgp_prefixes[0].ipv4_unicast_prefixes
    assert len(filtered_prefixes) == 1
    assert filtered_prefixes[0].ipv4_address == "100.1.0.0"
    assert filtered_prefixes[0].prefix_length == 24
