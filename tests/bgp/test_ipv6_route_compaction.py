"""
Hardware-free regression tests for two defects in BGP subset-withdraw
when a device-group or network-group multiplier > 1 is used.

Defect A (ngpf.py)   — set_route_state indexes the accumulator dict by the
                        wrong key when >=2 names share a compacted IxN node,
                        always raising KeyError on list (subset) withdraw.
Defect B (objectdb.py) — set_scalable silently skips IPv6 members whose
                          pre-compaction key-set differs from the compacted
                          representative, leaving them with xpath=='' and
                          index==0.
"""

import pytest
from unittest.mock import MagicMock

from snappi_ixnetwork.objectdb import IxNetObjects, IxNetInfo


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_info(xpath="", index=0, multiplier=1, names=None, extra_keys=None):
    """Return an IxNetInfo backed by a minimal dict ixnobject."""
    ixnobj = {"xpath": xpath}
    if extra_keys:
        ixnobj.update(extra_keys)
    return IxNetInfo(
        ixnobj,
        working_dg=MagicMock(),
        index=index,
        multiplier=multiplier,
        names=names or [],
    )


def _make_ngpf(route_infos):
    """
    Return a minimal Ngpf instance that can execute set_route_state without
    touching IxNetwork hardware.

    route_infos: dict of {route_name: IxNetInfo}
    """
    from snappi_ixnetwork.device.ngpf import Ngpf

    api = MagicMock()
    api.ixn_routes.get.side_effect = lambda name: route_infos[name]
    api.ixn_routes.names = list(route_infos.keys())

    ngpf = Ngpf.__new__(Ngpf)
    ngpf.api = api
    ngpf.logger = MagicMock()

    def _select_props(xpath, properties=None):
        # Build a values list large enough to cover all indices for this xpath.
        max_end = max(
            info.index + info.multiplier
            for info in route_infos.values()
            if info.xpath == xpath
        )
        return {"active": {"values": [True] * max_end}}

    ngpf.select_properties = MagicMock(side_effect=_select_props)
    ngpf.configure_value = MagicMock(return_value={"xpath": "/mock"})
    ngpf.imports = MagicMock()

    return ngpf


def _make_db():
    """Return an IxNetObjects with a mocked API."""
    api = MagicMock()
    api.ngpf.working_dg = MagicMock()
    db = IxNetObjects.__new__(IxNetObjects)
    db._api = api
    db._ixnet_infos = {}
    db.logger = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Fix A — set_route_state
# ---------------------------------------------------------------------------

def test_set_route_state_subset_does_not_raise_keyerror():
    """
    Two names that resolve to the same compacted IxN node must not raise
    KeyError when passed together as a list.  This is the direct customer
    symptom: individual withdraw works, subset (list) withdraw fails.
    """
    shared_xpath = "/topo[1]/dg[1]/ng[1]/bgpV6IPRouteProperty[1]"
    route_infos = {
        "peer0_routes_ipv6": _make_info(xpath=shared_xpath, index=0),
        "peer1_routes_ipv6": _make_info(xpath=shared_xpath, index=1),
    }
    ngpf = _make_ngpf(route_infos)

    payload = MagicMock()
    payload.state = "withdraw"
    payload.names = ["peer0_routes_ipv6", "peer1_routes_ipv6"]

    # Must not raise KeyError
    result = ngpf.set_route_state(payload)
    assert result is not None

    # One compacted node → configure_value called exactly once
    assert ngpf.configure_value.call_count == 1
    # Both instance indices must be set to False (withdrawn)
    values = ngpf.configure_value.call_args[0][2]
    assert values[0] is False
    assert values[1] is False


def test_set_route_state_single_name_still_works():
    """Single-name withdrawal must be unaffected by the fix."""
    xpath = "/topo[1]/dg[1]/ng[1]/bgpV4IPRouteProperty[1]"
    route_infos = {
        "peer0_routes_ipv4": _make_info(xpath=xpath, index=0),
    }
    ngpf = _make_ngpf(route_infos)

    payload = MagicMock()
    payload.state = "withdraw"
    payload.names = ["peer0_routes_ipv4"]

    result = ngpf.set_route_state(payload)
    assert result is not None

    assert ngpf.configure_value.call_count == 1
    values = ngpf.configure_value.call_args[0][2]
    assert values[0] is False


