"""
Unit tests for BGP extended-community config encoding (Bgp._EXTENDED_COMMUNITY_TYPE
/ _EXTENDED_COMMUNITY_SUBTYPE / _configure_extended_community / wiring into
_configure_route) and learned-state readback (Bgp._parse_extended_communities).

These build real snappi config objects (no chassis/REST connection involved)
rather than hand-written dicts, so that the choice/factory-property shape of
BgpExtendedCommunity -- and in particular the fact that iterating a route
range's extended_communities yields the *resolved* choice object rather than
the BgpExtendedCommunity wrapper -- is exercised the same way it is in
production, not re-guessed in the test.
"""
import logging

import pytest
import snappi

from snappi_ixnetwork.device.bgp import Bgp

try:  # pragma: no cover - import shape differs across Python versions
    from unittest.mock import MagicMock
except ImportError:  # pragma: no cover
    from mock import MagicMock


@pytest.fixture
def bgp():
    """A Bgp instance with a stubbed ngpf -- these tests never touch it."""
    return Bgp(MagicMock())


def make_route_range():
    """A minimal, valid BgpV4RouteRange with no extended_communities yet.

    Built through the real snappi config tree (not a hand-rolled object) so
    that a renamed/removed OTG field would break this test rather than
    silently keep passing.
    """
    config = snappi.Api().config()
    device = config.devices.device(name="d1")[-1]
    device.bgp.router_id = "1.1.1.1"
    device.ethernets.ethernet(name="eth1")[-1].ipv4_addresses.add(
        name="ip1"
    )
    peer = device.bgp.ipv4_interfaces.add(ipv4_name="ip1").peers.add(
        peer_address="2.2.2.2", as_type="ibgp", as_number=100
    )
    route_range = peer.v4_routes.add(name="rr1")
    route_range.addresses.add(address="10.0.0.0", prefix=24, count=1, step=1)
    route_range.next_hop_mode = "local_ip"
    return route_range


def values(ixn_node):
    """Unwrap every MultiValue in an ixn node dict, dropping "xpath"."""
    return {
        key: value.value
        for key, value in ixn_node.items()
        if key != "xpath"
    }


# ---------------------------------------------------------------------------
# _configure_extended_community -- one case per top-level type/subtype
# ---------------------------------------------------------------------------


def test_transitive_2octet_route_target(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    ext.transitive_2octet_as_type.route_target_subtype.global_2byte_as = 100
    ext.transitive_2octet_as_type.route_target_subtype.local_4byte_admin = 5

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratoras2octet",
        "subType": "routetarget",
        "asNumber2Bytes": 100,
        "assignedNumber4Bytes": 5,
    }


def test_transitive_2octet_route_origin(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    ext.transitive_2octet_as_type.route_origin_subtype.global_2byte_as = 200
    ext.transitive_2octet_as_type.route_origin_subtype.local_4byte_admin = 9

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratoras2octet",
        "subType": "origin",
        "asNumber2Bytes": 200,
        "assignedNumber4Bytes": 9,
    }


def test_transitive_2octet_link_bandwidth(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    ext.transitive_2octet_as_type.link_bandwidth_subtype.global_2byte_as = 300
    ext.transitive_2octet_as_type.link_bandwidth_subtype.bandwidth = 12.5

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratoras2octet",
        "subType": "extendedbandwidth",
        "asNumber2Bytes": 300,
        "linkBandwidth": 12.5,
    }


def test_transitive_ipv4_route_target(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.transitive_ipv4_address_type.route_target_subtype
    sub.global_ipv4_admin = "1.1.1.1"
    sub.local_2byte_admin = 7

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratorip",
        "subType": "routetarget",
        "ip": "1.1.1.1",
        "assignedNumber2Bytes": 7,
    }


