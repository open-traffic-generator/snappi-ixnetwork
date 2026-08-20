"""
Unit tests for address-family selection in get_states(bgp_prefixes).

``StatesRequest.bgp_prefixes`` carries three independent filters:

  * ``prefix_filters``          -- which address families to report;
  * ``ipv4_unicast_filters``    -- which IPv4 prefixes, within that family;
  * ``ipv6_unicast_filters``    -- likewise for IPv6.

These tests cover the first one and how it composes with the other two, plus
the family-per-learned-table routing that makes it possible.  No chassis is
needed: the learned-info tables are faked at the RestPy boundary.
"""

import logging
import re

import pytest
import snappi

from snappi_ixnetwork.device.bgp import Bgp
from snappi_ixnetwork.device.ngpf import Ngpf

try:  # pragma: no cover - import shape differs across Python versions
    from unittest.mock import MagicMock
except ImportError:  # pragma: no cover
    from mock import MagicMock


# ---------------------------------------------------------------------------
# Fake learned-info tables
# ---------------------------------------------------------------------------

V4_COLUMNS = [
    "IPv4 Prefix ",
    "Prefix Length",
    "Path ID",
    "IPv4 Next Hop",
    "IPv6 Next Hop",
    "MED",
    "Local Preference",
    "Origin",
    "AS Path",
    "Community",
]

V6_COLUMNS = [
    "IPv6 Prefix",
    "Prefix Length",
    "Path ID",
    "IPv4 Next Hop",
    "IPv6 Next Hop",
    "MED",
    "Local Preference",
    "Origin",
    "AS Path",
    "Community",
]


def v4_values(address="100.1.0.0"):
    return [
        address,
        "24",
        "NA",
        "10.1.1.1",
        "removePacket[ ]",
        "50",
        "0",
        "EGP",
        "<100 200>",
        "1 : 2",
    ]


def v6_values(address="4000::"):
    return [
        address,
        "64",
        "NA",
        "removePacket[ ]",
        "2001:db8::1",
        "60",
        "0",
        "IGP",
        "<500 600>",
        "3 : 4",
    ]


class FakeTable(object):
    def __init__(self, type_, columns, values):
        self.Type = type_
        self.Columns = columns
        self.Values = values


class _FindList(object):
    """Mimics a RestPy child accessor: ``.find()`` returns the items."""

    def __init__(self, items):
        self._items = items

    def find(self, **kwargs):
        return self._items


class _TableFindList(object):
    """``learnedInfo.Table`` accessor that honours ``find(Type=<regex>)``.

    RestPy evaluates ``find()``'s named parameters as regular expressions on
    the API server; this reproduces that so the server-side narrowing is
    actually exercised rather than silently bypassed.  ``patterns`` records
    every Type regex requested, and ``raise_on_type`` simulates a server that
    rejects the filtered query.
    """

    def __init__(self, tables, raise_on_type=False):
        self._tables = tables
        self.patterns = []
        self.unfiltered_calls = 0
        self.raise_on_type = raise_on_type

    def find(self, **kwargs):
        pattern = kwargs.get("Type")
        if pattern is None:
            self.unfiltered_calls += 1
            return list(self._tables)
        self.patterns.append(pattern)
        if self.raise_on_type:
            raise Exception("server rejected Type filter")
        return [
            t
            for t in self._tables
            if t.Type is not None and re.match(pattern, t.Type)
        ]


class FakeLearnedInfo(object):
    def __init__(self, tables, raise_on_type=False):
        self.Table = _TableFindList(tables, raise_on_type=raise_on_type)


class FakePeer(object):
    """A RestPy peer object exposing pre-baked learned-info tables."""

    def __init__(self, name, tables, raise_on_type=False):
        self.Name = name
        self._learned_info = FakeLearnedInfo(
            tables, raise_on_type=raise_on_type
        )
        self.LearnedInfo = _FindList([self._learned_info])
        self.get_all_learned_info_calls = 0

    @property
    def table_finder(self):
        return self._learned_info.Table

    def GetAllLearnedInfo(self):
        self.get_all_learned_info_calls += 1


