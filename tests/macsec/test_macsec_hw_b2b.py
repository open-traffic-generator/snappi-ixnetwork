"""Back-to-back MACsec tests with encrypt_decrypt (stateful) engines.

``none`` runs the software engine (staticMacsec, statefulL47).
``inline_crypto`` runs the hardware engine (macsec node) and needs ports
that support it.
"""

import datetime
import os

import pytest

# A chassis with inline crypto MACsec ports is not available in CI
pytestmark = pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true",
    reason="HW MACSEC supported Chassis is not available in CI",
)

SAK = {
    "gcm_aes_128": "f123456789abcdef0123456789abcdef",
    "gcm_aes_256": "f123456789abcdef0123456789abcdeff123456789abcdef0123456789abcdef",
}
SSCI = "0000000a"
SALT = "00000000000000000000000b"

ENGINES = [
    "none",
    pytest.param("inline_crypto", marks=pytest.mark.macsec_hw),
]


def _device(config, n, port, mac, peer_mac, ip, peer_ip, engine, cipher):
    d = config.devices.add()
    d.name = "d%d" % n
    eth = d.ethernets.add()
    eth.name = "eth%d" % n
    eth.mac = mac
    eth.connection.port_name = port.name
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ip%d" % n
    ipv4.address = ip
    ipv4.gateway = peer_ip
    ipv4.prefix = 24

    iface = d.macsec.ethernet_interfaces.add()
    iface.eth_name = eth.name
    secy = iface.secure_entity
    secy.name = "secy%d" % n
    secy.data_plane.choice = "encapsulation"
    crypto = secy.data_plane.encapsulation.crypto_engine
    crypto.choice = "encrypt_decrypt"
    crypto.encrypt_decrypt.hardware_acceleration.choice = engine

    secy.key_generation_protocol.choice = "static_key"
    sk = secy.key_generation_protocol.static_key
    sk.cipher_suite = cipher
    sk.confidentiality = True
    xpn = "xpn" in cipher
    sak = SAK[cipher.replace("_xpn", "")]

    txsc = sk.tx.secure_channels.add()
    txsc.system_id = mac
    txsc.port_id = 1
    tx_sak = txsc.saks.add()
    tx_sak.sak = sak
    rxsc = sk.rx.secure_channels.add()
    rxsc.dut_sci_system_id = peer_mac
    rxsc.dut_sci_port_id = 1
    rx_sak = rxsc.saks.add()
    rx_sak.sak = sak
    if xpn:
        tx_sak.ssci = rx_sak.ssci = SSCI
        tx_sak.salt = rx_sak.salt = SALT
    return d, ipv4


def _config(api, b2b_raw_config, engine, cipher="gcm_aes_128"):
    config = b2b_raw_config
    config.flows.clear()
    config.captures.clear()
    p1, p2 = config.ports
    m1, m2 = "00:00:00:00:00:11", "00:00:00:00:00:22"
    _, ip1 = _device(
        config, 1, p1, m1, m2, "10.1.1.1", "10.1.1.2", engine, cipher
    )
    _, ip2 = _device(
        config, 2, p2, m2, m1, "10.1.1.2", "10.1.1.1", engine, cipher
    )
    f = config.flows.flow(name="f1")[-1]
    f.packet.ethernet().ipv4()
    f.tx_rx.device.tx_names = [ip1.name]
    f.tx_rx.device.rx_names = [ip2.name]
    f.size.fixed = 128
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 500
    f.metrics.enable = True
    return config


def _flow_stats(api):
    req = api.metrics_request()
    req.flow.flow_names = ["f1"]
    return api.get_metrics(req).flow_metrics[0]


def _sessions_up(api, kinds=("Macsec", "StaticMacsec")):
    """Read the node status directly: much cheaper than the statistics views,
    which can block for a long time right after the start."""
    ixn = api._ixnetwork
    ethernets = ixn.Topology.find().DeviceGroup.find().Ethernet.find()
    nodes = []
    for kind in kinds:
        nodes += list(getattr(ethernets, kind).find())
    return len(nodes) == 2 and all(
        n.SessionStatus == ["up"] for n in nodes
    )