def test_transitive_ipv4_route_origin(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.transitive_ipv4_address_type.route_origin_subtype
    sub.global_ipv4_admin = "2.2.2.2"
    sub.local_2byte_admin = 11

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratorip",
        "subType": "origin",
        "ip": "2.2.2.2",
        "assignedNumber2Bytes": 11,
    }


def test_transitive_4octet_route_target(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.transitive_4octet_as_type.route_target_subtype
    sub.global_4byte_as = 70000
    sub.local_2byte_admin = 3

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratoras4octet",
        "subType": "routetarget",
        "asNumber4Bytes": 70000,
        "assignedNumber2Bytes": 3,
    }


def test_transitive_4octet_route_origin(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.transitive_4octet_as_type.route_origin_subtype
    sub.global_4byte_as = 80000
    sub.local_2byte_admin = 4

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratoras4octet",
        "subType": "origin",
        "asNumber4Bytes": 80000,
        "assignedNumber2Bytes": 4,
    }


def test_transitive_opaque_color(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.transitive_opaque_type.color_subtype
    sub.flags = 1
    sub.color = 42

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "opaque",
        "subType": "color",
        "colorCOBits": 1,
        "colorValue": 42,
    }


def test_transitive_opaque_encapsulation_packs_into_opaque_data(bgp):
    """No dedicated reserved/tunnel_type field exists on
    bgpExtendedCommunitiesList, so both
    values are packed into the generic 6-byte opaqueData field instead.
    """
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.transitive_opaque_type.encapsulation_subtype
    sub.reserved = 0
    sub.tunnel_type = 8

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "opaque",
        "subType": "encapsulation",
        "opaqueData": "000000000008",
    }


def test_transitive_evpn_router_mac_packs_into_opaque_data(bgp):
    """No dedicated MAC field exists on bgpExtendedCommunitiesList either,
    so the router MAC is packed into opaqueData the same way EVPN's own
    extended-community path already does for types it has no field for.
    """
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    ext.transitive_evpn_type.router_mac_subtype.router_mac = (
        "aa:bb:cc:dd:ee:ff"
    )

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "evpn",
        "subType": "macaddress",
        "opaqueData": "aabbccddeeff",
    }


def test_non_transitive_link_bandwidth(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    sub = ext.non_transitive_2octet_as_type.link_bandwidth_subtype
    sub.global_2byte_as = 400
    sub.bandwidth = 1.0

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "type": "administratoras2octetlinkbw",
        "subType": "extendedbandwidth",
        "asNumber2Bytes": 400,
        "linkBandwidth": 1.0,
    }


def test_custom(bgp):
    route_range = make_route_range()
    ext = route_range.extended_communities.add()
    ext.custom.community_type = "80"
    ext.custom.community_subtype = "09"
    ext.custom.value = "aabbccddeeff"

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    # "custom" has no type/subType of its own -- it is carried entirely via
    # the Custom* fields.
    assert values(ixn_ext) == {
        "customExtCommType": "8009",
        "customExtCommValue": "aabbccddeeff",
    }


def test_custom_defaults(bgp):
    """snappi's own defaults ('00', '00', '000000000000') round-trip."""
    route_range = make_route_range()
    route_range.extended_communities.add().custom

    ixn_ext = {}
    bgp._configure_extended_community(
        route_range.get("extended_communities")[0].parent, ixn_ext
    )

    assert values(ixn_ext) == {
        "customExtCommType": "0000",
        "customExtCommValue": "000000000000",
    }


def test_unsupported_top_level_choice_warns_and_sets_nothing(bgp, caplog):
    """A hand-built wrapper with a choice this repo doesn't know about
    (simulating a future OTG model addition) must warn, not raise or
    silently emit a half-configured node.
    """
    unsupported = MagicMock()
    unsupported.get.return_value = "some_future_type"

    ixn_ext = {}
    with caplog.at_level(logging.WARNING):
        bgp._configure_extended_community(unsupported, ixn_ext)

    assert ixn_ext == {}
    assert caplog.records, "unsupported extended community type was silent"