def test_set_route_state_full_list_withdraws_all_instances():
    """
    All three names on the same compacted node: every instance must be
    withdrawn when the full list is supplied.
    """
    xpath = "/topo[1]/dg[1]/ng[1]/bgpV6IPRouteProperty[1]"
    route_infos = {
        "peer0_routes_ipv6": _make_info(xpath=xpath, index=0),
        "peer1_routes_ipv6": _make_info(xpath=xpath, index=1),
        "peer2_routes_ipv6": _make_info(xpath=xpath, index=2),
    }
    ngpf = _make_ngpf(route_infos)

    payload = MagicMock()
    payload.state = "withdraw"
    payload.names = list(route_infos.keys())

    ngpf.set_route_state(payload)

    # Single node → one configure_value call; all three values False
    assert ngpf.configure_value.call_count == 1
    values = ngpf.configure_value.call_args[0][2]
    assert values[0] is False
    assert values[1] is False
    assert values[2] is False


# ---------------------------------------------------------------------------
# Fix B — set_scalable  (currently FAILING until Fix B is applied)
# ---------------------------------------------------------------------------

def _seed_db_with_members(db, names, stale_obj_factory):
    """Pre-register each name in db with an object returned by the factory."""
    for name in names:
        db._ixnet_infos[name] = IxNetInfo(
            stale_obj_factory(name),
            working_dg=MagicMock(),
            index=0,
            multiplier=1,
        )


def test_set_scalable_ipv6_members_inherit_representative_xpath():
    """
    After set_scalable with strict_key_match=False (as used by ixn_routes),
    every member name must point to the representative ixnobject and carry a
    unique index in [0, N) even when the pre-compaction member's key set
    differs from the compacted representative (IPv6 data-dependent divergence).
    """
    N = 4
    names = ["peer%d_routes_ipv6" % i for i in range(N)]

    # Simulate IPv6 pre-compaction nodes: each has an extra key absent from
    # the representative (this is what makes old_keys != keys trip).
    def stale_factory(name):
        return {
            "xpath": "",
            "name": name,
            "networkAddress": "4000::1",
            "prefixLength": 128,
            "ipv6ExtendedCommunities": [],  # extra key absent on representative
        }

    db = _make_db()
    _seed_db_with_members(db, names, stale_factory)

    # Compacted representative: same base keys as before, minus the extra one
    representative = {
        "xpath": "/topo[1]/dg[1]/ng[1]/ipv6PrefixPools[1]/bgpV6IPRouteProperty[1]",
        "name": names,
        "networkAddress": "4000::1",
        "prefixLength": 128,
    }
    db.set_scalable(representative, strict_key_match=False)

    indices = []
    for name in names:
        info = db._ixnet_infos[name]
        assert info.ixnobject is representative, (
            "%s still points to its stale pre-compaction object" % name
        )
        indices.append(info.index)

    assert sorted(indices) == list(range(N)), (
        "Expected unique indices 0..%d, got %s" % (N - 1, indices)
    )


def test_set_scalable_no_regression_for_identical_keysets():
    """
    IPv4-style members whose pre-compaction key-set matches the compacted
    representative are still registered correctly under the default
    strict_key_match=True mode.
    """
    N = 3
    names = ["peer%d_routes_ipv4" % i for i in range(N)]

    def stale_factory(name):
        return {
            "xpath": "",
            "name": name,
            "networkAddress": "10.0.0.1",
            "prefixLength": 32,
        }

    db = _make_db()
    _seed_db_with_members(db, names, stale_factory)

    representative = {
        "xpath": "/topo[1]/dg[1]/ng[1]/ipv4PrefixPools[1]/bgpIPRouteProperty[1]",
        "name": names,
        "networkAddress": "10.0.0.1",
        "prefixLength": 32,
    }
    db.set_scalable(representative)

    indices = [db._ixnet_infos[n].index for n in names]
    assert sorted(indices) == list(range(N))


def test_set_scalable_preserves_foreign_object_with_usable_xpath():
    """
    With the default strict_key_match=True (used by ixn_objects), a
    same-named entry whose key set differs from the incoming node must NOT
    be overwritten.  This prevents cross-type clobbers such as a
    bgpV6IPRouteProperty node overwriting an ipv6PrefixPools entry.
    """
    db = _make_db()
    # A legitimate entry with a real (non-empty) xpath and distinct keys
    foreign_obj = {"xpath": "/real/other/xpath[1]", "name": "shared", "differentKey": True}
    db._ixnet_infos["shared"] = IxNetInfo(
        foreign_obj, working_dg=MagicMock(), index=5, multiplier=1
    )

    # An incoming representative with a different key-set
    representative = {
        "xpath": "",
        "name": ["shared"],
        "networkAddress": "10.0.0.1",
    }
    db.set_scalable(representative)

    info = db._ixnet_infos["shared"]
    assert info.xpath == "/real/other/xpath[1]", "Foreign entry must not be clobbered"
    assert info.index == 5
