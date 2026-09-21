"""Pure unit tests for snappi_ixnetwork.vport.Vport.

These tests use lightweight Mocks instead of a real IxNetwork API
server/connection so they can run without hardware.
"""

import json
from types import SimpleNamespace

import pytest

from snappi_ixnetwork.vport import Vport


class MockObj(dict):
    """dict-backed stand-in for a snappi generated object.

    Supports both attribute access (``obj.field``) and the
    ``obj.get(name, with_default=True)`` calling convention used
    throughout vport.py.
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, key, with_default=False):
        return dict.get(self, key)


class Finder:
    """Mimics an ixnetwork_restpy node whose .find() returns a fixed result."""

    def __init__(self, result):
        self.result = result

    def find(self):
        return self.result


class Node(list):
    """List-like collection that also exposes child attributes."""

    def __init__(self, items=None, **children):
        super().__init__(items if items is not None else [])
        self._children = children

    def __getattr__(self, name):
        try:
            return self._children[name]
        except KeyError:
            raise AttributeError(name)


class MockApi:
    def __init__(self):
        self.warnings = []
        self.infos = []
        self.request_calls = []
        self.remove_calls = []
        self.clear_ownership_calls = []

    def warning(self, msg):
        self.warnings.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def _request(self, method, url, payload):
        self.request_calls.append((method, url, payload))

    def _remove(self, ixn_collection, config_items):
        self.remove_calls.append((ixn_collection, config_items))

    def clear_ownership(self, available_hardware_hrefs, location_hrefs):
        self.clear_ownership_calls.append(
            (available_hardware_hrefs, location_hrefs)
        )


def make_vport(api=None):
    api = api if api is not None else MockApi()
    return Vport(api), api


# ---------------------------------------------------------------------------
# _wait_for
# ---------------------------------------------------------------------------


def test_wait_for_returns_on_success():
    vport, _ = make_vport()
    assert vport._wait_for(lambda: True, "timed out", 0, 5) is True


def test_wait_for_raises_on_timeout():
    vport, _ = make_vport()
    with pytest.raises(Exception, match="timed out"):
        vport._wait_for(lambda: False, "timed out", 0, 0)


# ---------------------------------------------------------------------------
# is_protocols_stopped
# ---------------------------------------------------------------------------


def test_is_protocols_stopped_with_no_topologies():
    vport, api = make_vport()
    api._ixnetwork = SimpleNamespace(Topology=Finder(Node([])))
    assert vport.is_protocols_stopped() is True


def test_is_protocols_stopped_with_topology_but_no_device_groups():
    vport, api = make_vport()
    topo = Node([1], DeviceGroup=Finder(Node([])))
    api._ixnetwork = SimpleNamespace(Topology=Finder(topo))
    assert vport.is_protocols_stopped() is True


def test_is_protocols_stopped_with_device_groups_but_no_ethernet():
    vport, api = make_vport()
    dgs = Node([1], Ethernet=Finder(Node([])))
    topo = Node([1], DeviceGroup=Finder(dgs))
    api._ixnetwork = SimpleNamespace(Topology=Finder(topo))
    assert vport.is_protocols_stopped() is True


def test_is_protocols_stopped_with_ethernet_but_no_ipv4():
    vport, api = make_vport()
    eth = Node([1], Ipv4=Finder(Node([])), SessionStatus=["up"])
    dgs = Node([1], Ethernet=Finder(eth))
    topo = Node([1], DeviceGroup=Finder(dgs))
    api._ixnetwork = SimpleNamespace(Topology=Finder(topo))
    assert vport.is_protocols_stopped() is True


@pytest.mark.parametrize(
    "session_status, expected_stopped",
    [
        (["up"], False),
        (["down"], False),
        (["notStarted"], True),
    ],
)
def test_is_protocols_stopped_with_ipv4_and_session_status(
    session_status, expected_stopped
):
    vport, api = make_vport()
    eth = Node([1], Ipv4=Finder(Node([1])), SessionStatus=session_status)
    dgs = Node([1], Ethernet=Finder(eth))
    topo = Node([1], DeviceGroup=Finder(dgs))
    api._ixnetwork = SimpleNamespace(Topology=Finder(topo))
    assert vport.is_protocols_stopped() is expected_stopped


# ---------------------------------------------------------------------------
# _import
# ---------------------------------------------------------------------------


class MockResourceManager:
    def __init__(self, errata=None):
        self.errata = errata if errata is not None else []
        self.calls = []

    def ImportConfig(self, payload, arg2):
        self.calls.append((payload, arg2))
        return self.errata


def test_import_with_empty_imports_does_not_call_resource_manager():
    vport, api = make_vport()
    vport._resource_manager = MockResourceManager()
    vport._resource_manager.ImportConfig = lambda *a: (_ for _ in ()).throw(
        AssertionError("should not be called")
    )
    assert vport._import([]) is True


def test_import_success_returns_true():
    vport, api = make_vport()
    rm = MockResourceManager(errata=[])
    vport._resource_manager = rm
    imports = [{"xpath": "/vport[1]", "name": "p1"}]
    assert vport._import(imports) is True
    assert rm.calls == [(json.dumps(imports), False)]
    assert api.warnings == []


def test_import_with_errata_warns_and_returns_false():
    vport, api = make_vport()
    rm = MockResourceManager(errata=["warn1", "warn2"])
    vport._resource_manager = rm
    assert vport._import([{"xpath": "/vport[1]"}]) is False
    assert api.warnings == ["warn1", "warn2"]


# ---------------------------------------------------------------------------
# set_link_state
# ---------------------------------------------------------------------------


def test_set_link_state_builds_expected_payload():
    vport, api = make_vport()
    api._ixnetwork = SimpleNamespace(href="http://server/ixnetwork")
    api.ixn_objects = SimpleNamespace(get_href=lambda name: "href_%s" % name)
    link_state = SimpleNamespace(state="up", port_names=["p1", "p2"])

    vport.set_link_state(link_state)

    assert api.request_calls == [
        (
            "POST",
            "http://server/ixnetwork/vport/operations/linkupdn",
            {"arg1": ["href_p1", "href_p2"], "arg2": "up"},
        )
    ]


# ---------------------------------------------------------------------------
# _delete_vports / _create_vports
# ---------------------------------------------------------------------------


def test_delete_vports_calls_remove_with_ports():
    vport, api = make_vport()
    vport._ixn_vport = "vport_collection"
    api.snappi_config = SimpleNamespace(ports=["p1", "p2"])

    vport._delete_vports()

    assert api.remove_calls == [("vport_collection", ["p1", "p2"])]


def test_create_vports_imports_only_new_ports_and_registers_all():
    vport, api = make_vport()
    existing_vport = {"name": "p1", "xpath": "/vport[1]"}
    api.select_vports = lambda: {"p1": existing_vport}
    api.snappi_config = SimpleNamespace(
        ports=[
            MockObj(name="p1", location="10.1.1.1;1;1"),
            MockObj(name="p2", location=None),
        ]
    )
    captured_imports = []
    vport._import = lambda imports: captured_imports.append(imports) or True
    registered = []
    api.ixn_objects = SimpleNamespace(
        set=lambda name, obj: registered.append((name, obj))
    )

    vport._create_vports()

    assert len(captured_imports) == 1
    imports = captured_imports[0]
    assert len(imports) == 1
    assert imports[0]["name"] == "p2"
    assert imports[0]["xpath"] == "/vport[2]"
    assert imports[0]["connectedTo"] is None
    # port.location should have been reset to None for the new port
    assert api.snappi_config.ports[1].location is None
    assert registered == [("p1", existing_vport)]


# ---------------------------------------------------------------------------
# _set_vport_type
# ---------------------------------------------------------------------------


def test_set_vport_type_adds_fcoe_suffix_when_flow_control_present():
    vport, api = make_vport()
    ixn_vport = {"type": "ethernet", "xpath": "/vport[1]"}
    layer1 = MockObj(flow_control=MockObj(choice="ieee_802_1qbb"))
    imports = []

    result = vport._set_vport_type(ixn_vport, layer1, imports)

    assert result == "ethernetFcoe"
    assert imports == [
        {"xpath": "/vport[1]/l1Config", "currentType": "ethernetFcoe"}
    ]


def test_set_vport_type_strips_fcoe_suffix_when_flow_control_absent():
    vport, api = make_vport()
    ixn_vport = {"type": "ethernetFcoe", "xpath": "/vport[1]"}
    layer1 = MockObj()
    imports = []

    result = vport._set_vport_type(ixn_vport, layer1, imports)

    assert result == "ethernet"
    assert imports == [
        {"xpath": "/vport[1]/l1Config", "currentType": "ethernet"}
    ]


def test_set_vport_type_no_change_appends_nothing():
    vport, api = make_vport()
    ixn_vport = {"type": "ethernet", "xpath": "/vport[1]"}
    layer1 = MockObj()
    imports = []

    result = vport._set_vport_type(ixn_vport, layer1, imports)

    assert result == "ethernet"
    assert imports == []


# ---------------------------------------------------------------------------
# _add_l1config_import
# ---------------------------------------------------------------------------


def test_add_l1config_import_removes_matching_keys():
    vport, api = make_vport()
    ixn_vport = {
        "type": "ethernet",
        "l1Config": {
            "ethernet": {
                "speed": "speed1000",
                "media": "copper",
                "autoNegotiate": True,
                "speedAuto": [],
            }
        },
    }
    proposed = {
        "xpath": "/vport[1]/l1Config/ethernet",
        "speed": "speed1000",
        "media": "fiber",
        "autoNegotiate": True,
        "speedAuto": [],
    }
    imports = []

    vport._add_l1config_import(ixn_vport, proposed, imports)

    assert imports == [
        {"xpath": "/vport[1]/l1Config/ethernet", "media": "fiber"}
    ]


def test_add_l1config_import_keeps_speed_when_speed_auto_differs():
    vport, api = make_vport()
    ixn_vport = {
        "type": "ethernet",
        "l1Config": {
            "ethernet": {
                "speed": "speed1000",
                "media": "copper",
                "autoNegotiate": True,
                "speedAuto": ["speed100"],
            }
        },
    }
    proposed = {
        "xpath": "/vport[1]/l1Config/ethernet",
        "speed": "speed1000",
        "media": "copper",
        "autoNegotiate": True,
        "speedAuto": [],
    }
    imports = []

    vport._add_l1config_import(ixn_vport, proposed, imports)

    assert imports == [
        {
            "xpath": "/vport[1]/l1Config/ethernet",
            "speed": "speed1000",
            "speedAuto": [],
        }
    ]


# ---------------------------------------------------------------------------
# _set_ethernet_auto_negotiation / _set_gigabit_auto_negotiation
# ---------------------------------------------------------------------------


def test_set_ethernet_auto_negotiation_builds_import():
    vport, api = make_vport()
    ixn_vport = {
        "type": "ethernet",
        "xpath": "/vport[1]",
        "l1Config": {
            "ethernet": {
                "speed": "speed10g",
                "media": "copper",
                "autoNegotiate": False,
                "speedAuto": [],
            }
        },
    }
    layer1 = MockObj(speed="speed_1_gbps", media="fiber", auto_negotiate=True)
    imports = []

    vport._set_ethernet_auto_negotiation(ixn_vport, layer1, imports)

    assert len(imports) == 1
    assert imports[0]["xpath"] == "/vport[1]/l1Config/ethernet"
    assert imports[0]["speed"] == "speed1000"
    assert imports[0]["speedAuto"] == ["speed1000"]
    assert imports[0]["media"] == "fiber"
    assert imports[0]["autoNegotiate"] is True


@pytest.mark.parametrize(
    "speed, advertise_key",
    [
        ("speed_100_fd_mbps", "advertise_one_hundred_fd_mbps"),
        ("speed_100_hd_mbps", "advertise_one_hundred_hd_mbps"),
        ("speed_10_fd_mbps", "advertise_ten_fd_mbps"),
        ("speed_10_hd_mbps", "advertise_ten_hd_mbps"),
    ],
)
def test_set_ethernet_auto_negotiation_advertise_speeds(speed, advertise_key):
    vport, api = make_vport()
    ixn_vport = {
        "type": "ethernet",
        "xpath": "/vport[1]",
        "l1Config": {"ethernet": {"speedAuto": []}},
    }
    layer1 = MockObj(speed=speed, media="fiber", auto_negotiate=True)
    imports = []

    vport._set_ethernet_auto_negotiation(ixn_vport, layer1, imports)

    assert imports[0]["speedAuto"] == [Vport._ADVERTISE_MAP[advertise_key]]


def test_set_gigabit_auto_negotiation_builds_import():
    vport, api = make_vport()
    ixn_vport = {
        "type": "ethernet",
        "xpath": "/vport[1]",
        "l1Config": {
            "ethernet": {
                "ieeeL1Defaults": False,
                "speed": "speed1000",
                "enableAutoNegotiation": False,
                "enableRsFec": False,
                "linkTraining": True,
                "speedAuto": [],
                "media": "copper",
            }
        },
    }
    layer1 = MockObj(
        speed="speed_10_gbps",
        media="fiber",
        auto_negotiate=True,
        ieee_media_defaults=True,
        auto_negotiation=MockObj(rs_fec=True, link_training=False),
    )
    imports = []

    vport._set_gigabit_auto_negotiation(ixn_vport, layer1, imports)

    assert len(imports) == 2
    ieee_defaults_import = imports[0]
    assert ieee_defaults_import["ieeeL1Defaults"] is True
    proposed_import = imports[1]
    assert proposed_import["speed"] == "speed10g"
    assert proposed_import["enableAutoNegotiation"] is True
    assert proposed_import["enableRsFec"] is True
    assert proposed_import["linkTraining"] is False
    assert proposed_import["media"] == "fiber"


def test_set_gigabit_auto_negotiation_uses_autonegotiate_field_for_novus():
    vport, api = make_vport()
    ixn_vport = {
        "type": "novusTenGigLan",
        "xpath": "/vport[1]",
        "l1Config": {
            "novusTenGigLan": {
                "ieeeL1Defaults": False,
                "speed": "speed1000",
                "autoNegotiate": False,
                "enableRsFec": False,
                "linkTraining": True,
                "speedAuto": [],
                "media": "copper",
            }
        },
    }
    layer1 = MockObj(
        speed="speed_10_gbps",
        media="fiber",
        auto_negotiate=True,
        ieee_media_defaults=True,
        auto_negotiation=MockObj(rs_fec=True, link_training=False),
    )
    imports = []

    vport._set_gigabit_auto_negotiation(ixn_vport, layer1, imports)

    proposed_import = imports[1]
    assert "autoNegotiate" in proposed_import
    assert "enableAutoNegotiation" not in proposed_import


def test_set_gigabit_auto_negotiation_defaults_when_unset():
    vport, api = make_vport()
    ixn_vport = {
        "type": "ethernet",
        "xpath": "/vport[1]",
        "l1Config": {
            "ethernet": {
                "ieeeL1Defaults": False,
                "speed": "speed10g",
                "enableAutoNegotiation": True,
                "enableRsFec": True,
                "linkTraining": True,
                "speedAuto": [],
                "media": "copper",
            }
        },
    }
    layer1 = MockObj(
        speed="speed_10_gbps",
        media="fiber",
        auto_negotiate=None,
        ieee_media_defaults=None,
        auto_negotiation=MockObj(rs_fec=None, link_training=None),
    )
    imports = []

    vport._set_gigabit_auto_negotiation(ixn_vport, layer1, imports)

    ieee_defaults_import = imports[0]
    assert ieee_defaults_import["ieeeL1Defaults"] == "True"
    proposed_import = imports[1]
    # auto_negotiate defaults to the string "True" (not the bool True)
    # before the None-check for enableAutoNegotiation is ever reached
    assert proposed_import["enableAutoNegotiation"] == "True"
    assert proposed_import["enableRsFec"] is False
    assert proposed_import["linkTraining"] is False


# ---------------------------------------------------------------------------
# _get_speed
# ---------------------------------------------------------------------------


def test_get_speed_uses_vm_map_for_ethernetvm():
    vport, api = make_vport()
    layer1 = MockObj(speed="speed_9_gbps")
    assert vport._get_speed({"type": "ethernetvm"}, layer1) == "speed9000"


def test_get_speed_uses_normal_map_otherwise():
    vport, api = make_vport()
    layer1 = MockObj(speed="speed_10_gbps")
    assert vport._get_speed({"type": "ethernet"}, layer1) == "speed10g"


# ---------------------------------------------------------------------------
# _reset_auto_negotiation
# ---------------------------------------------------------------------------


def test_reset_auto_negotiation_skips_mbps_speeds():
    vport, api = make_vport()
    layer1 = MockObj(speed="speed_100_fd_mbps", auto_negotiate=True)
    imports = []
    vport._reset_auto_negotiation(
        {"type": "ethernet", "xpath": "/vport[1]"}, layer1, imports
    )
    assert imports == []


def test_reset_auto_negotiation_skips_1gbps():
    vport, api = make_vport()
    layer1 = MockObj(speed="speed_1_gbps", auto_negotiate=True)
    imports = []
    vport._reset_auto_negotiation(
        {"type": "ethernet", "xpath": "/vport[1]"}, layer1, imports
    )
    assert imports == []


def test_reset_auto_negotiation_resets_other_speeds():
    vport, api = make_vport()
    layer1 = MockObj(speed="speed_10_gbps", auto_negotiate=True)
    imports = []
    vport._reset_auto_negotiation(
        {"type": "ethernet", "xpath": "/vport[1]"}, layer1, imports
    )
    assert imports == [
        {
            "xpath": "/vport[1]/l1Config/ethernet",
            "enableAutoNegotiation": True,
        }
    ]


# ---------------------------------------------------------------------------
# _set_fcoe
# ---------------------------------------------------------------------------


def test_set_fcoe_skips_when_no_flow_control():
    vport, api = make_vport()
    layer1 = MockObj()
    imports = []
    vport._set_fcoe(
        {"type": "ethernet", "xpath": "/vport[1]"}, layer1, imports
    )
    assert imports == []


def test_set_fcoe_builds_imports_for_ieee_802_1qbb():
    vport, api = make_vport()
    pfc = MockObj(
        pfc_delay=5,
        pfc_class_0=0,
        pfc_class_1=None,
        pfc_class_2=None,
        pfc_class_3=None,
        pfc_class_4=None,
        pfc_class_5=None,
        pfc_class_6=None,
        pfc_class_7=None,
    )
    flow_control = MockObj(
        directed_address="01:80:c2:00:00:01",
        choice="ieee_802_1qbb",
        ieee_802_1qbb=pfc,
    )
    layer1 = MockObj(flow_control=flow_control)
    imports = []

    vport._set_fcoe(
        {"type": "ethernet", "xpath": "/vport[1]"}, layer1, imports
    )

    assert len(imports) == 2
    assert imports[0] == {
        "xpath": "/vport[1]/l1Config/ethernet",
        "flowControlDirectedAddress": "0180c2000001",
    }
    fcoe_import = imports[1]
    assert fcoe_import["xpath"] == "/vport[1]/l1Config/ethernet/fcoe"
    assert fcoe_import["flowControlType"] == "ieee802.1Qbb"
    assert fcoe_import["enablePFCPauseDelay"] is True
    assert fcoe_import["pfcPauseDelay"] == 5
    assert fcoe_import["pfcPriorityGroups"] == [0, -1, -1, -1, -1, -1, -1, -1]


# ---------------------------------------------------------------------------
# _set_card_resource_mode
# ---------------------------------------------------------------------------


def test_set_card_resource_mode_skips_when_not_connected():
    vport, api = make_vport()
    ixn_vport = {"connectionState": "connectedLinkDown"}
    ixn_vport["connectionState"] = "unconnected"
    layer1 = MockObj(name="l1", speed="speed_40_gbps")
    imports = []
    vport._set_card_resource_mode(ixn_vport, layer1, imports)
    assert imports == []


def test_set_card_resource_mode_skips_when_already_checked():
    vport, api = make_vport()
    vport._layer1_check = ["l1"]
    ixn_vport = {"connectionState": "connectedLinkUp"}
    layer1 = MockObj(name="l1", speed="speed_40_gbps")
    imports = []
    vport._set_card_resource_mode(ixn_vport, layer1, imports)
    assert imports == []


def test_set_card_resource_mode_sets_matching_aggregation_mode():
    vport, api = make_vport()
    ixn_vport = {"connectionState": "connectedLinkUp"}
    layer1 = MockObj(name="l1", speed="speed_40_gbps")
    card = {
        "xpath": "/card[1]",
        "description": "card1",
        "aggregationMode": "TenGig",
        "availableModes": ["FortyGig", "TenGig"],
    }
    api.select_chassis_card = lambda vport_arg: card
    imports = []

    vport._set_card_resource_mode(ixn_vport, layer1, imports)

    assert imports == [{"xpath": "/card[1]", "aggregationMode": "FortyGig"}]


# ---------------------------------------------------------------------------
# _set_l1config_properties / _set_auto_negotiation dispatch
# ---------------------------------------------------------------------------


def test_set_l1config_properties_skips_when_not_connected():
    vport, api = make_vport()
    calls = []
    vport._set_fcoe = lambda *a, **k: calls.append("fcoe")
    vport._set_auto_negotiation = lambda *a, **k: calls.append("auto")

    vport._set_l1config_properties(
        {"connectionState": "unconnected"}, MockObj(), []
    )

    assert calls == []


def test_set_l1config_properties_calls_helpers_when_connected():
    vport, api = make_vport()
    calls = []
    vport._set_fcoe = lambda *a, **k: calls.append("fcoe")
    vport._set_auto_negotiation = lambda *a, **k: calls.append("auto")

    vport._set_l1config_properties(
        {"connectionState": "connectedLinkUp"}, MockObj(), []
    )

    assert calls == ["fcoe", "auto"]


@pytest.mark.parametrize(
    "speed, expected",
    [
        ("speed_100_fd_mbps", "ethernet"),
        ("speed_1_gbps", "ethernet"),
        ("speed_10_gbps", "gigabit"),
    ],
)
def test_set_auto_negotiation_dispatches_by_speed(speed, expected):
    vport, api = make_vport()
    calls = []
    vport._set_ethernet_auto_negotiation = lambda *a, **k: calls.append(
        "ethernet"
    )
    vport._set_gigabit_auto_negotiation = lambda *a, **k: calls.append(
        "gigabit"
    )

    vport._set_auto_negotiation({}, MockObj(speed=speed), [])

    assert calls == [expected]


# ---------------------------------------------------------------------------
# _get_chassis_location_map
# ---------------------------------------------------------------------------


def test_get_chassis_location_map_combines_chassis_and_ports():
    vport, api = make_vport()
    chassis_list = [SimpleNamespace(Hostname="10.1.1.1", href="href_chassis")]
    port = SimpleNamespace(Location="10.1.1.1/1/1", href="href_port")
    location = SimpleNamespace(Ports=SimpleNamespace(find=lambda: [port]))
    api._ixnetwork = SimpleNamespace(
        AvailableHardware=SimpleNamespace(
            Chassis=SimpleNamespace(find=lambda: chassis_list)
        ),
        Locations=SimpleNamespace(find=lambda: [location]),
    )

    result = vport._get_chassis_location_map()

    assert result == {
        "10.1.1.1": "href_chassis",
        "10.1.1.1/1/1": "href_port",
    }


# ---------------------------------------------------------------------------
# _clear_ownership
# ---------------------------------------------------------------------------


def test_clear_ownership_noop_when_preemption_disabled():
    vport, api = make_vport()
    api.snappi_config = SimpleNamespace(
        options=SimpleNamespace(
            port_options=SimpleNamespace(location_preemption=False)
        )
    )

    vport._clear_ownership(["10.1.1.1;1;1"])

    assert api.clear_ownership_calls == []


def test_clear_ownership_noop_when_options_missing():
    vport, api = make_vport()
    api.snappi_config = SimpleNamespace()

    vport._clear_ownership(["10.1.1.1;1;1"])

    assert api.clear_ownership_calls == []


def test_clear_ownership_builds_hrefs_for_chassis_port_locations():
    vport, api = make_vport()
    api.snappi_config = SimpleNamespace(
        options=SimpleNamespace(
            port_options=SimpleNamespace(location_preemption=True)
        )
    )
    vport._get_chassis_location_map = lambda: {"10.1.1.1": "href_chassis"}

    vport._clear_ownership(["10.1.1.1;1;1"])

    assert api.clear_ownership_calls == [
        ({"10.1.1.1;1;1": "href_chassis/card/1/port/1"}, {})
    ]


def test_clear_ownership_uses_existing_href_for_slash_location():
    vport, api = make_vport()
    api.snappi_config = SimpleNamespace(
        options=SimpleNamespace(
            port_options=SimpleNamespace(location_preemption=True)
        )
    )
    vport._get_chassis_location_map = lambda: {
        "appliance/1/1": "href_appliance_port"
    }

    vport._clear_ownership(["appliance/1/1"])

    assert api.clear_ownership_calls == [
        ({}, {"appliance/1/1": "href_appliance_port"})
    ]


def test_clear_ownership_adds_location_host_when_missing_from_map():
    vport, api = make_vport()
    api.snappi_config = SimpleNamespace(
        options=SimpleNamespace(
            port_options=SimpleNamespace(location_preemption=True)
        )
    )
    added_hosts = []
    call_count = {"n": 0}

    def Mock_map():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {}
        return {"appliance/1/1": "href_appliance_port"}

    vport._get_chassis_location_map = Mock_map
    api._ixnetwork = SimpleNamespace(
        Locations=SimpleNamespace(
            add=lambda Hostname: added_hosts.append(Hostname)
        )
    )

    vport._clear_ownership(["appliance/1/1"])

    assert added_hosts == ["appliance"]
    assert api.clear_ownership_calls == [
        ({}, {"appliance/1/1": "href_appliance_port"})
    ]


# ---------------------------------------------------------------------------
# _set_result_value
# ---------------------------------------------------------------------------


def test_set_result_value_skips_unrequested_column():
    vport, api = make_vport()
    vport._column_names = ["frames_tx"]
    row = {}
    vport._set_result_value(row, "bytes_tx", "10", int)
    assert row == {}


def test_set_result_value_converts_successfully():
    vport, api = make_vport()
    vport._column_names = []
    row = {}
    vport._set_result_value(row, "frames_tx", "10", int)
    assert row == {"frames_tx": 10}


def test_set_result_value_falls_back_to_zero_on_conversion_error():
    vport, api = make_vport()
    vport._column_names = []
    row = {}
    vport._set_result_value(row, "frames_tx", "not-a-number", int)
    assert row == {"frames_tx": 0}


def test_set_result_value_falls_back_for_non_numeric_type_on_error():
    vport, api = make_vport()
    vport._column_names = []

    class Explodes:
        def __str__(self):
            raise ValueError("boom")

    row = {}
    vport._set_result_value(row, "name", Explodes(), str)
    assert row[str] is not None


# ---------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------


def test_results_returns_defaults_when_stat_viewer_unavailable():
    vport, api = make_vport()
    ixn_vport = {
        "name": "p1",
        "location": "10.1.1.1",
        "connectionState": "connectedLinkUp",
    }
    api.special_char = lambda names: names
    api.select_vports = lambda port_name_filters=None: {"p1": ixn_vport}

    def raise_no_viewer(name):
        raise Exception("no viewer")

    api.assistant = SimpleNamespace(StatViewAssistant=raise_no_viewer)

    rows = vport.results(MockObj(column_names=None, port_names=["p1"]))

    assert api.warnings == ["Could not retrive the port statistics viewer"]
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "p1"
    assert row["location"] == "10.1.1.1;connected"
    assert row["link"] == "up"
    assert row["capture"] == "stopped"
    assert row["frames_tx"] == 0
    assert row["bytes_rx_rate"] == 0.0


def test_results_merges_stat_view_rows():
    vport, api = make_vport()
    ixn_vport = {
        "name": "p1",
        "location": "",
        "connectionState": "down",
    }
    api._config = SimpleNamespace(ports=[MockObj(name="p1")])
    api.special_char = lambda names: names
    api.select_vports = lambda port_name_filters=None: {"p1": ixn_vport}
    stat_row = {
        "Port Name": "p1",
        "Frames Tx.": "100",
        "Valid Frames Rx.": "90",
        "Frames Tx. Rate": "1.5",
        "Valid Frames Rx. Rate": "1.2",
        "Bytes Tx.": "1000",
        "Bytes Rx.": "900",
        "Bytes Tx. Rate": "10.0",
        "Bytes Rx. Rate": "9.0",
    }
    api.assistant = SimpleNamespace(
        StatViewAssistant=lambda name: SimpleNamespace(Rows=[stat_row])
    )

    rows = vport.results(MockObj(column_names=None, port_names=None))

    assert len(rows) == 1
    row = rows[0]
    assert row["location"] == "down"
    assert row["link"] == "down"
    assert row["frames_tx"] == 100
    assert row["frames_rx"] == 90
    assert row["frames_tx_rate"] == 1.5
    assert row["bytes_tx"] == 1000
    assert row["bytes_rx_rate"] == 9.0


def test_results_raises_on_invalid_column_names_type():
    vport, api = make_vport()
    with pytest.raises(Exception, match="Invalid format"):
        vport.results(MockObj(column_names="not-a-list", port_names=["p1"]))


def test_results_raises_on_invalid_port_names_type():
    vport, api = make_vport()
    with pytest.raises(Exception, match="Invalid format"):
        vport.results(MockObj(column_names=None, port_names="not-a-list"))


def test_results_appends_connection_state_for_unconnected_location():
    vport, api = make_vport()
    ixn_vport = {
        "name": "p1",
        "location": "10.1.1.1",
        "connectionState": "unconnected",
    }
    api.special_char = lambda names: names
    api.select_vports = lambda port_name_filters=None: {"p1": ixn_vport}
    api.assistant = SimpleNamespace(
        StatViewAssistant=lambda name: (_ for _ in ()).throw(Exception())
    )

    rows = vport.results(MockObj(column_names=None, port_names=["p1"]))

    assert rows[0]["location"] == "10.1.1.1;unconnected"


def test_results_raises_when_stat_row_missing_port_name():
    vport, api = make_vport()
    ixn_vport = {
        "name": "p1",
        "location": "10.1.1.1",
        "connectionState": "connectedLinkUp",
    }
    api.special_char = lambda names: names
    api.select_vports = lambda port_name_filters=None: {"p1": ixn_vport}
    api.assistant = SimpleNamespace(
        StatViewAssistant=lambda name: SimpleNamespace(
            Rows=[{"Port Name": None}]
        )
    )

    with pytest.raises(Exception, match="Could not retrive 'Port Name'"):
        vport.results(MockObj(column_names=None, port_names=["p1"]))


def test_results_skips_stat_rows_for_unknown_ports():
    vport, api = make_vport()
    ixn_vport = {
        "name": "p1",
        "location": "10.1.1.1",
        "connectionState": "connectedLinkUp",
    }
    api.special_char = lambda names: names
    api.select_vports = lambda port_name_filters=None: {"p1": ixn_vport}
    api.assistant = SimpleNamespace(
        StatViewAssistant=lambda name: SimpleNamespace(
            Rows=[{"Port Name": "unknown-port"}]
        )
    )

    rows = vport.results(MockObj(column_names=None, port_names=["p1"]))

    assert rows[0]["name"] == "p1"
    assert rows[0]["frames_tx"] == 0


def test_results_defaults_column_when_stat_row_missing_field():
    vport, api = make_vport()
    ixn_vport = {
        "name": "p1",
        "location": "10.1.1.1",
        "connectionState": "connectedLinkUp",
    }
    api.special_char = lambda names: names
    api.select_vports = lambda port_name_filters=None: {"p1": ixn_vport}
    stat_row = {"Port Name": "p1"}
    api.assistant = SimpleNamespace(
        StatViewAssistant=lambda name: SimpleNamespace(Rows=[stat_row])
    )

    rows = vport.results(MockObj(column_names=None, port_names=["p1"]))

    assert rows[0]["frames_tx"] == 0
