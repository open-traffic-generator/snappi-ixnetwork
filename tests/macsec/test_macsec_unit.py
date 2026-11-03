"""Hardware-free unit tests for the MACsec device build phase.

No chassis and no IxNetwork server are needed: Ngpf is created with a mocked
API and the tests assert on the plain dict tree in ngpf._ixn_config.
"""

import pytest
import snappi
from unittest.mock import MagicMock

from snappi_ixnetwork.device.base import MultiValue
from snappi_ixnetwork.device.macsec import Macsec
from snappi_ixnetwork.device.macsec_hw import MacsecHw
from snappi_ixnetwork.device.mka import Mka
from snappi_ixnetwork.device.ngpf import Ngpf
from snappi_ixnetwork.exceptions import SnappiIxnException

SAK128 = "f123456789abcdef0123456789abcdef"
SAK256 = SAK128 + SAK128
SSCI = "0000000a"
SALT = "00000000000000000000000b"


def _value(node, key):
    value = node[key]
    return value.value if isinstance(value, MultiValue) else value


class _Env(object):
    """Config plus a minimal Ngpf/Macsec able to run Macsec.config()."""

    def __init__(self):
        self.config = snappi.Api().config()
        self.ixn_ethernets = {}
        self.warnings = []

    def device(self, name, engine="encrypt_only", key="static_key", **kw):
        device = self.config.devices.add()
        device.name = name
        eth = device.ethernets.add()
        eth.name = name + "_eth"
        eth.mac = "00:00:00:00:00:11"
        eth.connection.port_name = kw.get("port", "p1")
        ip = eth.ipv4_addresses.add()
        ip.name = name + "_ip"
        ip.address = "1.1.1.1"
        ip.gateway_mac.value = "00:00:00:00:00:22"
        iface = device.macsec.ethernet_interfaces.add()
        iface.eth_name = eth.name
        secy = iface.secure_entity
        secy.name = name + "_secy"
        self.configure(
            secy, engine, key, kw.get("cipher", "gcm_aes_128"), kw.get("sak")
        )
        return device

    def configure(self, secy, engine, key, cipher="gcm_aes_128", sak=None):
        secy.data_plane.choice = "encapsulation"
        crypto = secy.data_plane.encapsulation.crypto_engine
        if engine == "encrypt_only":
            crypto.choice = "encrypt_only"
            crypto.encrypt_only.secure_channels.add()
        elif engine == "encrypt_decrypt":
            crypto.choice = "encrypt_decrypt"
        elif engine == "inline_crypto":
            crypto.choice = "encrypt_decrypt"
            crypto.encrypt_decrypt.hardware_acceleration.choice = (
                "inline_crypto"
            )
        secy.key_generation_protocol.choice = key
        if key == "static_key":
            static_key = secy.key_generation_protocol.static_key
            static_key.cipher_suite = cipher
            sak = sak or (SAK128 if "128" in cipher else SAK256)
            for side in (static_key.tx, static_key.rx):
                sc = side.secure_channels.add()
                for _ in range(3):
                    s = sc.saks.add()
                    s.sak, s.ssci, s.salt = sak, SSCI, SALT
        return secy

    def macsec(self):
        ngpf = Ngpf.__new__(Ngpf)
        ngpf.api = MagicMock()
        ngpf.api.snappi_config = self.config
        ngpf.logger = MagicMock()
        ngpf.ether_ip_restriction_map = {}
        ngpf.api.ixn_objects.get_working_dg.return_value = {"name": "dg"}
        ngpf.api.ixn_objects.get_object.side_effect = lambda n: (
            self.ixn_ethernets.setdefault(n, {"xpath": ""})
        )
        macsec = Macsec(ngpf)
        macsec.logger = MagicMock()
        self.ngpf = ngpf
        return macsec

    def build(self, device_name=None):
        macsec = self.macsec()
        for device in self.config.devices:
            macsec.config(device)
            macsec.set_ip_restriction(device)
        self.logger = macsec.logger
        return macsec

    def node(self, device_name, kind="staticMacsec"):
        return self.ixn_ethernets[device_name + "_eth"][kind][0]


def _status(excinfo):
    return excinfo.value.status_code


# U18: software regression