def v4_table(addresses=("100.1.0.0",), type_="IPv4 Prefixes 1"):
    return FakeTable(
        type_, list(V4_COLUMNS), [v4_values(a) for a in addresses]
    )


def v6_table(addresses=("4000::",), type_="IPv6 Prefixes 1"):
    return FakeTable(
        type_, list(V6_COLUMNS), [v6_values(a) for a in addresses]
    )


@pytest.fixture
def bgp():
    return Bgp(MagicMock())


# ---------------------------------------------------------------------------
# resolve_prefix_filters  (R3-a, R3-c)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty", [None, []])
def test_empty_prefix_filters_means_all_supported_families(bgp, empty):
    assert bgp.resolve_prefix_filters(empty) == [
        "ipv4_unicast",
        "ipv6_unicast",
    ]


@pytest.mark.parametrize(
    "requested, expected",
    [
        (["ipv4_unicast"], ["ipv4_unicast"]),
        (["ipv6_unicast"], ["ipv6_unicast"]),
        (["ipv4_unicast", "ipv6_unicast"], ["ipv4_unicast", "ipv6_unicast"]),
        # Order of the request must not change the order of the result.
        (["ipv6_unicast", "ipv4_unicast"], ["ipv4_unicast", "ipv6_unicast"]),
        # Duplicates collapse.
        (["ipv4_unicast", "ipv4_unicast"], ["ipv4_unicast"]),
    ],
)
def test_supported_prefix_filters(bgp, requested, expected):
    assert bgp.resolve_prefix_filters(requested) == expected


@pytest.mark.parametrize("family", ["ipv4_mpls_unicast", "ipv6_mpls_unicast"])
def test_mpls_families_raise_rather_than_return_empty(bgp, family):
    """An unsupported family must fail loudly.

    Returning an empty list would be indistinguishable from "this peer
    learned nothing", which is the worst possible answer to give a test
    that is asserting on learned routes.
    """
    with pytest.raises(Exception) as excinfo:
        bgp.resolve_prefix_filters([family])
    message = str(excinfo.value)
    assert family in message
    assert "not supported" in message


def test_unknown_prefix_filter_value_raises(bgp):
    with pytest.raises(Exception) as excinfo:
        bgp.resolve_prefix_filters(["ipv4_multicast"])
    assert "Unknown" in str(excinfo.value)


def test_mpls_mixed_with_supported_family_still_raises(bgp):
    """Partial success would silently drop the family the user asked for."""
    with pytest.raises(Exception):
        bgp.resolve_prefix_filters(["ipv4_unicast", "ipv4_mpls_unicast"])


def test_prefix_filter_values_cover_the_otg_enum(bgp):
    """The known-values map must track the OTG enum, or 'Unknown' lies."""
    enum = set(
        snappi.snappi.BgpPrefixStateRequest._TYPES["prefix_filters"]["enum"]
    )
    assert set(bgp._PREFIX_FILTER_FIELDS) == enum


# ---------------------------------------------------------------------------
# Table type -> family  (the R4-a piece R3-b needs)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "table_type, expected",
    [
        ("IPv4 Prefixes 1", "ipv4_unicast"),
        ("IPv6 Prefixes 1", "ipv6_unicast"),
        # The trailing ordinal is per-fetch and unstable, so any value of it
        # must map the same way.
        ("IPv4 Prefixes 2", "ipv4_unicast"),
        ("IPv6 Prefixes 17", "ipv6_unicast"),
        ("ipv4 prefixes", "ipv4_unicast"),
        # Other families must NOT be claimed as unicast.
        ("IPv4 MPLS Prefixes 1", None),
        ("IPv6 MPLS Prefixes 1", None),
        ("EVPN Learned Info", None),
        ("", None),
        (None, None),
    ],
)
def test_table_family(bgp, table_type, expected):
    assert bgp._table_family(table_type) == expected


