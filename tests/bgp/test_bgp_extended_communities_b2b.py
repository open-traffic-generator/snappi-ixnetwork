"""
B2B end-to-end tests for BGP extended communities on route ranges.

Topology
--------
  Port tx ──── Port rx
  Device tx_dev          Device rx_dev
    eth1 (00:00:00:11)     eth2 (00:00:00:22)
    10.1.1.1/24      ←→    10.1.1.2/24          (v4 test)
    2001:db8::1/64   ←→    2001:db8::2/64       (v6 test)

  peer1 ←iBGP→ peer2  (AS 65001)

  peer1 advertises a route range carrying five extended communities
  (route-target 2-octet AS / IPv4 / 4-octet AS, route-origin, custom);
  peer2 advertises a plain route range with none.

What is verified
----------------
  1. set_config accepts the extended_communities config (no AppErrors).
  2. The sessions come up and the routes are exchanged.
  3. The bgpExtendedCommunitiesList entries IxNetwork holds for peer1's
     route range (read back through restpy) match the config: type,
     subType and values, in order.
  4. The route range without extended communities has none.

The receiving side is deliberately not asserted: IxNetwork's learned-info
table has no extended-community column (see CAPTURED_V4_COLUMNS in
test_bgp_prefix_parsers.py), so get_states cannot report them.

Encoding/wiring is also covered offline in test_bgp_extended_communities.py.
"""
import pytest

PREFIX_COUNT = 5

# Expected IxNetwork bgpExtendedCommunitiesList fields, in configuration
# order (only the fields that apply to each entry).
EXPECTED_IXN = [
    {"type": "administratoras2octet", "subType": "routetarget",
     "asNumber2Bytes": 100, "assignedNumber4Bytes": 5},
    {"type": "administratoras2octet", "subType": "origin",
     "asNumber2Bytes": 200, "assignedNumber4Bytes": 9},
    {"type": "administratorip", "subType": "routetarget",
     "ip": "1.1.1.1", "assignedNumber2Bytes": 7},
    {"type": "administratoras4octet", "subType": "routetarget",
     "asNumber4Bytes": 70000, "assignedNumber2Bytes": 9},
    {"customExtCommType": "8009", "customExtCommValue": "aabbccddeeff"},
]

# restpy property name for each expected field
_RESTPY_ATTR = {
    "type": "Type",
    "subType": "SubType",
    "asNumber2Bytes": "AsNumber2Bytes",
    "asNumber4Bytes": "AsNumber4Bytes",
    "assignedNumber2Bytes": "AssignedNumber2Bytes",
    "assignedNumber4Bytes": "AssignedNumber4Bytes",
    "ip": "Ip",
    "customExtCommType": "CustomExtCommType",
    "customExtCommValue": "CustomExtCommValue",
}


def _add_extended_communities(route_range):
    """Attach the five extended communities in EXPECTED_RAW order."""
    e = route_range.extended_communities.add()
    e.transitive_2octet_as_type.route_target_subtype.global_2byte_as = 100
    e.transitive_2octet_as_type.route_target_subtype.local_4byte_admin = 5

    e = route_range.extended_communities.add()
    e.transitive_2octet_as_type.route_origin_subtype.global_2byte_as = 200
    e.transitive_2octet_as_type.route_origin_subtype.local_4byte_admin = 9

    e = route_range.extended_communities.add()
    e.transitive_ipv4_address_type.route_target_subtype.global_ipv4_admin = (
        "1.1.1.1"
    )
    e.transitive_ipv4_address_type.route_target_subtype.local_2byte_admin = 7

    e = route_range.extended_communities.add()
    e.transitive_4octet_as_type.route_target_subtype.global_4byte_as = 70000
    e.transitive_4octet_as_type.route_target_subtype.local_2byte_admin = 9

    e = route_range.extended_communities.add()
    e.custom.community_type = "80"
    e.custom.community_subtype = "09"
    e.custom.value = "aabbccddeeff"