def test_encrypt_only_static_key_baseline():
    env = _Env()
    env.device("d1")
    env.build()
    node = env.node("d1")
    assert node["encryptedTrafficType"] == "statelessL23"
    assert _value(node, "cipherSuite") == "aes128"
    assert node["txSakPoolSize"] == 3
    assert node["rxSakPoolSize"] == 3
    assert _value(node["txSakPool"][0], "txSak128") == [SAK128] * 3
    assert _value(node["rxSakPool"][0], "rxSak128") == [SAK128] * 3
    assert "txSsci" not in node["txSakPool"][0]
    assert _value(node, "sourceIp") == "1.1.1.1"
    assert _value(node, "dutMac") == "00:00:00:00:00:22"
    env.ngpf.api.set_device_traffic_endpoint.assert_any_call(
        "d1_eth", "d1_secy"
    )
    assert env.ngpf.ether_ip_restriction_map == {"d1_eth": True}
    # name registered so flows can reference the secure entity
    env.ngpf.api.ixn_objects.set.assert_called_with("d1_secy", node)


# U2 / U3 / U4: cipher suites, SAK pools


@pytest.mark.parametrize(
    "cipher,enum,attr,xpn",
    [
        ("gcm_aes_128", "aes128", "Sak128", False),
        ("gcm_aes_256", "aes256", "Sak256", False),
        ("gcm_aes_xpn_128", "aesxpn128", "Sak128", True),
        ("gcm_aes_xpn_256", "aesxpn256", "Sak256", True),
    ],
)
def test_cipher_suites_and_sak_attributes(cipher, enum, attr, xpn):
    env = _Env()
    env.device("d1", cipher=cipher)
    env.build()
    node = env.node("d1")
    assert _value(node, "cipherSuite") == enum
    for direction in ("tx", "rx"):
        pool = node[direction + "SakPool"][0]
        assert direction + attr in pool
        other = "Sak256" if attr == "Sak128" else "Sak128"
        assert direction + other not in pool
        assert (direction + "Ssci" in pool) is xpn
        assert (direction + "Salt" in pool) is xpn


def test_rx_secure_channel_dut_sci_mapped():
    env = _Env()
    device = env.device("d1")
    rxsc = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.static_key.rx.secure_channels[0]
    rxsc.dut_sci_system_id = "00:00:00:00:00:22"
    rxsc.dut_sci_port_id = 7
    env.build()
    node = env.node("d1")
    assert _value(node, "dutSciMac") == "00:00:00:00:00:22"
    assert _value(node, "dutSciPortId") == 7


# U15: encrypt_decrypt + none -> staticMacsec, stateful


def test_encrypt_decrypt_none_uses_static_macsec_stateful():
    env = _Env()
    device = env.device("d1", engine="encrypt_decrypt")
    tx_pn = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.data_plane.encapsulation.crypto_engine.encrypt_decrypt.tx_pn
    tx_pn.starting_pn = 5
    tx_pn.starting_xpn = "0000000000000009"
    env.build()
    eth = env.ixn_ethernets["d1_eth"]
    assert "macsec" not in eth
    node = env.node("d1")
    assert node["encryptedTrafficType"] == "statefulL47"
    assert _value(node, "startingPn") == 5
    assert _value(node, "startingXpn") == "0000000000000009"
    assert "sourceIp" not in node and "dutMac" not in node
    assert env.ngpf.ether_ip_restriction_map == {}


def _hw_crypto(device):
    return device.macsec.ethernet_interfaces[
        0
    ].secure_entity.data_plane.encapsulation


# Hardware (inline crypto) engine


def test_inline_crypto_builds_macsec_node_not_static_macsec():
    env = _Env()
    device = env.device("d1", engine="inline_crypto")
    tx_pn = _hw_crypto(device).crypto_engine.encrypt_decrypt.tx_pn
    tx_pn.starting_pn = 5
    tx_pn.starting_xpn = "0000000000000009"
    env.build()
    eth = env.ixn_ethernets["d1_eth"]
    assert "staticMacsec" not in eth
    node = env.node("d1", "macsec")
    assert "encryptedTrafficType" not in node
    assert _value(node, "cipherSuite") == "aes128"
    assert _value(node, "startingPn") == 5
    assert _value(node, "startingXpn") == "0000000000000009"
    assert "sourceIp" not in node and "dutMac" not in node
    assert env.ngpf.ether_ip_restriction_map == {}
    env.ngpf.api.ixn_objects.set.assert_called_with("d1_secy", node)