def test_unrecognised_table_is_skipped_not_merged(bgp):
    """An MPLS table shares the IPv4 prefix column with the unicast table.

    Discriminating on table Type rather than on column presence is what
    stops those rows being reported as plain unicast prefixes.
    """
    mpls = FakeTable(
        "IPv4 MPLS Prefixes 1", list(V4_COLUMNS), [v4_values("9.9.9.0")]
    )
    peer = FakePeer("p", [v4_table(("100.1.0.0",)), mpls])

    tables = bgp._get_learned_table(peer)

    assert list(tables) == ["ipv4_unicast"]
    assert [r["IPv4 Prefix"] for r in tables["ipv4_unicast"]] == ["100.1.0.0"]


def test_learned_table_groups_by_family(bgp):
    peer = FakePeer("p", [v4_table(), v6_table()])
    tables = bgp._get_learned_table(peer)
    assert sorted(tables) == ["ipv4_unicast", "ipv6_unicast"]


def test_learned_table_merges_multiple_tables_of_one_family(bgp):
    peer = FakePeer(
        "p",
        [
            v4_table(("100.1.0.0",), type_="IPv4 Prefixes 1"),
            v4_table(("200.1.0.0",), type_="IPv4 Prefixes 2"),
        ],
    )
    tables = bgp._get_learned_table(peer)
    assert [r["IPv4 Prefix"] for r in tables["ipv4_unicast"]] == [
        "100.1.0.0",
        "200.1.0.0",
    ]


def test_learned_table_survives_a_failed_trigger(bgp):
    peer = FakePeer("p", [v4_table()])
    peer.GetAllLearnedInfo = MagicMock(side_effect=Exception("boom"))
    assert bgp._get_learned_table(peer) == {}


# ---------------------------------------------------------------------------
# Server-side table selection  (R4-d)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "families, expected_families",
    [
        (["ipv4_unicast"], ["ipv4_unicast"]),
        (["ipv6_unicast"], ["ipv6_unicast"]),
        (["ipv4_unicast", "ipv6_unicast"], ["ipv4_unicast", "ipv6_unicast"]),
    ],
)
def test_only_requested_families_are_fetched(bgp, families, expected_families):
    """The requested families are selected on the server, not locally."""
    peer = FakePeer("p", [v4_table(), v6_table()])

    tables = bgp._get_learned_table(peer, families)

    assert sorted(tables) == sorted(expected_families)
    # The narrowing really happened server-side: a Type regex was sent, and
    # no unfiltered read was needed.
    assert peer.table_finder.patterns, "no server-side Type filter was sent"
    assert peer.table_finder.unfiltered_calls == 0


def test_type_pattern_is_anchored_alternated_and_case_insensitive(bgp):
    assert bgp._table_type_pattern(["ipv4_unicast"]) == "(?i)^(IPv4 Prefixes)"
    assert bgp._table_type_pattern(None) == (
        "(?i)^(IPv4 Prefixes|IPv6 Prefixes)"
    )
    # A family with no table mapping cannot be narrowed server-side.
    assert bgp._table_type_pattern(["ipv4_mpls_unicast"]) is None


def test_type_pattern_matches_the_real_table_types(bgp):
    """Guards the regex against the captured 10.80 Type strings."""
    pattern = bgp._table_type_pattern(None)
    for table_type in ("IPv4 Prefixes 1", "IPv6 Prefixes 17"):
        assert re.match(pattern, table_type), table_type
    for table_type in ("IPv4 MPLS Prefixes 1", "EVPN Learned Info"):
        assert not re.match(pattern, table_type), table_type


def test_unfilterable_families_read_every_table(bgp):
    """With no server-side pattern available, fall back to reading all."""
    peer = FakePeer("p", [v4_table()])
    bgp._get_learned_table(peer, ["ipv4_mpls_unicast"])
    assert peer.table_finder.patterns == []
    assert peer.table_finder.unfiltered_calls == 1


def test_falls_back_to_unfiltered_read_when_type_filter_raises(bgp):
    """A server that rejects the filter must not cost us the data."""
    peer = FakePeer("p", [v4_table(), v6_table()], raise_on_type=True)

    tables = bgp._get_learned_table(peer, ["ipv4_unicast", "ipv6_unicast"])

    assert sorted(tables) == ["ipv4_unicast", "ipv6_unicast"]
    assert peer.table_finder.unfiltered_calls == 1


