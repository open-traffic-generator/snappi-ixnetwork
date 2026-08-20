"""
Unit tests for the get_states(bgp_prefixes) learned-info parsers.

"""
import logging

import pytest
import snappi

from snappi_ixnetwork.device.bgp import Bgp


try:  # pragma: no cover - import shape differs across Python versions
    from unittest.mock import MagicMock
except ImportError:  # pragma: no cover
    from mock import MagicMock


# ---------------------------------------------------------------------------
# Captured fixture data (IxNetwork 10.80.8001.21)
# ---------------------------------------------------------------------------

CAPTURED_V4_COLUMNS = [
    "IPv4 Prefix ",  # trailing space is intentional - real IxNetwork output
    "Prefix Length",
    "Path ID",
    "IPv4 Next Hop",
    "IPv6 Next Hop",
    "IPv6 Next Hop 2",
    "MED",
    "Local Preference",
    "Origin",
    "AS Path",
    "Community",
    "AIGP",
    "Color",
    "Large Community",
    "SRv6 SID",
    "Locator Block Length",
    "Locator Node Length",
    "Function Length",
    "Argument Length",
]

CAPTURED_V4_ROW = [
    "100.1.0.0",
    "24",
    "NA",
    "10.1.1.1",
    "removePacket[ ]",
    "removePacket[ ]",
    "50",
    "0",
    "EGP",
    "<100 200>",
    "1 : 2",
    "",
    "",
    "NA",
    "NA",
    "NA",
    "NA",
    "NA",
    "NA",
]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def bgp():
    """A Bgp instance with a stubbed ngpf -- the parsers never touch it."""
    return Bgp(MagicMock())


def make_row(columns, values):
    """Build a row dict the way _get_learned_table does (stripped keys)."""
    return {
        col.strip(): values[i]
        for i, col in enumerate(columns)
        if i < len(values)
    }


@pytest.fixture
def captured_v4_row():
    return make_row(CAPTURED_V4_COLUMNS, CAPTURED_V4_ROW)


def v4_row(**overrides):
    """A minimal-but-complete IPv4 row, with per-test column overrides.

    Passing ``None`` as a value removes the column entirely, which is how
    "IxNetwork stopped emitting this column" is simulated.
    """
    row = {
        "IPv4 Prefix": "100.1.0.0",
        "Prefix Length": "24",
        "Path ID": "NA",
        "IPv4 Next Hop": "10.1.1.1",
        "IPv6 Next Hop": "removePacket[ ]",
        "MED": "50",
        "Local Preference": "0",
        "Origin": "EGP",
        "AS Path": "<100 200>",
        "Community": "1 : 2",
    }
    for key, value in overrides.items():
        if value is None:
            row.pop(key, None)
        else:
            row[key] = value
    return row


def v6_row(**overrides):
    """A minimal-but-complete IPv6 row (column names UNCONFIRMED)."""
    row = {
        "IPv6 Prefix": "4000::",
        "Prefix Length": "64",
        "Path ID": "NA",
        "IPv6 Next Hop": "2000::1",
        "IPv4 Next Hop": "removePacket[ ]",
        "MED": "60",
        "Local Preference": "100",
        "Origin": "IGP",
        "AS Path": "<500 600>",
        "Community": "3 : 4",
    }
    for key, value in overrides.items():
        if value is None:
            row.pop(key, None)
        else:
            row[key] = value
    return row


def make_filter(family="ipv4", **kwargs):
    """Build a real snappi unicast filter so field names stay honest.

    A hand-rolled stub would keep passing if the OTG model renamed a
    filter field; the real object will not.
    """
    request = snappi.StatesRequest()
    filters = getattr(
        request.bgp_prefixes, "%s_unicast_filters" % family
    )
    filt = filters.add()
    for name, value in kwargs.items():
        setattr(filt, name, value)
    return filt


def segments(as_path):
    """Flatten a parsed as_path into ``[(type, [asn, ...]), ...]``."""
    return [(s["type"], s["as_numbers"]) for s in as_path["segments"]]