@pytest.mark.parametrize(
    "engine,moved",
    [("inline_crypto", True), ("encrypt_decrypt", True), ("encrypt_only", False)],
)
def test_ip_stacked_under_stateful_engine_node_only(engine, moved):
    env = _Env()
    env.device("d1", engine=engine)
    ip = {"xpath": "", "name": "d1_ip"}
    ip6 = {"xpath": "", "name": "d1_ip6"}
    env.ixn_ethernets["d1_eth"] = {"xpath": "", "ipv4": [ip], "ipv6": [ip6]}
    env.build()
    eth = env.ixn_ethernets["d1_eth"]
    if moved:
        node = env.node(
            "d1", "macsec" if engine == "inline_crypto" else "staticMacsec"
        )
        assert node["ipv4"] == [ip] and node["ipv4"][0] is ip
        assert node["ipv6"] == [ip6]
        assert "ipv4" not in eth and "ipv6" not in eth
    else:
        assert eth["ipv4"] == [ip] and eth["ipv6"] == [ip6]


@pytest.mark.parametrize(
    "cipher,attr,xpn",
    [
        ("gcm_aes_128", "Sak128", False),
        ("gcm_aes_256", "Sak256", False),
        ("gcm_aes_xpn_128", "Sak128", True),
        ("gcm_aes_xpn_256", "Sak256", True),
    ],
)
def test_inline_crypto_sak_pools(cipher, attr, xpn):
    env = _Env()
    env.device("d1", engine="inline_crypto", cipher=cipher)
    env.build()
    node = env.node("d1", "macsec")
    assert node["txSakPoolSize"] == 3 and node["rxSakPoolSize"] == 3
    for direction in ("tx", "rx"):
        pool = node[direction + "SakPool"][0]
        assert direction + attr in pool
        assert (direction + "Ssci" in pool) is xpn


def test_inline_crypto_replay_window_mapped_without_ignored_warning():
    env = _Env()
    device = env.device("d1", engine="inline_crypto")
    _hw_crypto(device).rx.replay_window = 64
    env.build()
    assert _value(env.node("d1", "macsec"), "replayWindowSize") == 64
    env.logger.warning.assert_not_called()


def test_inline_crypto_replay_protection_reported_as_per_port():
    env = _Env()
    device = env.device("d1", engine="inline_crypto")
    _hw_crypto(device).rx.replay_protection = True
    env.build()
    assert env.logger.warning.call_count == 0
    assert "replayProtection" not in env.node("d1", "macsec")


@pytest.mark.parametrize(
    "choice,mode,behaviour",
    [
        ("dont_rekey", "timerBased", "dontRekey"),
        ("pn_based", "pnBased", "rekeyContinuous"),
    ],
)
def test_inline_crypto_rekey_mode(choice, mode, behaviour):
    env = _Env()
    device = env.device("d1", engine="inline_crypto")
    key = device.macsec.ethernet_interfaces[0].secure_entity
    key.key_generation_protocol.static_key.tx.rekey_mode.choice = choice
    env.build()
    node = env.node("d1", "macsec")
    assert node["rekeyMode"] == mode
    assert node["rekeyBehaviour"] == behaviour


def test_inline_crypto_timer_based_rekey():
    env = _Env()
    device = env.device("d1", engine="inline_crypto")
    rekey = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.static_key.tx.rekey_mode
    rekey.choice = "timer_based"
    rekey.timer_based.choice = "fixed_count"
    rekey.timer_based.fixed_count = 3
    rekey.timer_based.interval = 60
    env.build()
    node = env.node("d1", "macsec")
    assert node["rekeyMode"] == "timerBased"
    assert node["rekeyBehaviour"] == "rekeyFixedCount"
    assert node["periodicRekeyAttempts"] == 3
    assert node["periodicRekeyInterval"] == 60


def test_inline_crypto_with_mka_writes_no_sak_pools():
    env = _Env()
    device = env.device("d1", engine="inline_crypto", key="mka")
    macsec = env.macsec()
    macsec._mka = MagicMock()
    macsec.config(device)
    node = env.node("d1", "macsec")
    assert "txSakPool" not in node and "rxSakPool" not in node
    macsec._mka.config.assert_called_once_with(device)


def test_inline_crypto_end_station_and_sci():
    env = _Env()
    device = env.device("d1", engine="inline_crypto")
    tx = _hw_crypto(device).tx
    tx.end_station = True
    tx.include_sci = True
    env.build()
    node = env.node("d1", "macsec")
    assert _value(node, "endStation") is True
    assert _value(node, "includeSci") is True


def test_software_and_hardware_in_different_devices_accepted():
    env = _Env()
    env.device("d1", engine="encrypt_only", port="p1")
    env.device("d2", engine="inline_crypto", port="p1")
    Macsec.validate_config(env.config)
    env.build()
    assert "staticMacsec" in env.ixn_ethernets["d1_eth"]
    assert "macsec" in env.ixn_ethernets["d2_eth"]


