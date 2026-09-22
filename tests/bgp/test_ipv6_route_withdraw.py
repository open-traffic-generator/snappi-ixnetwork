import pytest


# --------------------------------------------------------------------------- #
# BGP IPv6 route-range withdraw — compacted node / multiplier scenario
#
# When N structurally-identical IPv6 BGP route ranges are configured (one per
# device-group instance, multiplier > 1), the compactor merges them into a
# single multiplied IxNetwork node.  Two defects existed in that path:
#
#   Defect A (ngpf.py)    — set_route_state raised KeyError when >= 2 names
#                           that share the same compacted node were passed as a
#                           list.  A single name never hit the else-branch, so
#                           individual withdraw worked; subset (list) withdraw
#                           did not.
#
#   Defect B (objectdb.py) — set_scalable silently skipped IPv6 members whose
#                            pre-compaction key set differed from the compacted
#                            representative, leaving them with xpath == '' and
#                            index == 0.  This made any per-name operation on
#                            those members fail or target the wrong instance.
#
# This test is the end-to-end gate for both defects:
#   * N = 4 identical eBGP peers (>= 2 is enough to force compaction).
#   * Each peer advertises one IPv6 route range; all ranges compact into one
#     multiplied bgpV6IPRouteProperty node with N instances.
#   * A subset (list of >= 2 names) is withdrawn, then re-advertised.
# --------------------------------------------------------------------------- #

PEER_COUNT = 4          # >= 2 is enough to force compaction
ROUTE_COUNT = 5         # /128 prefixes advertised per peer


def _v6_route_names(prefix="tc1"):
    return ["%s_peer%d_routes_ipv6" % (prefix, i) for i in range(PEER_COUNT)]