def _build_config(api, b2b_raw_config, ip_version):
    """Wire b2b_raw_config for two iBGP peers; peer1's route range carries
    extended communities, peer2's does not."""
    api.set_config(api.config())
    b2b_raw_config.flows.clear()
    b2b_raw_config.devices.clear()

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

    bgp1, bgp2 = d1.bgp, d2.bgp
    bgp1.router_id, bgp2.router_id = "192.0.0.1", "192.0.0.2"

    if ip_version == 4:
        ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
        ip1.name, ip2.name = "ip_1", "ip_2"
        ip1.address, ip1.gateway, ip1.prefix = "10.1.1.1", "10.1.1.2", 24
        ip2.address, ip2.gateway, ip2.prefix = "10.1.1.2", "10.1.1.1", 24
        i1, i2 = bgp1.ipv4_interfaces.add(), bgp2.ipv4_interfaces.add()
        i1.ipv4_name, i2.ipv4_name = ip1.name, ip2.name
        addr1, addr2 = "10.1.1.2", "10.1.1.1"
    else:
        ip1, ip2 = eth1.ipv6_addresses.add(), eth2.ipv6_addresses.add()
        ip1.name, ip2.name = "ip_1", "ip_2"
        ip1.address, ip1.gateway, ip1.prefix = (
            "2001:db8::1", "2001:db8::2", 64
        )
        ip2.address, ip2.gateway, ip2.prefix = (
            "2001:db8::2", "2001:db8::1", 64
        )
        i1, i2 = bgp1.ipv6_interfaces.add(), bgp2.ipv6_interfaces.add()
        i1.ipv6_name, i2.ipv6_name = ip1.name, ip2.name
        addr1, addr2 = "2001:db8::2", "2001:db8::1"

    peer1, peer2 = i1.peers.add(), i2.peers.add()
    peer1.name, peer2.name = "peer1", "peer2"
    peer1.peer_address, peer1.as_type, peer1.as_number = addr1, "ibgp", 65001
    peer2.peer_address, peer2.as_type, peer2.as_number = addr2, "ibgp", 65001

    if ip_version == 4:
        peer1.learned_information_filter.unicast_ipv4_prefix = True
        peer2.learned_information_filter.unicast_ipv4_prefix = True
        rr1 = peer1.v4_routes.add(name="rr_ext")
        rr1.addresses.add(
            address="100.1.0.0", prefix=24, count=PREFIX_COUNT, step=1
        )
        rr2 = peer2.v4_routes.add(name="rr_plain")
        rr2.addresses.add(
            address="200.1.0.0", prefix=24, count=PREFIX_COUNT, step=1
        )
    else:
        peer1.learned_information_filter.unicast_ipv6_prefix = True
        peer2.learned_information_filter.unicast_ipv6_prefix = True
        rr1 = peer1.v6_routes.add(name="rr_ext")
        rr1.addresses.add(
            address="4000::", prefix=64, count=PREFIX_COUNT, step=1
        )
        rr2 = peer2.v6_routes.add(name="rr_plain")
        rr2.addresses.add(
            address="5000::", prefix=64, count=PREFIX_COUNT, step=1
        )

    _add_extended_communities(rr1)
    return b2b_raw_config


def _sessions_up(api, version):
    req = api.metrics_request()
    metrics_req = req.bgpv4 if version == 4 else req.bgpv6
    metrics_req.column_names = ["session_state"]
    results = api.get_metrics(req)
    rows = results.bgpv4_metrics if version == 4 else results.bgpv6_metrics
    return len(rows) == 2 and all(m.session_state == "up" for m in rows)


def _routes_received(api, version, expected):
    req = api.metrics_request()
    metrics_req = req.bgpv4 if version == 4 else req.bgpv6
    metrics_req.column_names = ["session_state", "routes_received"]
    results = api.get_metrics(req)
    rows = results.bgpv4_metrics if version == 4 else results.bgpv6_metrics
    return sum((m.routes_received or 0) for m in rows) >= expected