def test_software_and_hardware_in_one_device_rejected():
    env = _Env()
    device = env.device("d1", engine="encrypt_decrypt")
    eth2 = device.ethernets.add()
    eth2.name = "d1_eth2"
    eth2.connection.port_name = "p1"
    iface2 = device.macsec.ethernet_interfaces.add()
    iface2.eth_name = eth2.name
    iface2.secure_entity.name = "d1_secy2"
    env.configure(
        iface2.secure_entity, "inline_crypto", "static_key", "gcm_aes_128"
    )
    with pytest.raises(SnappiIxnException) as excinfo:
        Macsec.validate_config(env.config)
    assert _status(excinfo) == 400


def test_inline_crypto_sak_length_checked():
    env = _Env()
    env.device("d1", engine="inline_crypto", sak=SAK256)
    with pytest.raises(SnappiIxnException) as excinfo:
        env.build()
    assert _status(excinfo) == 400


# U27: encrypt_only options


def test_encrypt_only_send_gratuitous_arp_mapped():
    env = _Env()
    device = env.device("d1")
    (
        device.macsec.ethernet_interfaces[
            0
        ].secure_entity.data_plane.encapsulation.crypto_engine.encrypt_only.traffic_options.send_gratuitous_arp
    ) = False
    env.build()
    assert env.node("d1")["sendGratArp"] is False


# U14 / U14b: no_encapsulation


def test_no_encapsulation_with_mka_builds_no_macsec_node():
    env = _Env()
    device = env.device("d1", key="mka")
    secy = device.macsec.ethernet_interfaces[0].secure_entity
    secy.data_plane.choice = "no_encapsulation"
    macsec = env.macsec()
    macsec._mka = MagicMock()
    macsec.config(device)
    assert env.ixn_ethernets == {}
    macsec._mka.config.assert_called_once_with(device)


def test_no_encapsulation_with_static_key_is_rejected():
    env = _Env()
    device = env.device("d1")
    device.macsec.ethernet_interfaces[0].secure_entity.data_plane.choice = (
        "no_encapsulation"
    )
    with pytest.raises(SnappiIxnException) as excinfo:
        env.build()
    assert _status(excinfo) == 400


# U16: empty secure channels / SAKs


def test_empty_secure_channels_rejected_not_index_error():
    env = _Env()
    device = env.device("d1")
    static_key = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.static_key
    static_key.tx.secure_channels.clear()
    with pytest.raises(SnappiIxnException) as excinfo:
        env.build()
    assert _status(excinfo) == 400
    assert "secure_channels" in str(excinfo.value)


def test_missing_saks_rejected():
    env = _Env()
    device = env.device("d1")
    static_key = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.static_key
    static_key.rx.secure_channels[0].saks.clear()
    with pytest.raises(SnappiIxnException) as excinfo:
        env.build()
    assert _status(excinfo) == 400


# U21: SAK length against cipher suite


@pytest.mark.parametrize(
    "cipher,sak",
    [
        ("gcm_aes_128", SAK256),
        ("gcm_aes_xpn_128", SAK256),
        ("gcm_aes_256", SAK128),
        ("gcm_aes_xpn_256", SAK128),
    ],
)
def test_sak_length_must_match_cipher_suite(cipher, sak):
    env = _Env()
    env.device("d1", cipher=cipher, sak=sak)
    with pytest.raises(SnappiIxnException) as excinfo:
        env.build()
    assert _status(excinfo) == 400
    assert "hex digits" in str(excinfo.value)


def test_sak_with_0x_prefix_accepted():
    env = _Env()
    env.device("d1", sak="0x" + SAK128)
    env.build()


# U22: pn_based rekey on software


@pytest.mark.parametrize("engine", ["encrypt_only", "encrypt_decrypt"])
def test_pn_based_rekey_rejected_on_software(engine):
    env = _Env()
    device = env.device("d1", engine=engine)
    (
        device.macsec.ethernet_interfaces[
            0
        ].secure_entity.key_generation_protocol.static_key.tx.rekey_mode
    ).choice = "pn_based"
    with pytest.raises(SnappiIxnException) as excinfo:
        env.build()
    assert _status(excinfo) == 400
    assert "pn_based" in str(excinfo.value)


def test_timer_based_rekey_mapped():
    env = _Env()
    device = env.device("d1")
    rekey = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.static_key.tx.rekey_mode
    rekey.choice = "timer_based"
    rekey.timer_based.choice = "fixed_count"
    rekey.timer_based.fixed_count = 3
    rekey.timer_based.interval = 60
    env.build()
    node = env.node("d1")
    assert node["rekeyBehaviour"] == "rekeyFixedCount"
    assert node["periodicRekeyAttempts"] == 3
    assert node["periodicRekeyInterval"] == 60