# ---------------------------------------------------------------------------
# Wiring into _configure_route
# ---------------------------------------------------------------------------


def test_configure_route_wires_extended_communities(bgp):
    route_range = make_route_range()
    first = route_range.extended_communities.add()
    first.transitive_2octet_as_type.route_target_subtype.global_2byte_as = (
        100
    )
    first.transitive_2octet_as_type.route_target_subtype.local_4byte_admin = (
        5
    )
    second = route_range.extended_communities.add()
    second.custom.community_type = "80"
    second.custom.community_subtype = "09"
    second.custom.value = "aabbccddeeff"

    ixn_route = {}
    bgp._configure_route(route_range, ixn_route)

    assert ixn_route["enableExtendedCommunity"].value is True
    assert ixn_route["noOfExternalCommunities"] == 2

    nodes = ixn_route["bgpExtendedCommunitiesList"]
    assert len(nodes) == 2
    assert values(nodes[0])["type"] == "administratoras2octet"
    assert values(nodes[1])["customExtCommType"] == "8009"


def test_configure_route_without_extended_communities_does_not_add_node(
    bgp,
):
    route_range = make_route_range()

    ixn_route = {}
    bgp._configure_route(route_range, ixn_route)

    assert "enableExtendedCommunity" not in ixn_route
    assert "bgpExtendedCommunitiesList" not in ixn_route


# ---------------------------------------------------------------------------
# _parse_extended_communities -- learned-state readback
# ---------------------------------------------------------------------------


def test_parse_extended_communities_raw_tokens(bgp):
    result = bgp._parse_extended_communities(
        "0002000000000064 0x0003000000000065"
    )
    assert result == [
        {"raw": "0002000000000064"},
        {"raw": "0003000000000065"},
    ]


def test_parse_extended_communities_comma_separated(bgp):
    result = bgp._parse_extended_communities(
        "0002000000000064,0003000000000065"
    )
    assert result == [
        {"raw": "0002000000000064"},
        {"raw": "0003000000000065"},
    ]


@pytest.mark.parametrize("cell", [None, "", "  ", "N/A", "n/a"])
def test_parse_extended_communities_empty_cell(bgp, cell):
    assert bgp._parse_extended_communities(cell) == []


def test_parse_extended_communities_bad_token_warns_and_skips(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        result = bgp._parse_extended_communities("not-hex")
    assert result == []
    assert caplog.records, "unparseable extended community was dropped silently"


def test_parse_extended_communities_bad_token_does_not_lose_good_ones(
    bgp, caplog
):
    with caplog.at_level(logging.WARNING):
        result = bgp._parse_extended_communities(
            "0002000000000064 garbage 0003000000000065"
        )
    assert result == [
        {"raw": "0002000000000064"},
        {"raw": "0003000000000065"},
    ]
    assert caplog.records


def test_row_to_ipv4_prefix_includes_empty_extended_communities_by_default(
    bgp,
):
    """The captured 10.80 learned-info column list has no Extended
    Community column at all, so real-world rows must come back with an
    empty list rather than a missing key or a spurious warning.
    """
    row = {
        "IPv4 Prefix": "100.1.0.0",
        "Prefix Length": "24",
        "AS Path": "<100 200>",
        "Community": "1 : 2",
    }
    prefix = bgp._row_to_ipv4_prefix(row)
    assert prefix["extended_communities"] == []


def test_row_to_ipv4_prefix_reads_extended_community_column_when_present(
    bgp,
):
    row = {
        "IPv4 Prefix": "100.1.0.0",
        "Prefix Length": "24",
        "AS Path": "<100 200>",
        "Community": "1 : 2",
        "Extended Community": "0002000000000064",
    }
    prefix = bgp._row_to_ipv4_prefix(row)
    assert prefix["extended_communities"] == [{"raw": "0002000000000064"}]
