from types import SimpleNamespace

import pytest

from snappi_ixnetwork.device.base import MultiValue
from snappi_ixnetwork.device.vxlan import VXLAN


class AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class MockIxnObjects:
    def __init__(self, infos):
        self._infos = infos

    def get(self, name):
        return self._infos[name]


class MockApi:
    def __init__(self, infos, encap_by_source):
        self.ixn_objects = MockIxnObjects(infos)
        self._encap_by_source = encap_by_source

    def get_device_encap(self, source_interface):
        return self._encap_by_source[source_interface]


class MockNgpf:
    def __init__(self, infos, encap_by_source):
        self.api = MockApi(infos, encap_by_source)
        self.working_dg = None
        self.device_info = []

    def set_device_info(self, snappi_obj, ixn_obj):
        self.device_info.append((snappi_obj, ixn_obj))


def value(item):
    if isinstance(item, MultiValue):
        return item.value
    return item


def make_vxlan(encap_by_source=None):
    if encap_by_source is None:
        encap_by_source = {"ip1": "ipv4", "ip6": "ipv6"}
    infos = {
        "ip1": SimpleNamespace(ixnobject={}, working_dg="dg4"),
        "ip6": SimpleNamespace(ixnobject={}, working_dg="dg6"),
    }
    ngpf = MockNgpf(infos, encap_by_source)
    vxlan = VXLAN(ngpf)
    vxlan.source_interfaces.ipv4.clear()
    vxlan.source_interfaces.ipv6.clear()
    return vxlan, ngpf, infos


def vtep(remote_vtep_address, cache=None):
    return AttrDict(
        remote_vtep_address=remote_vtep_address,
        arp_suppression_cache=cache or [],
    )


def cache(remote_vm_mac, remote_vm_ipv4):
    return AttrDict(remote_vm_mac=remote_vm_mac, remote_vm_ipv4=remote_vm_ipv4)


def unicast(*vteps):
    return SimpleNamespace(vteps=list(vteps))


def destination(choice, unicast_value=None, multicast_address=None):
    return SimpleNamespace(
        choice=choice,
        unicast=unicast_value,
        multicast=AttrDict(address=multicast_address),
    )


def tunnel(name, source_interface, vni, destination_ip_mode):
    return AttrDict(
        name=name,
        source_interface=source_interface,
        vni=vni,
        destination_ip_mode=destination_ip_mode,
    )


def test_config_with_no_tunnels_does_not_create_ixn_nodes():
    vxlan, ngpf, infos = make_vxlan()

    vxlan.config(AttrDict(v4_tunnels=[], v6_tunnels=[]))

    assert infos["ip1"].ixnobject == {}
    assert infos["ip6"].ixnobject == {}
    assert ngpf.device_info == []


def test_source_interface_storage_deduplicates_by_ip_type():
    vxlan, _, _ = make_vxlan()
    ixn_ipv4 = {"name": "ipv4"}
    ixn_ipv6 = {"name": "ipv6"}

    vxlan._store_source_interface(ixn_ipv4, "ipv4")
    vxlan._store_source_interface(ixn_ipv4, "ipv4")
    vxlan._store_source_interface(ixn_ipv6, "ipv6")
    vxlan._store_source_interface(ixn_ipv6, "ipv6")

    assert vxlan.source_interfaces.ipv4 == [ixn_ipv4]
    assert vxlan.source_interfaces.ipv6 == [ixn_ipv6]


def test_config_v4_unicast_tunnel_populates_static_info():
    vxlan, ngpf, infos = make_vxlan()
    config = AttrDict(
        v4_tunnels=[
            tunnel(
                "vxlan4",
                "ip1",
                1000,
                destination(
                    "unicast",
                    unicast(
                        vtep("2.2.2.2"),
                        vtep(
                            "3.3.3.3",
                            [cache("00:00:00:00:00:03", "100.1.1.3")],
                        ),
                    ),
                ),
            )
        ],
        v6_tunnels=[],
    )

    vxlan.config(config)

    ixn_vxlan = infos["ip1"].ixnobject["vxlan"][0]
    ixn_static = ixn_vxlan["vxlanStaticInfo"][0]
    assert ngpf.working_dg == "dg4"
    assert ngpf.device_info == [(config["v4_tunnels"][0], ixn_vxlan)]
    assert value(ixn_vxlan["name"]) == "vxlan4"
    assert ixn_vxlan["multiplier"] == 1
    assert value(ixn_vxlan["vni"]) == 1000
    assert ixn_vxlan["enableStaticInfo"] is True
    assert ixn_vxlan["staticInfoCount"] == 2
    assert value(ixn_static["remoteVtepIpv4"]) == ["2.2.2.2", "3.3.3.3"]
    assert value(ixn_static["suppressArp"]) == [False, True]
    assert value(ixn_static["remoteVmStaticMac"]) == [
        "00:00:00:00:00:00",
        "00:00:00:00:00:03",
    ]
    assert value(ixn_static["remoteVmStaticIpv4"]) == ["0.0.0.0", "100.1.1.3"]
    assert vxlan.source_interfaces.ipv4 == [infos["ip1"].ixnobject]