# U23: replay settings are warned about and not written


def test_replay_settings_warn_and_are_not_written():
    env = _Env()
    device = env.device("d1")
    rx = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.data_plane.encapsulation.rx
    rx.replay_protection = True
    rx.replay_window = 32
    env.build()
    assert env.logger.warning.call_count == 2
    node = env.node("d1")
    assert "replayWindowSize" not in node and "replayProtection" not in node


# U17: per secure entity dispatch (B1, B2)


def test_dynamic_key_is_decided_per_secure_entity():
    env = _Env()
    device = env.device("d1")
    # second interface on the same device uses MKA (no static SAK pools)
    eth2 = device.ethernets.add()
    eth2.name = "d1_eth2"
    eth2.connection.port_name = "p1"
    iface2 = device.macsec.ethernet_interfaces.add()
    iface2.eth_name = eth2.name
    iface2.secure_entity.name = "d1_secy2"
    env.configure(iface2.secure_entity, "encrypt_only", "mka")
    macsec = env.macsec()
    macsec._mka = MagicMock()
    macsec.config(device)
    first = env.ixn_ethernets["d1_eth"]["staticMacsec"][0]
    second = env.ixn_ethernets["d1_eth2"]["staticMacsec"][0]
    assert "txSakPool" in first
    assert "txSakPool" not in second


def test_every_interface_is_checked_for_data_plane():
    env = _Env()
    device = env.device("d1", key="mka")
    device.macsec.ethernet_interfaces[0].secure_entity.data_plane.choice = (
        "no_encapsulation"
    )
    eth2 = device.ethernets.add()
    eth2.name = "d1_eth2"
    eth2.connection.port_name = "p1"
    ip = eth2.ipv4_addresses.add()
    ip.name, ip.address = "d1_ip2", "1.1.1.2"
    ip.gateway_mac.value = "00:00:00:00:00:22"
    iface2 = device.macsec.ethernet_interfaces.add()
    iface2.eth_name = eth2.name
    iface2.secure_entity.name = "d1_secy2"
    env.configure(iface2.secure_entity, "encrypt_only", "mka")
    macsec = env.macsec()
    macsec._mka = MagicMock()
    macsec.config(device)
    assert "d1_eth" not in env.ixn_ethernets
    assert "staticMacsec" in env.ixn_ethernets["d1_eth2"]


# U13: conflicting engines / key generation on one device or port


def test_mixed_engines_in_one_device_rejected():
    env = _Env()
    device = env.device("d1")
    eth2 = device.ethernets.add()
    eth2.name = "d1_eth2"
    eth2.connection.port_name = "p1"
    iface2 = device.macsec.ethernet_interfaces.add()
    iface2.eth_name = eth2.name
    iface2.secure_entity.name = "d1_secy2"
    env.configure(iface2.secure_entity, "encrypt_decrypt", "static_key")
    with pytest.raises(SnappiIxnException) as excinfo:
        Macsec.validate_config(env.config)
    assert _status(excinfo) == 400
    assert "d1" in str(excinfo.value)


def test_engines_in_different_devices_accepted():
    env = _Env()
    env.device("d1", engine="encrypt_only", port="p1")
    env.device("d2", engine="encrypt_decrypt", port="p1")
    Macsec.validate_config(env.config)


def test_key_generation_mixed_on_one_port_rejected():
    env = _Env()
    env.device("d1", key="static_key", port="p1")
    env.device("d2", key="mka", port="p1")
    with pytest.raises(SnappiIxnException) as excinfo:
        Macsec.validate_config(env.config)
    assert _status(excinfo) == 400
    assert "p1" in str(excinfo.value)


def test_key_generation_on_different_ports_accepted():
    env = _Env()
    env.device("d1", key="static_key", port="p1")
    env.device("d2", key="mka", port="p2")
    Macsec.validate_config(env.config)


# U28: LAG MACsec


def test_lag_port_macsec_rejected():
    config = snappi.Api().config()
    lag = config.lags.add()
    lag.name = "lag1"
    lag_port = lag.ports.add()
    lag_port.port_name = "p1"
    lag_port.macsec.secure_entity.name = "lag_secy"
    with pytest.raises(SnappiIxnException) as excinfo:
        Macsec.validate_config(config)
    assert _status(excinfo) == 400


def test_lag_without_macsec_accepted():
    config = snappi.Api().config()
    lag = config.lags.add()
    lag.name = "lag1"
    lag.ports.add().port_name = "p1"
    Macsec.validate_config(config)


# U24: MKA key source