def _start(api, config, utils, start_capture=False, kinds=("Macsec", "StaticMacsec")):
    """Like utils.start_traffic, but waits for the MACsec sessions to be up
    before transmitting, because traffic is refused while they are not."""
    api.set_config(config)
    if start_capture:
        cs = api.control_state()
        cs.choice = cs.PORT
        cs.port.choice = cs.port.CAPTURE
        cs.port.capture.state = cs.port.capture.START
        api.set_control_state(cs)
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)
    utils.wait_for(
        lambda: _sessions_up(api, kinds), "MACsec sessions to be up",
        timeout_seconds=60,
    )
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)


@pytest.mark.parametrize("engine", ENGINES)
def test_encrypt_decrypt_b2b_traffic(api, b2b_raw_config, utils, engine):
    config = _config(api, b2b_raw_config, engine)
    try:
        _start(api, config, utils)
    except Exception as e:
        # the macsec node is accepted in config, but starting it fails on
        # cards without inline crypto MACsec (e.g. NOVUS10/1GE16DP)
        if engine == "inline_crypto" and "not supported on this port" in str(
            e
        ):
            pytest.skip("ports do not support inline crypto MACsec")
        raise
    utils.wait_for(
        lambda: _flow_stats(api).transmit == "stopped",
        "flow to stop",
        timeout_seconds=60,
    )
    # the flow reports "stopped" before the last counters are published
    utils.wait_for(
        lambda: _flow_stats(api).frames_tx == 500
        and _flow_stats(api).frames_rx == 500,
        "flow counters to settle",
        timeout_seconds=30,
    )
    stats = _flow_stats(api)
    print("flow tx %s rx %s" % (stats.frames_tx, stats.frames_rx))
    assert stats.frames_tx == 500
    assert stats.frames_rx == stats.frames_tx

    req = api.metrics_request()
    req.macsec.secure_entity_names = ["d1", "d2"]
    metrics = api.get_metrics(req).macsec_metrics
    for m in metrics:
        print("macsec %s: %s" % (m.name, m.serialize("dict")))
    if engine == "inline_crypto":
        assert sorted(m.name for m in metrics) == ["d1", "d2"]
        assert all(m.session_state == "up" for m in metrics)


def _ethertype(frame):
    """EtherType of a frame given as a list of bytes, skipping VLAN tags."""
    offset = 12
    while frame[offset : offset + 2] in ([0x81, 0x00], [0x88, 0xA8]):
        offset += 4
    return (frame[offset] << 8) | frame[offset + 1]


@pytest.mark.parametrize("engine", ENGINES)
def test_encrypt_decrypt_b2b_frames_are_encrypted(
    api, b2b_raw_config, utils, engine
):
    """H12: the receiving port sees MACsec frames, not the plain IPv4 flow."""
    config = _config(api, b2b_raw_config, engine)
    cap = config.captures.add()
    cap.name = "c1"
    cap.port_names = [config.ports[1].name]
    cap.format = cap.PCAPNG
    try:
        _start(api, config, utils, start_capture=True)
    except Exception as e:
        if engine == "inline_crypto" and "not supported on this port" in str(
            e
        ):
            pytest.skip("ports do not support inline crypto MACsec")
        raise
    utils.wait_for(
        lambda: _flow_stats(api).frames_tx == 500
        and _flow_stats(api).frames_rx == 500,
        "flow counters to settle",
        timeout_seconds=60,
    )
    cs = api.control_state()
    cs.port.capture.state = cs.port.capture.STOP
    api.set_control_state(cs)

    frames = utils.get_all_captures(api, config)[config.ports[1].name]
    macsec = [f for f in frames if _ethertype(f) == 0x88E5]
    plain = [f for f in frames if _ethertype(f) == 0x0800]
    print(
        "captured %d frames: %d MACsec (0x88e5), %d plain IPv4"
        % (len(frames), len(macsec), len(plain))
    )
    assert len(macsec) >= 500
    assert len(plain) == 0