# ---------------------------------------------------------------------------
# _parse_as_path  
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cell, expected",
    [
        # The bracketed asplain form IxNetwork 10.80 actually emits.
        ("<100 200>", [("as_seq", [100, 200])]),
        # Unbracketed sequence (older/other IxNetwork output).
        ("100 200 300", [("as_seq", [100, 200, 300])]),
        # All four OTG segment types, one per bracket style.
        ("<100>", [("as_seq", [100])]),
        ("{100 200}", [("as_set", [100, 200])]),
        ("(100 200)", [("as_confed_seq", [100, 200])]),
        ("[100 200]", [("as_confed_set", [100, 200])]),
        # Mixed: a group followed by loose ASNs, and the reverse.  Segment
        # order must follow the string, not the parser's buffering.
        (
            "{100 200} 300",
            [("as_set", [100, 200]), ("as_seq", [300])],
        ),
        (
            "300 {100 200}",
            [("as_seq", [300]), ("as_set", [100, 200])],
        ),
        (
            "(100 200) [300]",
            [("as_confed_seq", [100, 200]), ("as_confed_set", [300])],
        ),
        (
            "100 {200} 300",
            [
                ("as_seq", [100]),
                ("as_set", [200]),
                ("as_seq", [300]),
            ],
        ),
        ("<100> <200>", [("as_seq", [100]), ("as_seq", [200])]),
        # 2-byte and 4-byte AS numbers (asplain), including the uint32 max.
        ("65535", [("as_seq", [65535])]),
        ("4200000000", [("as_seq", [4200000000])]),
        ("<4294967295>", [("as_seq", [4294967295])]),
        # Empty / sentinel cells yield no segments rather than a segment
        # with no members.
        ("", []),
        ("   ", []),
        ("N/A", []),
        ("n/a", []),
        ("0", []),
        # An unterminated group is recovered rather than dropped.
        ("<100 200", [("as_seq", [100, 200])]),
    ],
)
def test_parse_as_path(bgp, cell, expected):
    assert segments(bgp._parse_as_path(cell)) == expected


def test_parse_as_path_none_cell(bgp):
    """_get_cell returns None for an absent/placeholder column."""
    assert bgp._parse_as_path(None) == {"segments": []}


# The verbatim AS Path cell from an eBGP peer on 10.80 advertising three
# configured segments.  Two things this pins down, both found on hardware
# after the first version of these tests guessed wrong:
#   * AS_SET members are COMMA-separated ('{300,400}') while AS_SEQ members
#     are space-separated -- the separator differs by segment type;
#   * the advertising peer prepends its own AS (4200000001) as a separate
#     leading AS_SEQ segment over eBGP.
CAPTURED_EBGP_AS_PATH = "<4200000001> <100 200> {300,400} <4200000000>"