def test_renamed_table_type_is_reported_not_silently_empty(bgp, caplog):
    """Tables exist but none map to a family: the schema-drift signal.

    The filtered read comes back empty, the unfiltered re-read finds the
    table, and nothing can be made of it -- so the caller gets a warning
    naming the type rather than an empty result and no explanation.
    """
    renamed = FakeTable(
        "IPv4 Unicast Routes 1", list(V4_COLUMNS), [v4_values()]
    )
    peer = FakePeer("p", [renamed])

    with caplog.at_level(logging.WARNING):
        tables = bgp._get_learned_table(peer, ["ipv4_unicast"])

    assert tables == {}
    assert peer.table_finder.unfiltered_calls == 1
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "IPv4 Unicast Routes 1" in messages
    assert "unhandled type" in messages


def test_case_differing_table_type_is_still_matched(bgp, caplog):
    """The server pattern is case-insensitive, matching _table_family.

    The '(?i)' flag is verified to work on IxNetwork 10.80, so a type that
    differs only in casing is selected server-side with no re-read.
    """
    peer = FakePeer("p", [v4_table(type_="ipv4 prefixes 1")])

    with caplog.at_level(logging.WARNING):
        tables = bgp._get_learned_table(peer, ["ipv4_unicast"])

    assert list(tables) == ["ipv4_unicast"]
    assert peer.table_finder.unfiltered_calls == 0
    assert caplog.records == []


def test_requesting_a_family_the_peer_lacks_is_quiet(bgp, caplog):
    """The normal narrowed case: asking a v6 peer for IPv4.

    The filter correctly matches nothing, so there is nothing to report.  An
    earlier version warned here, which fired on every such request.
    """
    peer = FakePeer("p", [v6_table()])

    with caplog.at_level(logging.WARNING):
        tables = bgp._get_learned_table(peer, ["ipv4_unicast"])

    assert tables == {}
    assert caplog.records == [], "narrowing to an absent family must be quiet"


def test_fallback_that_recovers_data_warns(bgp, caplog):
    """If the server filter misbehaves, say so -- but keep the rows."""
    peer = FakePeer("p", [v4_table()], raise_on_type=True)

    with caplog.at_level(logging.WARNING):
        tables = bgp._get_learned_table(peer, ["ipv4_unicast"])

    assert list(tables) == ["ipv4_unicast"]
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "may not be behaving as expected" in messages


def test_no_tables_at_all_does_not_warn(bgp, caplog):
    """A peer that has simply learned nothing is not an anomaly."""
    peer = FakePeer("p", [])
    with caplog.at_level(logging.WARNING):
        assert bgp._get_learned_table(peer, ["ipv4_unicast"]) == {}
    assert caplog.records == []


def test_only_unrecognised_tables_warns(bgp, caplog):
    """Understood nothing we fetched -- the schema-drift signal."""
    peer = FakePeer(
        "p",
        [FakeTable("EVPN Learned Info", list(V4_COLUMNS), [v4_values()])],
    )
    with caplog.at_level(logging.WARNING):
        assert bgp._get_learned_table(peer, None) == {}
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "unhandled type" in messages
    assert "EVPN Learned Info" in messages


def test_recognised_plus_unrecognised_does_not_warn(bgp, caplog):
    """A peer carrying other families as well is normal, not a problem."""
    peer = FakePeer(
        "p",
        [
            v4_table(),
            FakeTable("EVPN Learned Info", list(V4_COLUMNS), [v4_values()]),
        ],
    )
    with caplog.at_level(logging.WARNING):
        tables = bgp._get_learned_table(peer, None)
    assert list(tables) == ["ipv4_unicast"]
    assert caplog.records == []


# ---------------------------------------------------------------------------
# get_learned_prefixes: family routing  (R3-b)
# ---------------------------------------------------------------------------