def test_config_v4_multicast_tunnel_populates_multicast_address():
    vxlan, _, infos = make_vxlan()
    config = AttrDict(
        v4_tunnels=[
            tunnel(
                "vxlan4",
                "ip1",
                2000,
                destination("multicast", multicast_address="239.1.1.1"),
            )
        ],
        v6_tunnels=[],
    )

    vxlan.config(config)

    ixn_vxlan = infos["ip1"].ixnobject["vxlan"][0]
    assert ixn_vxlan["enableStaticInfo"] is False
    assert value(ixn_vxlan["ipv4_multicast"]) == "239.1.1.1"


def test_config_v4_tunnel_rejects_non_ipv4_source_interface():
    vxlan, _, _ = make_vxlan({"ip1": "ipv6", "ip6": "ipv6"})
    config = AttrDict(
        v4_tunnels=[
            tunnel(
                "vxlan4",
                "ip1",
                1000,
                destination("multicast", multicast_address="239.1.1.1"),
            )
        ],
        v6_tunnels=[],
    )

    with pytest.raises(TypeError, match="ip1 should support IPv4"):
        vxlan.config(config)


def test_config_v6_unicast_tunnel_populates_static_info():
    vxlan, ngpf, infos = make_vxlan()
    config = AttrDict(
        v4_tunnels=[],
        v6_tunnels=[
            tunnel(
                "vxlan6",
                "ip6",
                3000,
                destination(
                    "unicast",
                    unicast(
                        vtep(
                            "2000::2",
                            [cache("00:00:00:00:00:06", "100.1.1.6")],
                        )
                    ),
                ),
            )
        ],
    )

    vxlan.config(config)

    ixn_vxlan = infos["ip6"].ixnobject["vxlanv6"][0]
    ixn_static = ixn_vxlan["vxlanIPv6StaticInfo"][0]
    assert ngpf.working_dg == "dg6"
    assert value(ixn_vxlan["name"]) == "vxlan6"
    assert value(ixn_vxlan["vni"]) == 3000
    assert ixn_vxlan["enableStaticInfo"] is True
    assert ixn_vxlan["staticInfoCount"] == 1
    assert value(ixn_static["remoteVtepUnicastIpv6"]) == ["2000::2"]
    assert value(ixn_static["suppressArp"]) == [True]
    assert value(ixn_static["remoteVmStaticMac"]) == ["00:00:00:00:00:06"]
    assert value(ixn_static["remoteVmStaticIpv4"]) == ["100.1.1.6"]
    assert vxlan.source_interfaces.ipv6 == [infos["ip6"].ixnobject]


def test_config_v6_multicast_tunnel_populates_multicast_address():
    vxlan, _, infos = make_vxlan()
    config = AttrDict(
        v4_tunnels=[],
        v6_tunnels=[
            tunnel(
                "vxlan6",
                "ip6",
                4000,
                destination("multicast", multicast_address="ff05::1"),
            )
        ],
    )

    vxlan.config(config)

    ixn_vxlan = infos["ip6"].ixnobject["vxlanv6"][0]
    assert ixn_vxlan["enableStaticInfo"] is False
    assert value(ixn_vxlan["ipv6_multicast"]) == "ff05::1"


def test_config_v6_tunnel_rejects_non_ipv6_source_interface():
    vxlan, _, _ = make_vxlan({"ip1": "ipv4", "ip6": "ipv4"})
    config = AttrDict(
        v4_tunnels=[],
        v6_tunnels=[
            tunnel(
                "vxlan6",
                "ip6",
                1000,
                destination("multicast", multicast_address="ff05::1"),
            )
        ],
    )

    with pytest.raises(TypeError, match="ip6 should support IPv6"):
        vxlan.config(config)


def test_get_all_info_expands_each_arp_suppression_cache_entry():
    vxlan, _, _ = make_vxlan()

    count, all_info = vxlan._get_all_info(
        unicast(
            vtep("2.2.2.2"),
            vtep(
                "3.3.3.3",
                [
                    cache("00:00:00:00:00:01", "100.1.1.1"),
                    cache("00:00:00:00:00:02", "100.1.1.2"),
                ],
            ),
        )
    )

    assert count == 3
    assert all_info.remote_vtep_address == ["2.2.2.2", "3.3.3.3", "3.3.3.3"]
    assert all_info.suppress_arp == [False, True, True]
    assert all_info.remote_vm_mac == [
        "00:00:00:00:00:00",
        "00:00:00:00:00:01",
        "00:00:00:00:00:02",
    ]
    assert all_info.remote_vm_ipv4 == ["0.0.0.0", "100.1.1.1", "100.1.1.2"]