def test_mka_msk_key_source_rejected():
    from snappi_ixnetwork.device.mka import Mka

    # snappi 1.61.0 only models psk, so the msk choice is faked
    kay = MagicMock()
    kay.get.side_effect = lambda name: {
        "basic": MagicMock(key_source=MagicMock(choice="msk")),
        "tx": MagicMock(),
    }[name]
    with pytest.raises(SnappiIxnException) as excinfo:
        Mka(MagicMock())._is_valid("d1_eth", kay)
    assert _status(excinfo) == 400
    assert "msk" in str(excinfo.value)


def test_mka_psk_key_source_accepted():
    from snappi_ixnetwork.device.mka import Mka

    env = _Env()
    device = env.device("d1", key="mka")
    kay = device.macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.mka
    kay.basic.key_source.choice = "psk"
    kay.basic.key_source.psks.add()
    kay.tx.secure_channels.add()
    assert Mka(MagicMock())._is_valid("d1_eth", kay) is True


# VLAN options (both engines): enableClearTextVlans is a plain bool, the
# inverse of encrypt_interface_vlans


@pytest.mark.parametrize("engine", ["encrypt_only", "inline_crypto"])
@pytest.mark.parametrize("encrypt,clear_text", [(True, False), (False, True)])
def test_vlan_options_map_to_enable_clear_text_vlans(
    engine, encrypt, clear_text
):
    env = _Env()
    device = env.device("d1", engine=engine)
    vlan_options = _hw_crypto(device).vlan_options
    vlan_options.encrypt_interface_vlans = encrypt
    env.build()
    kind = "macsec" if engine == "inline_crypto" else "staticMacsec"
    assert env.node("d1", kind)["enableClearTextVlans"] is clear_text


def test_mka_macsec_capability_enum_values_exist_in_ixnetwork():
    from snappi_ixnetwork.device.mka import Mka

    # values read from IxNetwork 10.80 (mka.MacsecCapability enum)
    allowed = {
        "macsecnotimplemented",
        "macsecintegritywithoutconfidentiality",
        "macsecintegritywithnoconfidentialityoffset",
        "macsecintegritywithconfidentialityoffset",
    }
    mapped = Mka._BASIC["macsec_capability"]["enum_map"].values()
    assert set(mapped) == allowed


# ---------------------------------------------------------------------------
# Per port settings (Globals.Topology.Macsec)


def _port_options(env, port="p1"):
    per_port = env.config.options.per_port_options.add()
    per_port.port_name = port
    protocol = per_port.protocols.add()
    protocol.choice = "macsec"
    return protocol.macsec


def _inline(options):
    options.hardware_acceleration.choice = "inline_crypto"
    return options.hardware_acceleration.inline_crypto


def test_port_settings_none_without_hardware_secy():
    env = _Env()
    env.device("d1", engine="encrypt_only")
    assert MacsecHw.port_settings(env.config) == {}


def test_port_settings_no_options_means_nothing_to_write():
    env = _Env()
    env.device("d1", engine="inline_crypto")
    assert MacsecHw.port_settings(env.config) == {}


def test_port_settings_inline_crypto_defaults_and_mapping():
    env = _Env()
    env.device("d1", engine="inline_crypto")
    options = _port_options(env)
    inline = _inline(options)
    assert MacsecHw.port_settings(env.config) == {
        "RxSecTagOffset": 12,
        "RxScIdentifyingField": "rxscidentifyingfieldsrcmac",
        "MaxCaCount": "macsecmaxcatwohundredfiftysix",
        "TypeOfCa": "pairwiseca",
    }
    inline.rx_sectag_offset = 20
    inline.rx_sc_identifying_field = "sci_port_id"
    inline.max_ca_count = "thirty_two"
    inline.type_of_ca.choice = "group_ca"
    inline.type_of_ca.group_ca.choice = "multiple_dut_tx_sc"
    inline.type_of_ca.group_ca.multiple_dut_tx_sc.max_dut_tx_sc_per_ca = 4
    options.validate_frames.choice = "check"
    attrs = MacsecHw.port_settings(env.config)
    assert attrs["RxSecTagOffset"] == 20
    assert attrs["RxScIdentifyingField"] == "rxscidentifyingfieldsciportid"
    assert attrs["MaxCaCount"] == "macsecmaxcathirtytwo"
    assert attrs["TypeOfCa"] == "groupwithmultidut"
    assert attrs["MaxDutTxScPerCa"] == 4
    assert attrs["MacsecValidation"] == "check"