@pytest.mark.parametrize("engine", ENGINES)
def test_encrypt_decrypt_b2b_sak_mismatch_drops_traffic(
    api, b2b_raw_config, utils, engine
):
    """H7: if the receiver holds a different SAK the flow must not arrive.
    Frames that arrive anyway mean MACsec is not applied to the data."""
    config = _config(api, b2b_raw_config, engine)
    secy = config.devices[1].macsec.ethernet_interfaces[0].secure_entity
    rx_sak = secy.key_generation_protocol.static_key.rx.secure_channels[
        0
    ].saks[0]
    rx_sak.sak = "0123456789abcdef0123456789abcdef"
    try:
        _start(api, config, utils)
    except Exception as e:
        if engine == "inline_crypto" and "not supported on this port" in str(
            e
        ):
            pytest.skip("ports do not support inline crypto MACsec")
        if "Start MACSec on selected Tx ports" in str(e):
            # IxNetwork refuses to transmit when the SecY is not up: the
            # wrong key keeps traffic from flowing
            return
        raise
    utils.wait_for(
        lambda: _flow_stats(api).frames_tx == 500,
        "flow to transmit",
        timeout_seconds=60,
    )
    stats = _flow_stats(api)
    print("sak mismatch: flow tx %s rx %s" % (stats.frames_tx, stats.frames_rx))
    assert stats.frames_rx == 0


@pytest.mark.macsec_hw
def test_per_port_options_are_applied(api, b2b_raw_config, utils):
    """H10: per port options reach Globals.Topology.Macsec and the sessions
    still come up and carry traffic."""
    config = _config(api, b2b_raw_config, "inline_crypto")
    for port in config.ports:
        per_port = config.options.per_port_options.add()
        per_port.port_name = port.name
        protocol = per_port.protocols.add()
        protocol.choice = "macsec"
        protocol.macsec.validate_frames.choice = "check"
        acceleration = protocol.macsec.hardware_acceleration
        acceleration.choice = "inline_crypto"
        inline = acceleration.inline_crypto
        inline.rx_sectag_offset = 16
        inline.rx_sc_identifying_field = "source_mac"
        inline.max_ca_count = "sixteen"
        inline.type_of_ca.choice = "pairwise_ca"
    _start(api, config, utils)
    utils.wait_for(
        lambda: _flow_stats(api).frames_tx == 500
        and _flow_stats(api).frames_rx == 500,
        "flow counters to settle",
        timeout_seconds=60,
    )
    glob = api._ixnetwork.Globals.Topology.find().Macsec.find()
    # read only in IxNetwork, derived from the configuration
    assert glob.KeyGenerationMode == "staticKeyGenerationMode"
    assert set(glob.RxSecTagOffset.Values) == {"16"}
    assert set(glob.MaxCaCount.Values) == {"macsecmaxcasixteen"}
    assert set(glob.TypeOfCa.Values) == {"pairwiseca"}
    assert set(glob.RxScIdentifyingField.Values) == {
        "rxscidentifyingfieldsrcmac"
    }
    assert set(glob.MacsecValidation.Values) == {"check"}


def test_per_port_strict_validate_frames_rejected(api, b2b_raw_config):
    """strict is not offered by IxNetwork: 400 before any REST call."""
    config = _config(api, b2b_raw_config, "inline_crypto")
    per_port = config.options.per_port_options.add()
    per_port.port_name = config.ports[0].name
    protocol = per_port.protocols.add()
    protocol.choice = "macsec"
    protocol.macsec.validate_frames.choice = "strict"
    with pytest.raises(Exception) as err:
        api.set_config(config)
    assert "strict" in str(err.value)