def test_ipv6_route_withdraw_subset_e2e(api, b2b_raw_config, utils):
    """Verify that a subset of IPv6 route ranges that were compacted into a
    single multiplied node can be withdrawn and re-advertised by name.

    Scenario
    --------
    N identical eBGP peers are configured, each advertising one IPv6 route
    range.  Because all ranges are structurally identical, snappi_ixnetwork
    compacts them into a single bgpV6IPRouteProperty node with N instances.

    The test asserts:
      1. Pre-condition: every compacted member resolves to a non-empty xpath
         and a unique index in [0, N) (Defect B regression check).
      2. Withdrawing a subset by list of names does not raise an error
         (Defect A regression check).
      3. Only the requested instances flip inactive; untouched members remain
         advertised.
      4. Re-advertising the same subset restores all instances.
    """
    config = b2b_raw_config
    api.set_config(api.config())
    config.flows.clear()

    p1, p2 = config.ports
    route_names = _v6_route_names()

    # N identical tx peers on p1, mirrored by N rx peers on p2. Each peer sits
    # on its own /64 so the eBGP sessions come up back-to-back; the ranges are
    # structurally identical, so snappi_ixnetwork compacts them into one node.
    for i in range(PEER_COUNT):
        # --- tx side ---
        tx_dev = config.devices.add(name="tx_peer%d" % i)
        tx_eth = tx_dev.ethernets.add(name="tx_eth%d" % i)
        tx_eth.connection.port_name = p1.name
        tx_eth.mac = "00:10:00:00:00:%02x" % i
        tx_ip = tx_eth.ipv6_addresses.add(name="tx_ip%d" % i)
        tx_ip.address = "2000:%d::1" % i
        tx_ip.gateway = "2000:%d::2" % i
        tx_ip.prefix = 64

        tx_bgp = tx_dev.bgp
        tx_bgp.router_id = "1.1.1.%d" % (i + 1)
        tx_int = tx_bgp.ipv6_interfaces.add()
        tx_int.ipv6_name = tx_ip.name
        tx_peer = tx_int.peers.add(name="tx_bgp_peer%d" % i)
        tx_peer.peer_address = "2000:%d::2" % i
        tx_peer.as_type = "ebgp"
        tx_peer.as_number = 65000 + i

        tx_route = tx_peer.v6_routes.add(name=route_names[i])
        tx_route.addresses.add(
            address="3000:%d::1" % i, prefix=128, count=ROUTE_COUNT, step=1
        )

        # --- rx side (mirror, single aggregate route range per peer) ---
        rx_dev = config.devices.add(name="rx_peer%d" % i)
        rx_eth = rx_dev.ethernets.add(name="rx_eth%d" % i)
        rx_eth.connection.port_name = p2.name
        rx_eth.mac = "00:20:00:00:00:%02x" % i
        rx_ip = rx_eth.ipv6_addresses.add(name="rx_ip%d" % i)
        rx_ip.address = "2000:%d::2" % i
        rx_ip.gateway = "2000:%d::1" % i
        rx_ip.prefix = 64

        rx_bgp = rx_dev.bgp
        rx_bgp.router_id = "2.2.2.%d" % (i + 1)
        rx_int = rx_bgp.ipv6_interfaces.add()
        rx_int.ipv6_name = rx_ip.name
        rx_peer = rx_int.peers.add(name="rx_bgp_peer%d" % i)
        rx_peer.peer_address = "2000:%d::1" % i
        rx_peer.as_type = "ebgp"
        rx_peer.as_number = 55000 + i

    api.set_config(config)

    # --- the compaction precondition: all N ranges resolve to ONE node ------- #
    # (This is what makes the subset withdraw exercise the compacted path.)
    xpaths = {api.ixn_routes.get(n).xpath for n in route_names}
    assert "" not in xpaths, (
        "a compacted IPv6 member resolved to an empty xpath (Defect B): %s"
        % {n: api.ixn_routes.get(n).xpath for n in route_names}
    )
    assert len(xpaths) == 1, (
        "expected all %d identical IPv6 ranges to compact into one node, "
        "got xpaths: %s" % (PEER_COUNT, xpaths)
    )
    rep_xpath = xpaths.pop()
    indices = sorted(api.ixn_routes.get(n).index for n in route_names)
    assert indices == list(range(PEER_COUNT)), (
        "compacted members must carry a unique index in [0, N): got %s"
        % indices
    )

    # --- start protocols and wait for every session up ----------------------- #
    ps = api.control_state()
    ps.choice = ps.PROTOCOL
    ps.protocol.choice = ps.protocol.ALL
    ps.protocol.all.state = ps.protocol.all.START
    res = api.set_control_state(ps)
    assert len(res.warnings) == 0, res.warnings

    def _all_sessions_up():
        req = api.metrics_request()
        req.bgpv6.peer_names = []
        metrics = api.get_metrics(req).bgpv6_metrics
        return len(metrics) > 0 and all(
            m.session_state == "up" for m in metrics
        )

    utils.wait_for(_all_sessions_up, "all BGPv6 sessions up")

    # --- the customer ask: withdraw a SUBSET by list of names ---------------- #
    withdraw_subset = [route_names[1], route_names[2]]   # 2 of N, >= 2 names
    keep_subset = [route_names[0], route_names[3]]

    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.choice = cs.protocol.ROUTE
    cs.protocol.route.names = withdraw_subset
    cs.protocol.route.state = cs.protocol.route.WITHDRAW
    # Pre-fix this raised `KeyError` in Ngpf.set_route_state; it must not now.
    res = api.set_control_state(cs)
    assert len(res.warnings) == 0, res.warnings

    # Only the two requested instances of the compacted node are inactive.
    active = api.ngpf.select_properties(rep_xpath, properties=["active"])[
        "active"
    ]["values"]
    assert len(active) == PEER_COUNT
    for name in withdraw_subset:
        idx = api.ixn_routes.get(name).index
        assert active[idx] == "false", (
            "instance %d (%s) should be withdrawn" % (idx, name)
        )
    for name in keep_subset:
        idx = api.ixn_routes.get(name).index
        assert active[idx] == "true", (
            "instance %d (%s) must remain advertised" % (idx, name)
        )

    # --- advertise the same subset back: every instance restored ------------- #
    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.choice = cs.protocol.ROUTE
    cs.protocol.route.names = withdraw_subset
    cs.protocol.route.state = cs.protocol.route.ADVERTISE
    res = api.set_control_state(cs)
    assert len(res.warnings) == 0, res.warnings

    active = api.ngpf.select_properties(rep_xpath, properties=["active"])[
        "active"
    ]["values"]
    assert all(v == "true" for v in active), (
        "all instances should be advertised after re-advertise: %s" % active
    )

    api.set_config(api.config())


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