def test_port_settings_single_dut_group_ca():
    env = _Env()
    env.device("d1", engine="inline_crypto")
    inline = _inline(_port_options(env))
    inline.type_of_ca.choice = "group_ca"
    inline.type_of_ca.group_ca.choice = "single_dut_tx_sc"
    attrs = MacsecHw.port_settings(env.config)
    assert attrs["TypeOfCa"] == "groupwithsingledut"
    assert "MaxDutTxScPerCa" not in attrs


def test_port_settings_strict_validate_frames_rejected():
    env = _Env()
    env.device("d1", engine="inline_crypto")
    _port_options(env).validate_frames.choice = "strict"
    with pytest.raises(SnappiIxnException) as err:
        MacsecHw.port_settings(env.config)
    assert err.value.status_code == 400 and "strict" in str(err.value)


def test_port_settings_max_ca_count_smaller_than_secure_entities():
    env = _Env()
    for name in ("d1", "d2", "d3"):
        env.device(name, engine="inline_crypto")
    inline = _inline(_port_options(env))
    inline.max_ca_count = "two"
    with pytest.raises(SnappiIxnException) as err:
        MacsecHw.port_settings(env.config)
    assert "max_ca_count" in str(err.value)


def test_port_settings_differing_between_ports_rejected():
    env = _Env()
    env.device("d1", engine="inline_crypto", port="p1")
    env.device("d2", engine="inline_crypto", port="p2")
    _inline(_port_options(env, "p1")).rx_sectag_offset = 12
    _inline(_port_options(env, "p2")).rx_sectag_offset = 16
    with pytest.raises(SnappiIxnException) as err:
        MacsecHw.port_settings(env.config)
    assert "differ between ports" in str(err.value)


def test_port_settings_same_on_every_port_accepted():
    env = _Env()
    env.device("d1", engine="inline_crypto", port="p1")
    env.device("d2", engine="inline_crypto", port="p2")
    _inline(_port_options(env, "p1")).rx_sectag_offset = 16
    _inline(_port_options(env, "p2")).rx_sectag_offset = 16
    assert MacsecHw.port_settings(env.config)["RxSecTagOffset"] == 16


def test_port_settings_options_without_hardware_secy_ignored():
    env = _Env()
    env.device("d1", engine="encrypt_decrypt")
    _inline(_port_options(env)).rx_sectag_offset = 99
    assert MacsecHw.port_settings(env.config) == {}


def test_port_settings_replay_protection_from_secure_entity():
    env = _Env()
    d1 = env.device("d1", engine="inline_crypto")
    secy = d1.macsec.ethernet_interfaces[0].secure_entity
    secy.data_plane.encapsulation.rx.replay_protection = True
    assert MacsecHw.port_settings(env.config)["ReplayProtection"] is True


def test_port_settings_replay_protection_conflict_on_one_port_rejected():
    env = _Env()
    for name, value in (("d1", True), ("d2", False)):
        device = env.device(name, engine="inline_crypto")
        secy = device.macsec.ethernet_interfaces[0].secure_entity
        secy.data_plane.encapsulation.rx.replay_protection = value
    with pytest.raises(SnappiIxnException) as err:
        MacsecHw.port_settings(env.config)
    assert "replay_protection" in str(err.value)


def test_apply_port_settings_writes_globals():
    env = _Env()
    env.device("d1", engine="inline_crypto")
    inline = _inline(_port_options(env))
    inline.rx_sectag_offset = 20
    env.config.devices[0].macsec.ethernet_interfaces[
        0
    ].secure_entity.data_plane.encapsulation.rx.replay_protection = True
    ixnetwork = MagicMock()
    glob = ixnetwork.Globals.Topology.find.return_value.Macsec.find.return_value
    MacsecHw.apply_port_settings(ixnetwork, env.config)
    glob.RxSecTagOffset.Single.assert_called_once_with("20")
    glob.ReplayProtection.Single.assert_called_once_with("true")


def test_apply_port_settings_without_hardware_touches_nothing():
    env = _Env()
    env.device("d1", engine="encrypt_only")
    ixnetwork = MagicMock()
    MacsecHw.apply_port_settings(ixnetwork, env.config)
    ixnetwork.Globals.Topology.find.assert_not_called()


# ---------------------------------------------------------------------------
# MKA per port settings (phase 4) and auto_macsec helper (phase 5)


def _mka_basic(device):
    secy = device.macsec.ethernet_interfaces[0].secure_entity
    return secy.key_generation_protocol.mka.basic


def _set_utc(basic, day):
    basic.psk_chain_start_time.choice = "utc"
    utc = basic.psk_chain_start_time.utc
    utc.day, utc.month, utc.year = day, 11, 2026
    utc.hour, utc.minute, utc.second = 1, 2, 3