def test_returns_each_family_under_its_own_field(bgp):
    peer = FakePeer("p", [v4_table(), v6_table()])
    result = bgp.get_learned_prefixes(peer, None)
    assert sorted(result) == [
        "ipv4_unicast_prefixes",
        "ipv6_unicast_prefixes",
    ]
    assert result["ipv4_unicast_prefixes"][0]["ipv4_address"] == "100.1.0.0"
    assert result["ipv6_unicast_prefixes"][0]["ipv6_address"] == "4000::"


def test_families_argument_restricts_the_result(bgp):
    peer = FakePeer("p", [v4_table(), v6_table()])
    result = bgp.get_learned_prefixes(peer, None, ["ipv6_unicast"])
    assert list(result) == ["ipv6_unicast_prefixes"]


def test_family_comes_from_the_table_not_the_peer(bgp):
    """An MP-BGP session over IPv4 that has learned IPv6 NLRI.

    The peer object is a bgpIpv4Peer, but the learned table is IPv6, so the
    prefixes must be reported as ipv6_unicast_prefixes.  Deriving the family
    from the peer's own IP version -- as the first implementation did --
    dropped these entirely.
    """
    peer = FakePeer("bgpv4_peer1", [v6_table()])
    result = bgp.get_learned_prefixes(peer, None)
    assert list(result) == ["ipv6_unicast_prefixes"]


def test_absent_family_is_omitted_rather_than_empty(bgp):
    """A v4-only peer must not claim an empty IPv6 result."""
    peer = FakePeer("p", [v4_table()])
    result = bgp.get_learned_prefixes(peer, None)
    assert list(result) == ["ipv4_unicast_prefixes"]


def test_family_present_but_filtered_to_nothing_is_an_empty_list(bgp):
    """Distinguishes "nothing matched the filter" from "not carried"."""
    request = snappi.StatesRequest().bgp_prefixes
    filt = request.ipv4_unicast_filters.add()
    filt.addresses = ["203.0.113.0"]

    peer = FakePeer("p", [v4_table()])
    result = bgp.get_learned_prefixes(peer, request)
    assert result["ipv4_unicast_prefixes"] == []


def test_per_family_filters_apply_to_their_own_family(bgp):
    """An IPv4 filter must not narrow the IPv6 result, or vice versa."""
    request = snappi.StatesRequest().bgp_prefixes
    filt = request.ipv4_unicast_filters.add()
    filt.addresses = ["100.1.1.0"]

    peer = FakePeer(
        "p",
        [
            v4_table(("100.1.0.0", "100.1.1.0")),
            v6_table(("4000::", "5000::")),
        ],
    )
    result = bgp.get_learned_prefixes(peer, request)

    assert [p["ipv4_address"] for p in result["ipv4_unicast_prefixes"]] == [
        "100.1.1.0"
    ]
    assert [p["ipv6_address"] for p in result["ipv6_unicast_prefixes"]] == [
        "4000::",
        "5000::",
    ]


# ---------------------------------------------------------------------------
# Ngpf.get_bgp_prefix_states: end-to-end wiring  
# ---------------------------------------------------------------------------


class FakeNgpf(object):
    """Just enough of Ngpf to drive get_bgp_prefix_states.

    The method only touches ``self._bgp`` and ``self.logger``, so this avoids
    building a whole Ngpf (and its api/session) for an offline test.
    """

    def __init__(self, bgp, peer_entries):
        self._bgp = bgp
        self.logger = logging.getLogger(__name__)
        bgp.get_bgp_peer_objects = MagicMock(return_value=peer_entries)

    def run(self, request):
        return Ngpf.get_bgp_prefix_states(self, request)


def make_request(peer_names=None, prefix_filters=None):
    request = snappi.StatesRequest()
    request.choice = "bgp_prefixes"
    if peer_names is not None:
        request.bgp_prefixes.bgp_peer_names = peer_names
    if prefix_filters is not None:
        request.bgp_prefixes.prefix_filters = prefix_filters
    return request