def test_parse_captured_ebgp_as_path(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        result = bgp._parse_as_path(CAPTURED_EBGP_AS_PATH)
    assert segments(result) == [
        ("as_seq", [4200000001]),
        ("as_seq", [100, 200]),
        ("as_set", [300, 400]),
        ("as_seq", [4200000000]),
    ]
    assert caplog.records == [], "real IxNetwork output must parse cleanly"


@pytest.mark.parametrize(
    "cell, expected",
    [
        # Comma-separated members, with and without spaces.  '{300,400}' is
        # the real 10.80 AS_SET rendering.
        ("{300,400}", [("as_set", [300, 400])]),
        ("{300, 400}", [("as_set", [300, 400])]),
        ("<100,200>", [("as_seq", [100, 200])]),
        ("(100,200)", [("as_confed_seq", [100, 200])]),
        ("[100,200]", [("as_confed_set", [100, 200])]),
        # Unbracketed, comma-separated.
        ("100,200", [("as_seq", [100, 200])]),
        # Trailing/repeated separators must not produce phantom entries.
        ("{300,400,}", [("as_set", [300, 400])]),
        ("{300,,400}", [("as_set", [300, 400])]),
    ],
)
def test_parse_as_path_comma_separated_members(bgp, caplog, cell, expected):
    with caplog.at_level(logging.WARNING):
        assert segments(bgp._parse_as_path(cell)) == expected
    assert caplog.records == []


def test_parse_as_path_empty_group_is_kept(bgp):
    """Documents current behaviour: '{}' yields an empty as_set segment.

    Harmless for consumers (the segment simply has no members) but recorded
    here so a future change to drop empty segments is a deliberate one.
    """
    assert segments(bgp._parse_as_path("{}")) == [("as_set", [])]


@pytest.mark.parametrize(
    "cell, kept",
    [
        # asdot is deliberately NOT converted: IxNetwork has only ever been
        # observed emitting asplain, and ixnetwork_restpy exposes no asdot
        # setting.  The token must be dropped *loudly*.
        ("<1.10 200>", [200]),
        # Out-of-range for uint32.
        ("<4294967296>", []),
        # Non-numeric junk.  (A comma-separated list is NOT junk -- see
        # test_parse_as_path_comma_separated_members.)
        ("<abc 200>", [200]),
        ("<100;200>", []),
    ],
)
def test_parse_as_path_bad_tokens_warn_not_silent(bgp, caplog, cell, kept):
    """A token that cannot be parsed must produce a warning, never silence.

    Silently dropping an ASN turns a format surprise into a wrong AS path,
    and AS-path assertions are the main reason these states exist.
    """
    with caplog.at_level(logging.WARNING):
        result = bgp._parse_as_path(cell)
    assert segments(result)[0][1] == kept
    assert caplog.records, "unparseable AS token was dropped silently"


def test_parse_as_path_asdot_warning_names_the_conversion(bgp, caplog):
    """The asdot warning must tell the reader how to implement it."""
    with caplog.at_level(logging.WARNING):
        bgp._parse_as_path("<1.10>")
    message = " ".join(r.getMessage() for r in caplog.records)
    assert "asdot" in message
    assert "65536" in message


def test_parse_as_path_valid_asns_never_warn(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        bgp._parse_as_path("{100 200} 300 <4294967295>")
    assert caplog.records == []


# ---------------------------------------------------------------------------
# _parse_communities  
# ---------------------------------------------------------------------------


def manual(as_number, as_custom):
    return {
        "type": "manual_as_number",
        "as_number": as_number,
        "as_custom": as_custom,
    }


@pytest.mark.parametrize(
    "cell, expected",
    [
        # The spaced form IxNetwork 10.80 actually emits.
        ("1 : 2", [manual(1, 2)]),
        ("1:2", [manual(1, 2)]),
        ("1:2 3:4", [manual(1, 2), manual(3, 4)]),
        ("1 : 2 3 : 4", [manual(1, 2), manual(3, 4)]),
        # Boundary values: both fields are capped at 65535 by OTG.
        ("0:0", [manual(0, 0)]),
        ("65535:65535", [manual(65535, 65535)]),
        # Every well-known type in the OTG enum, in the spellings the
        # parser accepts, plus a case-insensitivity check.
        ("no-export", [{"type": "no_export"}]),
        ("noexport", [{"type": "no_export"}]),
        ("NO-EXPORT", [{"type": "no_export"}]),
        ("no-advertise", [{"type": "no_advertised"}]),
        ("noadvertise", [{"type": "no_advertised"}]),
        ("no-advertised", [{"type": "no_advertised"}]),
        ("no_export_subconfed", [{"type": "no_export_subconfed"}]),
        ("no-export-subconfed", [{"type": "no_export_subconfed"}]),
        ("llgr_stale", [{"type": "llgr_stale"}]),
        ("no_llgr", [{"type": "no_llgr"}]),
        # Mixed well-known and numeric in one cell.
        (
            "1:2 no-export",
            [manual(1, 2), {"type": "no_export"}],
        ),
        # Empty / sentinel cells.
        ("", []),
        ("N/A", []),
        ("n/a", []),
    ],
)
def test_parse_communities(bgp, cell, expected):
    assert bgp._parse_communities(cell) == expected


def test_parse_communities_none_cell(bgp):
    assert bgp._parse_communities(None) == []


# The verbatim Community cell from the same eBGP capture.  Pins down that
# the list is COMMA-separated and that well-known names come back uppercase
# with underscores ('NO_EXPORT'), neither of which the first version of the
# parser handled.
CAPTURED_EBGP_COMMUNITY = "1 : 2, NO_EXPORT, 65535 : 65535"


def test_parse_captured_ebgp_communities(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        result = bgp._parse_communities(CAPTURED_EBGP_COMMUNITY)
    assert result == [
        manual(1, 2),
        {"type": "no_export"},
        manual(65535, 65535),
    ]
    assert caplog.records == [], "real IxNetwork output must parse cleanly"


@pytest.mark.parametrize(
    "cell, expected",
    [
        # Comma-separated, the real 10.80 rendering.
        ("1:2,3:4", [manual(1, 2), manual(3, 4)]),
        ("1:2, 3:4", [manual(1, 2), manual(3, 4)]),
        ("1 : 2, 3 : 4", [manual(1, 2), manual(3, 4)]),
        # Trailing/repeated separators must not produce phantom entries.
        ("1:2,", [manual(1, 2)]),
        ("1:2,,3:4", [manual(1, 2), manual(3, 4)]),
        # Uppercase / underscore spellings, as emitted on 10.80.
        ("NO_EXPORT", [{"type": "no_export"}]),
        ("NO_ADVERTISED", [{"type": "no_advertised"}]),
        ("NO_EXPORT_SUBCONFED", [{"type": "no_export_subconfed"}]),
        ("LLGR_STALE", [{"type": "llgr_stale"}]),
        ("NO_LLGR", [{"type": "no_llgr"}]),
        # Mixed comma-separated well-known and manual entries.
        (
            "NO_EXPORT, 1 : 2",
            [{"type": "no_export"}, manual(1, 2)],
        ),
    ],
)
def test_parse_communities_comma_separated(bgp, caplog, cell, expected):
    with caplog.at_level(logging.WARNING):
        assert bgp._parse_communities(cell) == expected
    assert caplog.records == []


def test_parse_communities_covers_every_otg_type(bgp):
    """Guard against the OTG enum growing past what the parser handles."""
    produced = set()
    for cell in (
        "1:2",
        "no-export",
        "no-advertise",
        "no_export_subconfed",
        "llgr_stale",
        "no_llgr",
    ):
        produced.update(c["type"] for c in bgp._parse_communities(cell))
    expected = set(
        snappi.snappi.ResultBgpCommunity._TYPES["type"]["enum"]
    )
    assert produced == expected


@pytest.mark.parametrize(
    "cell",
    [
        # Large community 'X:Y:Z' -- int('Y:Z') fails.
        "1:2:3",
        # Not a pair and not a well-known name.
        "garbage",
        # Out of range: emitting these would raise at snappi serialisation
        # time and fail the entire get_states call.
        "65536:1",
        "1:65536",
    ],
)
def test_parse_communities_bad_tokens_warn_and_skip(bgp, caplog, cell):
    with caplog.at_level(logging.WARNING):
        assert bgp._parse_communities(cell) == []
    assert caplog.records, "unparseable community was dropped silently"


def test_parse_communities_bad_token_does_not_lose_good_ones(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        result = bgp._parse_communities("1:2 garbage 3:4")
    assert result == [manual(1, 2), manual(3, 4)]
    assert caplog.records


def test_parse_communities_valid_never_warn(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        bgp._parse_communities("1 : 2 no-export 65535:65535")
    assert caplog.records == []


# ---------------------------------------------------------------------------
# _row_to_ipv4_prefix / _row_to_ipv6_prefix
# ---------------------------------------------------------------------------


def test_captured_row_maps_completely(bgp, captured_v4_row, caplog):
    """The real 10.80 row must translate with no warnings at all."""
    with caplog.at_level(logging.WARNING):
        prefix = bgp._row_to_ipv4_prefix(captured_v4_row)

    assert prefix == {
        "ipv4_address": "100.1.0.0",
        "prefix_length": 24,
        "ipv4_next_hop": "10.1.1.1",
        "origin": "egp",
        "local_preference": 0,
        "multi_exit_discriminator": 50,
        "as_path": {
            "segments": [{"type": "as_seq", "as_numbers": [100, 200]}]
        },
        "communities": [manual(1, 2)],
    }
    # 'NA' Path ID must not become path_id=0, and the
    # 'removePacket[ ]' IPv6 next hop must not be emitted as an address.
    assert "path_id" not in prefix
    assert "ipv6_next_hop" not in prefix
    assert caplog.records == [], "captured row should need no warnings"


def test_captured_ebgp_row_maps_completely(bgp, caplog):
    """The verbatim eBGP row: comma separators, NO_EXPORT, title-case origin.

    Every value here is exactly what IxNetwork 10.80 returned; this is the
    row that broke the first version of the parsers.
    """
    row = v4_row(
        **{
            "AS Path": CAPTURED_EBGP_AS_PATH,
            "Community": CAPTURED_EBGP_COMMUNITY,
            "Origin": "Incomplete",
            "MED": "70",
            "Local Preference": "removePacket[N/A]",
        }
    )
    with caplog.at_level(logging.WARNING):
        prefix = bgp._row_to_ipv4_prefix(row)

    assert prefix["origin"] == "incomplete"
    assert prefix["multi_exit_discriminator"] == 70
    # eBGP does not propagate LOCAL_PREF, so the cell is a placeholder.
    assert "local_preference" not in prefix
    assert [
        (s["type"], s["as_numbers"]) for s in prefix["as_path"]["segments"]
    ] == [
        ("as_seq", [4200000001]),
        ("as_seq", [100, 200]),
        ("as_set", [300, 400]),
        ("as_seq", [4200000000]),
    ]
    assert prefix["communities"] == [
        manual(1, 2),
        {"type": "no_export"},
        manual(65535, 65535),
    ]
    assert caplog.records == [], "real IxNetwork row must parse cleanly"


def test_captured_row_v6_handler_returns_none(bgp, captured_v4_row, caplog):
    """A v4 row offered to the v6 handler is skipped, quietly.

    Until the learned table is selected by ``table.Type``, both handlers see
    every row, so a cross-family miss is expected and must not warn.
    """
    with caplog.at_level(logging.WARNING):
        assert bgp._row_to_ipv6_prefix(captured_v4_row) is None
    assert caplog.records == []


def test_v6_row_maps_completely(bgp, caplog):
    with caplog.at_level(logging.WARNING):
        prefix = bgp._row_to_ipv6_prefix(v6_row())

    assert prefix == {
        "ipv6_address": "4000::",
        "prefix_length": 64,
        "ipv6_next_hop": "2000::1",
        "origin": "igp",
        "local_preference": 100,
        "multi_exit_discriminator": 60,
        "as_path": {
            "segments": [{"type": "as_seq", "as_numbers": [500, 600]}]
        },
        "communities": [manual(3, 4)],
    }
    assert "ipv4_next_hop" not in prefix
    assert caplog.records == []


@pytest.mark.parametrize(
    "address, length_cell, expected_addr, expected_len",
    [
        # Bare address plus a separate Prefix Length column (10.80).
        ("100.1.0.0", "24", "100.1.0.0", 24),
        # Full CIDR in the address column (other IxNetwork versions).
        ("100.1.0.0/24", "24", "100.1.0.0", 24),
        # CIDR wins over the separate column when they disagree.
        ("100.1.0.0/25", "24", "100.1.0.0", 25),
        # Unparseable length degrades to 0 rather than raising.
        ("100.1.0.0", "junk", "100.1.0.0", 0),
    ],
)
def test_v4_address_and_prefix_length(
    bgp, address, length_cell, expected_addr, expected_len
):
    prefix = bgp._row_to_ipv4_prefix(
        v4_row(**{"IPv4 Prefix": address, "Prefix Length": length_cell})
    )
    assert prefix["ipv4_address"] == expected_addr
    assert prefix["prefix_length"] == expected_len


def test_v6_cidr_in_address_column(bgp):
    prefix = bgp._row_to_ipv6_prefix(
        v6_row(**{"IPv6 Prefix": "4000::/64"})
    )
    assert prefix["ipv6_address"] == "4000::"
    assert prefix["prefix_length"] == 64


def test_v6_link_local_second_next_hop_is_not_mapped(bgp):
    """'IPv6 Next Hop 2' carries the link-local address on real hardware.

    It is genuine data, not a placeholder, but OTG has no field for a second
    next hop -- so it must not leak into ipv6_next_hop.
    """
    prefix = bgp._row_to_ipv6_prefix(
        v6_row(
            **{
                "IPv6 Next Hop": "2001:db8::1",
                "IPv6 Next Hop 2": "fe80::200:ff:fe00:11",
            }
        )
    )
    assert prefix["ipv6_next_hop"] == "2001:db8::1"


def test_whitespace_only_community_is_empty(bgp, caplog):
    """An empty Community column arrives as a single space on 10.80."""
    with caplog.at_level(logging.WARNING):
        prefix = bgp._row_to_ipv6_prefix(v6_row(**{"Community": " "}))
    assert prefix["communities"] == []
    assert caplog.records == []


def test_missing_address_column_returns_none(bgp):
    assert bgp._row_to_ipv4_prefix(v4_row(**{"IPv4 Prefix": None})) is None
    assert bgp._row_to_ipv6_prefix(v6_row(**{"IPv6 Prefix": None})) is None


@pytest.mark.parametrize(
    "placeholder",
    [
        "NA",
        "N/A",
        "",
        "removePacket[ ]",
        # Seen on 'Local Preference' for an eBGP peer, where LOCAL_PREF is
        # not propagated: the bracketed part varies, hence prefix matching.
        "removePacket[N/A]",
        "removePacket[]",
    ],
)
def test_placeholder_optional_fields_are_omitted(bgp, placeholder):
    """A placeholder must omit the field, not coerce it to 0."""
    prefix = bgp._row_to_ipv4_prefix(
        v4_row(
            **{
                "MED": placeholder,
                "Local Preference": placeholder,
                "Path ID": placeholder,
                "Origin": placeholder,
            }
        )
    )
    assert "multi_exit_discriminator" not in prefix
    assert "local_preference" not in prefix
    assert "path_id" not in prefix
    assert "origin" not in prefix


def test_zero_valued_fields_are_kept(bgp):
    """0 is data, not absence -- local_preference 0 is in the real capture.

    path_id is the documented exception: '0' means "no add-path ID".
    """
    prefix = bgp._row_to_ipv4_prefix(
        v4_row(**{"Local Preference": "0", "MED": "0", "Path ID": "0"})
    )
    assert prefix["local_preference"] == 0
    assert prefix["multi_exit_discriminator"] == 0
    assert "path_id" not in prefix


def test_path_id_present_when_set(bgp):
    prefix = bgp._row_to_ipv4_prefix(v4_row(**{"Path ID": "7"}))
    assert prefix["path_id"] == 7


@pytest.mark.parametrize(
    "origin_cell, expected",
    [
        ("EGP", "egp"),
        ("IGP", "igp"),
        ("egp", "egp"),
        ("Igp", "igp"),
        ("INCOMPLETE", "incomplete"),
    ],
)
def test_origin_mapping(bgp, origin_cell, expected):
    prefix = bgp._row_to_ipv4_prefix(v4_row(**{"Origin": origin_cell}))
    assert prefix["origin"] == expected


def test_unmapped_origin_is_omitted(bgp):
    prefix = bgp._row_to_ipv4_prefix(v4_row(**{"Origin": "wat"}))
    assert "origin" not in prefix


# --- next-hop selection ----------------------------------------------------


def test_next_hop_prefers_explicit_family_columns(bgp):
    ipv4_nh, ipv6_nh = bgp._get_next_hops(
        v4_row(**{"IPv4 Next Hop": "10.0.0.1", "IPv6 Next Hop": "2000::1"})
    )
    assert (ipv4_nh, ipv6_nh) == ("10.0.0.1", "2000::1")


def test_next_hop_placeholders_yield_none_without_warning(bgp, caplog):
    """Columns present but empty is a normal row, not a schema change."""
    with caplog.at_level(logging.WARNING):
        nh = bgp._get_next_hops(
            v4_row(
                **{"IPv4 Next Hop": "NA", "IPv6 Next Hop": "removePacket[ ]"}
            )
        )
    assert nh == (None, None)
    assert caplog.records == []


@pytest.mark.parametrize(
    "value, expected",
    [("10.0.0.9", ("10.0.0.9", None)), ("2000::1", (None, "2000::1"))],
)
def test_next_hop_legacy_single_column_fallback(bgp, value, expected):
    """The legacy 'Next Hop' column infers family from ':'."""
    row = v4_row(
        **{"IPv4 Next Hop": None, "IPv6 Next Hop": None, "Next Hop": value}
    )
    assert bgp._get_next_hops(row) == expected


def test_missing_all_next_hop_columns_warns_once(bgp, caplog):
    row = v4_row(**{"IPv4 Next Hop": None, "IPv6 Next Hop": None})
    with caplog.at_level(logging.WARNING):
        assert bgp._get_next_hops(row) == (None, None)
        bgp._get_next_hops(row)
        bgp._get_next_hops(row)
    assert len(caplog.records) == 1, "warning should be deduplicated"
    assert "Next Hop" in caplog.records[0].getMessage()


# --- schema-drift warnings -------------------------------------------------


@pytest.mark.parametrize(
    "column", ["Prefix Length", "Origin", "AS Path", "Community", "MED"]
)
def test_renamed_column_warns(bgp, caplog, column):
    """A vanished column must surface in the log, not silently drop data."""
    with caplog.at_level(logging.WARNING):
        bgp._row_to_ipv4_prefix(v4_row(**{column: None}))
    assert any(
        column in r.getMessage() for r in caplog.records
    ), "no warning mentioning the missing %r column" % column


def test_column_warning_is_deduplicated_across_rows(bgp, caplog):
    rows = [v4_row(**{"MED": None}) for _ in range(5)]
    bgp._warned_columns = set()
    with caplog.at_level(logging.WARNING):
        for row in rows:
            bgp._row_to_ipv4_prefix(row)
    med_warnings = [
        r for r in caplog.records if "MED" in r.getMessage()
    ]
    assert len(med_warnings) == 1, "one warning per column, not per row"


def test_trailing_space_in_column_name_is_tolerated(bgp):
    """'IPv4 Prefix ' (with the real trailing space) must still match."""
    row = make_row(["IPv4 Prefix ", "Prefix Length"], ["1.1.1.0", "24"])
    assert bgp._row_to_ipv4_prefix(row)["ipv4_address"] == "1.1.1.0"


# ---------------------------------------------------------------------------
# Filters: _prefix_matches_filter / _apply_v4_filters / _apply_v6_filters
# ---------------------------------------------------------------------------


@pytest.fixture
def v4_prefixes(bgp):
    return [
        bgp._row_to_ipv4_prefix(
            v4_row(
                **{
                    "IPv4 Prefix": "100.1.%d.0" % n,
                    "Path ID": str(n) if n else "NA",
                }
            )
        )
        for n in range(3)
    ]


def addresses_of(prefixes):
    return [p["ipv4_address"] for p in prefixes]


def test_no_filters_returns_everything(bgp, v4_prefixes):
    assert bgp._apply_v4_filters(v4_prefixes, None) == v4_prefixes
    assert bgp._apply_v4_filters(v4_prefixes, []) == v4_prefixes


def test_filter_by_address(bgp, v4_prefixes):
    filt = make_filter(addresses=["100.1.1.0"])
    result = bgp._apply_v4_filters(v4_prefixes, [filt])
    assert addresses_of(result) == ["100.1.1.0"]


def test_filter_by_multiple_addresses(bgp, v4_prefixes):
    filt = make_filter(addresses=["100.1.0.0", "100.1.2.0"])
    result = bgp._apply_v4_filters(v4_prefixes, [filt])
    assert addresses_of(result) == ["100.1.0.0", "100.1.2.0"]


def test_filter_fields_are_anded(bgp, v4_prefixes):
    """Within one filter every set field must match."""
    matching = make_filter(addresses=["100.1.1.0"], prefix_length=24)
    assert len(bgp._apply_v4_filters(v4_prefixes, [matching])) == 1

    conflicting = make_filter(addresses=["100.1.1.0"], prefix_length=25)
    assert bgp._apply_v4_filters(v4_prefixes, [conflicting]) == []


def test_multiple_filters_are_ored(bgp, v4_prefixes):
    filters = [
        make_filter(addresses=["100.1.0.0"]),
        make_filter(addresses=["100.1.2.0"]),
    ]
    result = bgp._apply_v4_filters(v4_prefixes, filters)
    assert addresses_of(result) == ["100.1.0.0", "100.1.2.0"]


def test_unset_filter_fields_are_wildcards(bgp, v4_prefixes):
    assert bgp._apply_v4_filters(v4_prefixes, [make_filter()]) == v4_prefixes


def test_filter_by_origin(bgp, v4_prefixes):
    matching = bgp._apply_v4_filters(
        v4_prefixes, [make_filter(origin="egp")]
    )
    assert len(matching) == 3
    assert bgp._apply_v4_filters(
        v4_prefixes, [make_filter(origin="igp")]
    ) == []


def test_filter_by_path_id(bgp, v4_prefixes):
    result = bgp._apply_v4_filters(v4_prefixes, [make_filter(path_id=2)])
    assert addresses_of(result) == ["100.1.2.0"]


def test_filter_path_id_zero_matches_absent_path_id(bgp, v4_prefixes):
    """A prefix with no path_id is treated as path_id 0.

    Documents the current default; the OTG spec is worth re-checking here
    (tracked as X5 in the review notes).
    """
    result = bgp._apply_v4_filters(v4_prefixes, [make_filter(path_id=0)])
    assert addresses_of(result) == ["100.1.0.0"]


def test_v6_filters_use_the_ipv6_address_key(bgp):
    prefixes = [
        bgp._row_to_ipv6_prefix(v6_row(**{"IPv6 Prefix": "4000::"})),
        bgp._row_to_ipv6_prefix(v6_row(**{"IPv6 Prefix": "5000::"})),
    ]
    filt = make_filter(family="ipv6", addresses=["5000::"])
    result = bgp._apply_v6_filters(prefixes, [filt])
    assert [p["ipv6_address"] for p in result] == ["5000::"]


# ---------------------------------------------------------------------------
# The parsers' output must survive the real OTG model
# ---------------------------------------------------------------------------


def test_parsed_prefixes_deserialize_into_states_response(bgp):
    """Mirror snappi_api.get_states: deserialize the dict we hand back.

    This is the check that catches a parser emitting a model-invalid value
    (an out-of-range community, say) -- which in the real API surfaces as
    an opaque TypeError from serialize(), not as a parsing error.
    """
    v4 = bgp._row_to_ipv4_prefix(v4_row(**{"Path ID": "7"}))
    v6 = bgp._row_to_ipv6_prefix(v6_row())
    response = snappi.StatesResponse()
    response.deserialize(
        {
            "choice": "bgp_prefixes",
            "bgp_prefixes": [
                {
                    "bgp_peer_name": "bgpv4_peer2",
                    "ipv4_unicast_prefixes": [v4],
                    "ipv6_unicast_prefixes": [v6],
                }
            ],
        }
    )
    # serialize() is where snappi enforces formats and ranges.
    response.serialize()

    state = response.bgp_prefixes[0]
    got_v4 = state.ipv4_unicast_prefixes[0]
    assert got_v4.ipv4_address == "100.1.0.0"
    assert got_v4.prefix_length == 24
    assert got_v4.origin == "egp"
    assert got_v4.multi_exit_discriminator == 50
    assert got_v4.path_id == 7
    assert got_v4.as_path.segments[0].type == "as_seq"
    assert got_v4.as_path.segments[0].as_numbers == [100, 200]
    assert got_v4.communities[0].as_number == 1
    assert got_v4.communities[0].as_custom == 2

    got_v6 = state.ipv6_unicast_prefixes[0]
    assert got_v6.ipv6_address == "4000::"
    assert got_v6.ipv6_next_hop == "2000::1"
    assert got_v6.as_path.segments[0].as_numbers == [500, 600]


@pytest.mark.parametrize(
    "as_path_cell, community_cell",
    [
        ("{100 200} 300", "1:2 3:4"),
        ("(65001) [65002] <4200000000>", "no-export 65535:65535"),
        ("", ""),
    ],
)
def test_varied_attributes_survive_the_model(
    bgp, as_path_cell, community_cell
):
    prefix = bgp._row_to_ipv4_prefix(
        v4_row(**{"AS Path": as_path_cell, "Community": community_cell})
    )
    response = snappi.StatesResponse()
    response.deserialize(
        {
            "choice": "bgp_prefixes",
            "bgp_prefixes": [
                {
                    "bgp_peer_name": "p",
                    "ipv4_unicast_prefixes": [prefix],
                }
            ],
        }
    )
    response.serialize()
