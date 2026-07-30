"""Object-level regression tests for IPv6 BGP route-range compaction.

Ref: Case 02198204 (nexthop.ai) - when N structurally-identical IPv6 BGP
route ranges are compacted into a single multiplied node (which happens
whenever a device-group / network-group multiplier > 1 is in play), the
snappi name->object map used to lose the per-member xpath / instance index
for every member except the representative. As a result:

  * advertise / withdraw / flap of a *single* name could work, but
  * advertise / withdraw of a *subset* (a list of >= 2 names that resolve to
    the same compacted node) raised ``KeyError`` in ``set_route_state``.

These tests exercise the two fixes without a live IxNetwork:

  * Defect B - ``IxNetObjects.set_scalable`` must repoint every compacted
    member at the representative node (real xpath) with a unique instance
    index, even when the member's own pre-compaction node had a different
    key-set (the data-dependent divergence that hit IPv6 but not IPv4).
  * Defect A - ``Ngpf.set_route_state`` must group requested names by the
    matched existing key, so a subset (list) of names resolving to the same
    compacted node does not raise ``KeyError``.
"""

import types
import logging

import pytest

from snappi_ixnetwork.objectdb import IxNetObjects
from snappi_ixnetwork.device.ngpf import Ngpf

REP_XPATH = (
    "/topology[1]/deviceGroup[1]/networkGroup[1]"
    "/ipv6PrefixPools[1]/bgpV6IPRouteProperty[1]"
)


def _make_api(ixn_routes=None):
    """A minimal fake api sufficient for IxNetObjects / set_route_state."""
    topology = types.SimpleNamespace(ApplyOnTheFly=lambda: None)
    globals_ = types.SimpleNamespace(Topology=topology)
    ixnetwork = types.SimpleNamespace(Globals=globals_)
    return types.SimpleNamespace(
        ngpf=types.SimpleNamespace(working_dg="dg0"),
        ixn_routes=ixn_routes,
        _ixnetwork=ixnetwork,
    )


def _build_compacted_routes(names, divergent_members=True):
    """Reproduce the state after a device/network-group multiplier compacts
    ``names`` into a single node, then runs ``set_scalable`` and finally the
    xpath assignment done by CreateIxnConfig.

    Returns the populated ``IxNetObjects`` instance and the representative
    node dict.
    """
    ixn_routes = IxNetObjects(_make_api())

    # 1. During config build, set_ixn_routes registers each route node. The
    #    first (representative) node is the primary object that compaction
    #    keeps and mutates in place; the rest are separate nodes.
    rep = {"xpath": "", "name": names[0], "networkAddress": "2000::1"}
    ixn_routes.set(names[0], rep)
    for name in names[1:]:
        member = {"xpath": "", "name": name, "networkAddress": "2000::1"}
        if divergent_members:
            # The IPv6 data-dependent case: the member's own node key-set
            # diverges from the compacted representative (here the compacted
            # node gains a "multiplier" key). This is what used to trip the
            # old ``if old_keys != keys: continue`` guard.
            pass
        else:
            # IPv4-style case that always worked: identical key-set.
            member["multiplier"] = 1
        ixn_routes.set(name, member)

    # 2. Compaction mutates the representative node in place and rewrites its
    #    name into the full member list before calling set_scalable.
    rep["multiplier"] = len(names)
    rep["name"] = list(names)
    ixn_routes.set_scalable(rep)

    # 3. CreateIxnConfig assigns the real xpath to the node still in the tree
    #    (the representative). Members repointed at it inherit this lazily.
    rep["xpath"] = REP_XPATH
    return ixn_routes, rep


class _RouteStateHarness(object):
    """Binds the real ``Ngpf.set_route_state`` onto a light fake so we can
    drive it without a live IxNetwork."""

    _ROUTE_STATE = Ngpf._ROUTE_STATE
    set_route_state = Ngpf.set_route_state

    def __init__(self, api, active_values):
        self.api = api
        self.logger = logging.getLogger("test_ipv6_route_compaction")
        self._active_values = active_values
        self.configured = []
        self.imported = None

    def select_properties(self, xpath, properties):
        assert xpath == REP_XPATH
        return {"active": {"values": list(self._active_values[xpath])}}

    def configure_value(self, xpath, attr, values):
        self.configured.append((xpath, attr, list(values)))
        return {"xpath": xpath, attr: values}

    def imports(self, imports):
        self.imported = imports