def test_response_shape_and_choice(bgp):
    peer = FakePeer("peer1", [v4_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    response = ngpf.run(make_request())

    assert response["choice"] == "bgp_prefixes"
    assert len(response["bgp_prefixes"]) == 1
    assert response["bgp_prefixes"][0]["bgp_peer_name"] == "peer1"


def test_prefix_filters_select_the_reported_family(bgp):
    peer = FakePeer("peer1", [v4_table(), v6_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    entry = ngpf.run(make_request(prefix_filters=["ipv4_unicast"]))[
        "bgp_prefixes"
    ][0]
    assert "ipv4_unicast_prefixes" in entry
    assert "ipv6_unicast_prefixes" not in entry

    entry = ngpf.run(make_request(prefix_filters=["ipv6_unicast"]))[
        "bgp_prefixes"
    ][0]
    assert "ipv6_unicast_prefixes" in entry
    assert "ipv4_unicast_prefixes" not in entry


def test_no_prefix_filters_reports_every_family(bgp):
    peer = FakePeer("peer1", [v4_table(), v6_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    entry = ngpf.run(make_request())["bgp_prefixes"][0]
    assert "ipv4_unicast_prefixes" in entry
    assert "ipv6_unicast_prefixes" in entry


def test_dual_stack_peer_yields_one_entry_not_two(bgp):
    """R3-d: one BgpPrefixesState per peer, however many families."""
    peer = FakePeer("peer1", [v4_table(), v6_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    entries = ngpf.run(make_request())["bgp_prefixes"]

    assert len(entries) == 1
    names = [e["bgp_peer_name"] for e in entries]
    assert len(names) == len(set(names)), "duplicate bgp_peer_name entries"


def test_repeated_peer_name_is_merged_into_one_entry(bgp):
    """Defensive: two walk results for one name must not split the entry."""
    peer_a = FakePeer("peer1", [v4_table(("100.1.0.0",))])
    peer_b = FakePeer("peer1", [v6_table(("4000::",))])
    ngpf = FakeNgpf(
        bgp, [("peer1", peer_a, 1, "v4"), ("peer1", peer_b, 1, "v6")]
    )

    entries = ngpf.run(make_request())["bgp_prefixes"]

    assert len(entries) == 1
    assert len(entries[0]["ipv4_unicast_prefixes"]) == 1
    assert len(entries[0]["ipv6_unicast_prefixes"]) == 1


def test_separate_peers_keep_separate_entries(bgp):
    ngpf = FakeNgpf(
        bgp,
        [
            ("peer1", FakePeer("peer1", [v4_table()]), 1, "v4"),
            ("peer2", FakePeer("peer2", [v4_table(("200.1.0.0",))]), 1, "v4"),
        ],
    )
    entries = ngpf.run(make_request())["bgp_prefixes"]
    assert [e["bgp_peer_name"] for e in entries] == ["peer1", "peer2"]


def test_mpls_prefix_filter_raises_through_get_states(bgp):
    peer = FakePeer("peer1", [v4_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    with pytest.raises(Exception) as excinfo:
        ngpf.run(make_request(prefix_filters=["ipv4_mpls_unicast"]))
    assert "not supported" in str(excinfo.value)


def test_unsupported_family_is_rejected_before_querying_hardware(bgp):
    """The error must not cost a learned-info fetch on every peer."""
    peer = FakePeer("peer1", [v4_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    with pytest.raises(Exception):
        ngpf.run(make_request(prefix_filters=["ipv6_mpls_unicast"]))
    assert peer.get_all_learned_info_calls == 0


def test_response_deserializes_into_the_otg_model(bgp):
    """The dict handed back must survive StatesResponse.deserialize()."""
    peer = FakePeer("peer1", [v4_table(), v6_table()])
    ngpf = FakeNgpf(bgp, [("peer1", peer, 1, "v4")])

    response = snappi.StatesResponse()
    response.deserialize(ngpf.run(make_request()))
    response.serialize()

    state = response.bgp_prefixes[0]
    assert state.bgp_peer_name == "peer1"
    assert state.ipv4_unicast_prefixes[0].ipv4_address == "100.1.0.0"
    assert state.ipv6_unicast_prefixes[0].ipv6_address == "4000::"