def test_mka_port_settings_default_ether_type_writes_nothing():
    env = _Env()
    _mka_basic(env.device("d1", engine="inline_crypto", key="mka"))
    assert Mka.port_settings(env.config) == {}


def test_mka_port_settings_ether_type():
    env = _Env()
    d1 = env.device("d1", engine="inline_crypto", key="mka")
    _mka_basic(d1).eapol_ethernet_type = "88E7"
    assert Mka.port_settings(env.config) == {"EtherType": "88e7"}


def test_mka_port_settings_first_instance_on_a_port_wins(caplog):
    env = _Env()
    d1 = env.device("d1", engine="inline_crypto", key="mka")
    d2 = env.device("d2", engine="inline_crypto", key="mka")
    _mka_basic(d1).eapol_ethernet_type = "88E7"
    _mka_basic(d2).eapol_ethernet_type = "88E8"
    with caplog.at_level("WARNING"):
        attrs = Mka.port_settings(env.config)
    assert attrs == {"EtherType": "88e7"}
    assert any("first instance wins" in r.message for r in caplog.records)


def test_mka_port_settings_differing_between_ports_rejected():
    env = _Env()
    d1 = env.device("d1", engine="inline_crypto", key="mka", port="p1")
    d2 = env.device("d2", engine="inline_crypto", key="mka", port="p2")
    _mka_basic(d1).eapol_ethernet_type = "88E7"
    _mka_basic(d2).eapol_ethernet_type = "88E8"
    with pytest.raises(SnappiIxnException) as err:
        Mka.port_settings(env.config)
    assert "differs between ports" in str(err.value)


def test_mka_first_test_start_time_and_conflict_warning(caplog):
    env = _Env()
    d1 = env.device("d1", engine="inline_crypto", key="mka")
    d2 = env.device("d2", engine="inline_crypto", key="mka")
    env.config.devices[0].macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.mka.name = "mka1"
    env.config.devices[1].macsec.ethernet_interfaces[
        0
    ].secure_entity.key_generation_protocol.mka.name = "mka2"
    _set_utc(_mka_basic(d1), 5)
    _set_utc(_mka_basic(d2), 6)
    assert Mka.first_test_start_time(env.config) == (
        "mka1",
        (5, 11, 2026, 1, 2, 3),
    )
    with caplog.at_level("WARNING"):
        Mka.port_settings(env.config)
    assert any("psk_chain_start_time differs" in r.message for r in caplog.records)


def test_mka_apply_port_settings_writes_ether_type():
    env = _Env()
    d1 = env.device("d1", engine="inline_crypto", key="mka")
    _mka_basic(d1).eapol_ethernet_type = "88E7"
    ixnetwork = MagicMock()
    glob = ixnetwork.Globals.Topology.find.return_value.Mka.find.return_value
    Mka.apply_port_settings(ixnetwork, env.config)
    glob.EtherType.Single.assert_called_once_with("88e7")


def test_engines_on_port():
    env = _Env()
    env.device("d1", engine="encrypt_only", port="p1")
    env.device("d2", engine="inline_crypto", port="p1")
    env.device("d3", engine="encrypt_decrypt", port="p2")
    assert Macsec.engines_on_port(env.config, "p1") == {
        "encrypt_only",
        "encrypt_decrypt_inline_crypto",
    }
    assert Macsec.engines_on_port(env.config, "p2") == {
        "encrypt_decrypt_none"
    }
    assert Macsec.engines_on_port(env.config, "p3") == set()


def test_every_device_is_built_when_helpers_iterate_the_config():
    """snappi lists share one iteration index: a helper that iterates
    config.devices while the build loop does the same ends that loop after
    the first device. Mka._config_test_start_time does, via
    Mka.first_test_start_time."""
    env = _Env()
    for name in ("d1", "d2", "d3"):
        device = env.device(name, engine="inline_crypto", key="mka")
        kay = device.macsec.ethernet_interfaces[
            0
        ].secure_entity.key_generation_protocol.mka
        kay.name = "mka_" + name
        kay.basic.key_source.choice = "psk"
        psk = kay.basic.key_source.psks.add()
        psk.cak_name, psk.cak_value = "F" * 64, "F" * 32
        kay.tx.secure_channels.add().name = "txsc_" + name
        _set_utc(kay.basic, 5)
    env.build()
    for name in ("d1", "d2", "d3"):
        eth = env.ixn_ethernets[name + "_eth"]
        assert "macsec" in eth and "mka" in eth, name