def test_set_scalable_ipv6_members_inherit_representative_xpath():
    """Defect B: every compacted member resolves to the representative xpath
    with a unique instance index in [0, N)."""
    names = [
        "tc1_peer0_routes_ipv6",
        "tc1_peer1_routes_ipv6",
        "tc1_peer2_routes_ipv6",
    ]
    ixn_routes, rep = _build_compacted_routes(names, divergent_members=True)

    seen_index = set()
    for expected_index, name in enumerate(names):
        info = ixn_routes.get(name)
        assert (
            info.xpath == REP_XPATH
        ), "member %s lost the representative xpath (got %r)" % (
            name,
            info.xpath,
        )
        assert info.ixnobject is rep
        assert info.index == expected_index
        assert info.multiplier == 1
        seen_index.add(info.index)
    assert seen_index == {0, 1, 2}


def test_set_scalable_no_regression_for_identical_keysets():
    """IPv4-style members with an identical key-set keep working."""
    names = ["v4_peer0", "v4_peer1", "v4_peer2"]
    ixn_routes, rep = _build_compacted_routes(names, divergent_members=False)

    for expected_index, name in enumerate(names):
        info = ixn_routes.get(name)
        assert info.xpath == REP_XPATH
        assert info.index == expected_index
        assert info.multiplier == 1


def test_set_scalable_preserves_foreign_object_with_usable_xpath():
    """A same-named object already resolving to a usable xpath under a
    genuinely different structure must not be clobbered."""
    ixn_routes = IxNetObjects(_make_api())
    foreign = {"xpath": "/foreign[1]", "name": "shared", "onlyHere": True}
    ixn_routes.set("shared", foreign)

    rep = {
        "xpath": "",
        "name": ["shared", "other"],
        "networkAddress": "2000::1",
        "multiplier": 2,
    }
    ixn_routes.set("other", {"xpath": "", "name": "other"})
    ixn_routes.set_scalable(rep)

    # "shared" keeps its own usable xpath; it is not repointed at rep.
    assert ixn_routes.get("shared").xpath == "/foreign[1]"


def test_set_route_state_subset_does_not_raise_keyerror():
    """Defect A: withdrawing a subset (list) of names that resolve to the
    same compacted node must not raise KeyError and must flip only the
    requested instances."""
    names = [
        "tc1_peer0_routes_ipv6",
        "tc1_peer1_routes_ipv6",
        "tc1_peer2_routes_ipv6",
    ]
    ixn_routes, _ = _build_compacted_routes(names, divergent_members=True)
    api = _make_api(ixn_routes)

    harness = _RouteStateHarness(
        api, active_values={REP_XPATH: ["true", "true", "true"]}
    )
    payload = types.SimpleNamespace(
        state="withdraw", names=[names[0], names[1]]
    )

    returned = harness.set_route_state(payload)

    assert sorted(returned) == sorted([names[0], names[1]])
    # One import per representative xpath (the two names collapse to one node).
    assert len(harness.configured) == 1
    xpath, attr, values = harness.configured[0]
    assert xpath == REP_XPATH
    assert attr == "active"
    # Only instances 0 and 1 are withdrawn; instance 2 is untouched.
    assert values[0] is False
    assert values[1] is False
    assert values[2] == "true"


def test_set_route_state_single_name_still_works():
    """Withdrawing a single name (the case that already worked) is
    unaffected."""
    names = [
        "tc1_peer0_routes_ipv6",
        "tc1_peer1_routes_ipv6",
        "tc1_peer2_routes_ipv6",
    ]
    ixn_routes, _ = _build_compacted_routes(names, divergent_members=True)
    api = _make_api(ixn_routes)

    harness = _RouteStateHarness(
        api, active_values={REP_XPATH: ["true", "true", "true"]}
    )
    payload = types.SimpleNamespace(state="withdraw", names=[names[1]])

    harness.set_route_state(payload)

    _, _, values = harness.configured[0]
    assert values[0] == "true"
    assert values[1] is False
    assert values[2] == "true"


def test_set_route_state_full_list_withdraws_all_instances():
    """Withdrawing the full list flips every instance of the compacted
    node."""
    names = [
        "tc1_peer0_routes_ipv6",
        "tc1_peer1_routes_ipv6",
        "tc1_peer2_routes_ipv6",
    ]
    ixn_routes, _ = _build_compacted_routes(names, divergent_members=True)
    api = _make_api(ixn_routes)

    harness = _RouteStateHarness(
        api, active_values={REP_XPATH: ["true", "true", "true"]}
    )
    payload = types.SimpleNamespace(state="withdraw", names=list(names))

    harness.set_route_state(payload)

    assert len(harness.configured) == 1
    _, _, values = harness.configured[0]
    assert values == [False, False, False]


if __name__ == "__main__":
    pytest.main(["-sv", __file__])