def _to_mka(config):
    """Switch both devices of _config() from static key to MKA with a PSK."""
    cak_name = "F123456789ABCDEF0123456789ABCDEFF123456789ABCDEF0123456789ABCD01"
    cak_value = "F123456789ABCDEF0123456789ABCD01"
    for device in config.devices:
        iface = device.macsec.ethernet_interfaces[0]
        secy = iface.secure_entity
        mac = [e for e in device.ethernets if e.name == iface.eth_name][0].mac
        secy.key_generation_protocol.choice = "mka"
        kay = secy.key_generation_protocol.mka
        kay.name = "mka_" + device.name
        kay.basic.key_derivation_function = "aes_cmac_128"
        # the key chain starts at this time, so use the current one
        now = datetime.datetime.now(datetime.timezone.utc)
        kay.basic.psk_chain_start_time.choice = "utc"
        utc = kay.basic.psk_chain_start_time.utc
        utc.day, utc.month, utc.year = now.day, now.month, now.year
        utc.hour, utc.minute, utc.second = now.hour, now.minute, now.second
        kay.basic.key_source.choice = "psk"
        psk = kay.basic.key_source.psks.add()
        psk.cak_name = cak_name
        psk.cak_value = cak_value
        psk.start_offset_time.hh = 0
        psk.start_offset_time.mm = 0
        # the key must be valid for a while (a zero length key never starts
        # MKA)
        psk.end_offset_time.hh = 22
        psk.end_offset_time.mm = 0
        sc = kay.tx.secure_channels.add()
        sc.name = "txsc_" + device.name
        sc.system_id = mac


def _mka_metrics(api):
    req = api.metrics_request()
    req.mka.peer_names = ["d1", "d2"]
    return api.get_metrics(req).mka_metrics


@pytest.mark.macsec_hw
def test_hardware_mka_b2b_traffic(api, b2b_raw_config, utils):
    """H4: MKA with a PSK on two hardware SecYs, then protected traffic. The
    static SAK pools are not written, the keys come from MKA."""
    config = _config(api, b2b_raw_config, "inline_crypto")
    _to_mka(config)
    cap = config.captures.add()
    cap.name = "c1"
    cap.port_names = [config.ports[1].name]
    cap.format = cap.PCAPNG
    _start(api, config, utils, start_capture=True)
    utils.wait_for(
        lambda: all(m.live_peer_count == 1 for m in _mka_metrics(api)),
        "MKA live peers",
        timeout_seconds=60,
    )
    utils.wait_for(
        lambda: _flow_stats(api).frames_tx == 500
        and _flow_stats(api).frames_rx == 500,
        "flow counters to settle",
        timeout_seconds=60,
    )
    cs = api.control_state()
    cs.port.capture.state = cs.port.capture.STOP
    api.set_control_state(cs)
    frames = utils.get_all_captures(api, config)[config.ports[1].name]
    macsec = [f for f in frames if _ethertype(f) == 0x88E5]
    plain = [f for f in frames if _ethertype(f) == 0x0800]
    print("captured %d MACsec, %d plain IPv4" % (len(macsec), len(plain)))
    assert len(macsec) >= 500 and len(plain) == 0


@pytest.mark.macsec_hw
def test_protocol_stop_and_start_cycles_hardware_sessions(
    api, b2b_raw_config, utils
):
    """H13: protocol.all stop brings the hardware sessions down, start brings
    them up again."""
    config = _config(api, b2b_raw_config, "inline_crypto")
    _start(api, config, utils)
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.STOP
    api.set_control_state(cs)
    utils.wait_for(
        lambda: not _sessions_up(api), "sessions to go down", timeout_seconds=60
    )
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)
    utils.wait_for(
        lambda: _sessions_up(api), "sessions to come up", timeout_seconds=60
    )


def test_no_encapsulation_mka_b2b(api, b2b_raw_config, utils):
    """H16: MKA only (no MACsec data plane) on two devices, the MKA sessions
    come up and see one live peer."""
    config = _config(api, b2b_raw_config, "none")
    _to_mka(config)
    for device in config.devices:
        secy = device.macsec.ethernet_interfaces[0].secure_entity
        secy.data_plane.choice = "no_encapsulation"
    config.flows.clear()
    _start_protocols = _start  # same start sequence, no flow is configured
    api.set_config(config)
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)
    utils.wait_for(
        lambda: _sessions_up(api, ("Mka",)),
        "MKA sessions to be up",
        timeout_seconds=60,
    )