def _route_properties(api, version):
    """Return {route_range_name: BgpIPRouteProperty} as held by IxNetwork
    (read back through restpy)."""
    pools, props = (
        ("Ipv4PrefixPools", "BgpIPRouteProperty")
        if version == 4
        else ("Ipv6PrefixPools", "BgpV6IPRouteProperty")
    )
    result = {}
    for dg in api._ixnetwork.Topology.find().DeviceGroup.find():
        for ng in dg.NetworkGroup.find():
            for pool in getattr(ng, pools).find():
                for prop in getattr(pool, props).find():
                    result[ng.Name] = prop
    return result


def _multivalue(node, attr):
    return getattr(node, attr).Values[0]


def _pushed_fields(node, expected):
    """Read back, from *node*, the fields named in *expected*."""
    return {
        key: _multivalue(node, _RESTPY_ATTR[key]) for key in expected
    }


def _normalise(value):
    """restpy returns every multivalue as a string."""
    return str(value).lower()


def _assert_pushed(api, version, name, expected_list):
    """Assert the route range *name* holds exactly *expected_list*.

    IxNetwork keeps a default (unused) list entry on every route property,
    so "no extended communities" means the enable flag is off, not that
    the list is empty.
    """
    prop = _route_properties(api, version)[name]
    enabled = _normalise(_multivalue(prop, "EnableExtendedCommunity"))
    if not expected_list:
        assert enabled == "false"
        return
    assert enabled == "true"
    nodes = prop.BgpExtendedCommunitiesList.find()
    assert len(nodes) == len(expected_list)
    for node, expected in zip(nodes, expected_list):
        actual = _pushed_fields(node, expected)
        assert {k: _normalise(v) for k, v in actual.items()} == {
            k: _normalise(v) for k, v in expected.items()
        }


def _learned_prefix_count(api, peer_name, version):
    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = [peer_name]
    states = api.get_states(req)
    assert len(states.bgp_prefixes) == 1
    state = states.bgp_prefixes[0]
    return len(
        state.ipv4_unicast_prefixes
        if version == 4
        else state.ipv6_unicast_prefixes
    )


@pytest.mark.parametrize("version", [4, 6])
def test_bgp_extended_communities_b2b(api, b2b_raw_config, utils, version):
    """
    peer1 advertises PREFIX_COUNT routes tagged with five extended
    communities.  The sessions must come up, every prefix must be
    exchanged, and IxNetwork must hold exactly the configured extended
    communities on peer1's route range (and none on peer2's).
    """
    config = _build_config(api, b2b_raw_config, version)
    utils.start_traffic(api, config, start_capture=False)

    utils.wait_for(
        lambda: _sessions_up(api, version),
        "BGP sessions to come up",
        timeout_seconds=30,
    )
    utils.wait_for(
        lambda: _routes_received(api, version, 2 * PREFIX_COUNT),
        "BGP routes to be received on both peers",
        timeout_seconds=30,
    )

    assert _learned_prefix_count(api, "peer2", version) == PREFIX_COUNT
    assert _learned_prefix_count(api, "peer1", version) == PREFIX_COUNT

    _assert_pushed(api, version, "rr_ext", EXPECTED_IXN)
    _assert_pushed(api, version, "rr_plain", [])


def test_bgp_extended_communities_removed_on_reconfig(
    api, b2b_raw_config, utils
):
    """
    Re-pushing the same config without extended communities must remove
    them from the route range while the routes are still advertised.
    """
    config = _build_config(api, b2b_raw_config, 4)
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _routes_received(api, 4, 2 * PREFIX_COUNT),
        "BGP routes to be received",
        timeout_seconds=60,
    )
    _assert_pushed(api, 4, "rr_ext", EXPECTED_IXN)

    config = _build_config(api, b2b_raw_config, 4)
    rr = config.devices[0].bgp.ipv4_interfaces[0].peers[0].v4_routes[0]
    rr.extended_communities.clear()
    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: _routes_received(api, 4, 2 * PREFIX_COUNT),
        "BGP routes to be received after reconfig",
        timeout_seconds=60,
    )
    assert _learned_prefix_count(api, "peer2", 4) == PREFIX_COUNT
    _assert_pushed(api, 4, "rr_ext", [])
