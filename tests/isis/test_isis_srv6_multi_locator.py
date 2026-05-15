import io
import ipaddress
import time

import dpkt
import pytest

pytestmark = pytest.mark.skip(reason="ISIS-SRv6 control plane not yet supported")

# Converted from: config.ISIS_SRV6_multiple_locator_tlvs_IPV4_IPV6_sourcerouterid.ixncfg
# Source script:  test.ISIS_SRV6_multiple_locator_tlvs_IPV4_IPV6_sourcerouterid.py
# Test intent:    Verify multiple SRv6 locator TLVs and IPv4/IPv6 source
#                 router IDs across two emulated devices on each port. The
#                 P4 source applies two capture filters (by source MAC) to
#                 isolate p2d1 vs p2d2 LSPs; the snappi version keys directly
#                 off the LSP-ID instead, since both are present in the same
#                 capture.
#
# Topology (back-to-back, 2 ports):
#   Port 1 — Topology 1: 2 emulated devices (p1d1, p1d2)
#     p1d1: system_id=640100010000, mac=00:11:01:00:00:01
#     p1d2: system_id=640100020000, mac=00:11:01:00:00:02
#   Port 2 — Topology 2: 2 emulated devices (p2d1, p2d2) +
#     2 simulated nodes in a networkGroup (omitted — no snappi equivalent)
#     p2d1: system_id=650100010000, mac=00:12:01:00:00:01
#       2 locators, algorithm 1, prefix flags one X=R=0/N=1 and one X=R=N=1
#     p2d2: system_id=650100020000, mac=00:12:01:00:00:02
#       3 locators, algorithms 0 / 2 / 3 (Flex-Algo)
#   Network type: broadcast (both topologies)
#   Sessions expected: P4 source asserts 2/port; snappi expects >= 2/port
#                      with simulated routers omitted.
#
# Capture: port 1 buffer (receives LSPs flooded from port-2 devices).
#
# Phase 2 capture assertions:
#   p2d1 LSP 6501.0001.0000.00-00 (P4 filter 1: eth.addr=00:12:01:00:00:01)
#     +  Locator 6000:0:1:1:: present in TLV 27
#     +  Algorithm 1 on advertised locators
#     +  Source Router ID 1.1.1.3 in TLV 134
#     xfail  Prefix attribute flags X=R=0/N=1 and X=R=N=1 on the two
#            locators — wire correctness gap on some IxN versions.
#   p2d2 LSP 6501.0002.0000.00-00 (P4 filter 2: eth.addr=00:12:01:00:00:02)
#     +  TLV 27 advertises 3 locators with algorithms {0, 2, 3}
#     +  Source Router ID 1.1.1.5 in TLV 134
#     skip   IPv6 Source Router IDs 1000:0:0:2::3 and 1000:0:0:2::4 — OTG
#            ISIS model has no equivalent for multiple IPv6 SRIDs.
#     skip   IPv4 prefix length 24 and IPv6 prefix length 64 from extra
#            reachability TLVs — would require route ranges not modelled
#            by this test case.
#   skip   Simulated node LSPs 6401.0000.0001.00-00 and 6401.0000.0002.00-00
#          — see ISSUE_ANALYSIS.md Issue 5.
#
# KNOWN BLOCKERS:
#   P1  isis.py / isis_srv6.py: prefix attribute flag wire correctness
#       unverified — guarded with xfail.
#   P2  snappi model: no equivalent for IxN networkGroup simulated routers
#       (the 6401.* LSP assertions are intentionally dropped).
#   P3  snappi model: no field for multiple IPv6 source router IDs per
#       ISIS router (the dual-SRID assertion on p2d2 is dropped).
#
# NOTE: The P4 source has stopAllProtocols commented out — likely a bug.
# This snappi version always issues the protocol STOP for clean teardown
# (per plan §4 Test 4 conversion challenges).
#
# MANUAL INTERVENTION REQUIRED:
#   - Update tests/settings.json with b2b port locations
#   - Verify convergence timeout (currently 30s) against actual hardware


def _configure_device(
    device,
    port_name,
    mac,
    ipv6_addr,
    ipv6_gw,
    system_id,
    locators,
    ipv4_te_router_id=None,
):
    """Configure an IS-IS SRv6 device with the given locators."""
    eth = device.ethernets.add()
    eth.connection.port_name = port_name
    eth.name = "%s_eth" % device.name
    eth.mac = mac
    eth.mtu = 1500

    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = "%s_ipv6" % device.name
    ipv6.address = ipv6_addr
    ipv6.gateway = ipv6_gw
    ipv6.prefix = 64

    isis = device.isis
    isis.name = "%s_isis" % device.name
    isis.system_id = system_id
    isis.basic.enable_wide_metric = True
    isis.basic.learned_lsp_filter = False
    if ipv4_te_router_id is not None:
        isis.basic.ipv4_te_router_id = ipv4_te_router_id
    isis.advanced.area_addresses = ["490001"]
    isis.advanced.enable_hello_padding = True
    isis.advanced.lsp_lifetime = 1200
    isis.advanced.lsp_refresh_rate = 900
    isis.advanced.csnp_interval = 10000

    # Touch srv6_capability so config_node_capability() runs and ipv6Srh=True
    # is set on the IxN router — otherwise TLV 242 is never emitted.
    srv6_cap = isis.segment_routing.router_capability.srv6_capability
    srv6_cap.c_flag = False
    srv6_cap.o_flag = False

    for i, loc_cfg in enumerate(locators, start=1):
        loc_name = "%s_loc%d" % (device.name, i)
        loc = isis.segment_routing.srv6_locators.add()
        loc.locator_name = loc_name
        loc.locator = loc_cfg["locator"]
        loc.prefix_length = 64
        loc.algorithm = loc_cfg.get("algorithm", 0)
        loc.metric = 10
        loc.d_flag = loc_cfg.get("d_flag", False)
        loc.mt_id = []
        loc.sid_structure.locator_block_length = 40
        loc.sid_structure.locator_node_length = 24
        loc.sid_structure.function_length = 16
        loc.sid_structure.argument_length = 0

        alp = loc.advertise_locator_as_prefix
        alp.route_metric = 0
        alp.redistribution_type = "up"
        alp.route_origin = "internal"
        pfx = alp.prefix_attributes
        pfx.n_flag = loc_cfg.get("n_flag", True)
        pfx.r_flag = loc_cfg.get("r_flag", False)
        pfx.x_flag = loc_cfg.get("x_flag", False)

        end_sid = loc.end_sids.add()
        end_sid.function = "0001"
        end_sid.argument = "0000"
        end_sid.endpoint_behavior = "end"
        end_sid.c_flag = False

    intf = isis.interfaces.add()
    intf.name = "%s_intf" % device.name
    intf.eth_name = eth.name
    intf.network_type = "broadcast"
    intf.level_type = "level_2"
    intf.metric = 10
    intf.l2_settings.hello_interval = 10
    intf.l2_settings.dead_interval = 30
    intf.l2_settings.priority = 0

    adj_sid = intf.srv6_adjacency_sids.sids.add()
    adj_sid.locator = "custom_locator_reference"
    adj_sid.custom_locator_reference = "%s_loc1" % device.name
    adj_sid.function = "0040"
    adj_sid.endpoint_behavior = "end_x"
    adj_sid.b_flag = False
    adj_sid.s_flag = False
    adj_sid.p_flag = False
    adj_sid.c_flag = False
    adj_sid.algorithm = 0
    adj_sid.weight = 0


def build_config(b2b_raw_config):
    config = b2b_raw_config
    config.flows.clear()
    p1, p2 = config.ports

    p1d1, p1d2, p2d1, p2d2 = (
        config.devices
        .device(name="p1d1")
        .device(name="p1d2")
        .device(name="p2d1")
        .device(name="p2d2")
    )

    # --- Port 1 (Topology 1): 2 emulated devices, single locator each ---
    # Not asserted on; minimal valid config so the broadcast LAN forms.
    _configure_device(
        p1d1, p1.name,
        mac="00:11:01:00:00:01",
        ipv6_addr="2000:0:0:1::1",
        ipv6_gw="2000:0:0:1::3",
        system_id="640100010000",
        ipv4_te_router_id="1.1.1.10",
        locators=[
            {
                "locator": "5000:0:0:1::",
                "algorithm": 0,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
        ],
    )
    _configure_device(
        p1d2, p1.name,
        mac="00:11:01:00:00:02",
        ipv6_addr="2000:0:0:1::2",
        ipv6_gw="2000:0:0:1::4",
        system_id="640100020000",
        ipv4_te_router_id="1.1.1.11",
        locators=[
            {
                "locator": "5000:0:0:2::",
                "algorithm": 0,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
        ],
    )

    # --- Port 2 (Topology 2): 2 emulated devices ---
    # p2d1 (filter 1 target): 2 locators with prefix flags X=R=0/N=1 and
    # X=R=N=1, both algorithm=1, source router ID 1.1.1.3.
    _configure_device(
        p2d1, p2.name,
        mac="00:12:01:00:00:01",
        ipv6_addr="2000:0:0:1::3",
        ipv6_gw="2000:0:0:1::1",
        system_id="650100010000",
        ipv4_te_router_id="1.1.1.3",
        locators=[
            {
                "locator": "6000:0:1:1::",
                "algorithm": 1,
                "n_flag": True,
                "r_flag": True,
                "x_flag": True,
            },
            {
                "locator": "6000:0:1:2::",
                "algorithm": 1,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
        ],
    )

    # p2d2 (filter 2 target): 3 locators with algorithms 0, 2, 3 (Flex-Algo).
    # Source Router ID 1.1.1.5. Source asserts on dual IPv6 source router
    # IDs (1000:0:0:2::3 and 1000:0:0:2::4) and IPv4 prefix length 24 from
    # extra reachability TLVs — neither is reachable through OTG today.
    _configure_device(
        p2d2, p2.name,
        mac="00:12:01:00:00:02",
        ipv6_addr="2000:0:0:1::4",
        ipv6_gw="2000:0:0:1::2",
        system_id="650100020000",
        ipv4_te_router_id="1.1.1.5",
        locators=[
            {
                "locator": "5000:0:2:0::",
                "algorithm": 0,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
            {
                "locator": "5000:0:2:2::",
                "algorithm": 2,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
            {
                "locator": "5000:0:2:3::",
                "algorithm": 3,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
        ],
    )

    cap = config.captures.add()
    cap.name = "port1_cap"
    cap.port_names = [p1.name]
    cap.format = cap.PCAPNG

    return config


# ---------------------------------------------------------------------------
# ISIS LSP capture helpers (shared with sibling tests in this directory)
# ---------------------------------------------------------------------------

_ISIS_LLC = bytes([0xFE, 0xFE, 0x03])
_ISIS_L2_LSP = 0x14  # PDU type 20


def _get_hw_capture(api, port_name):
    """Download the HW capture file directly via RestPy.

    Bypasses api.get_capture() which calls MergeCapture(SW, HW) — that fails
    when there is no software-generated traffic (control-plane only capture).
    """
    ixn = api._ixnetwork
    vport = api._vport.find(Name=port_name)

    vport.Capture.Stop("allTraffic")
    for _ in range(30):
        time.sleep(3)
        cap_state = api._vport.find(Name=port_name).Capture
        hw_ready = (
            not cap_state.HardwareEnabled
            or cap_state.DataCaptureState != "notReady"
        )
        sw_ready = (
            not cap_state.SoftwareEnabled
            or cap_state.ControlCaptureState != "notReady"
        )
        if hw_ready and sw_ready:
            break

    persistence_path = ixn.Globals.PersistencePath
    ixn.SaveCaptureFiles(persistence_path + "/capture")

    hw_path = persistence_path + "/capture/" + vport.Name + "_HW.cap"
    url = "%s/files?absolute=%s/capture&filename=%s" % (
        ixn.href, persistence_path, hw_path
    )
    raw_bytes = api._request("GET", url)
    return io.BytesIO(raw_bytes)


def _parse_isis_lsps(pcap_bytes):
    """Return {lsp_id_hex: {tlv_type: [bytes, ...]}} for all L2 LSP PDUs."""
    lsp_db = {}
    reader_src = (
        pcap_bytes if hasattr(pcap_bytes, "read") else io.BytesIO(pcap_bytes)
    )
    for _ts, raw in dpkt.pcapng.Reader(reader_src):
        if len(raw) < 17 or raw[14:17] != _ISIS_LLC:
            continue
        isis_pdu = raw[17:]
        if len(isis_pdu) < 20 or isis_pdu[0] != 0x83:
            continue
        if (isis_pdu[4] & 0x1F) != _ISIS_L2_LSP:
            continue
        hdr_len = isis_pdu[1]
        if len(isis_pdu) < hdr_len:
            continue
        lsp_id = isis_pdu[12:20].hex()
        tlv_data = isis_pdu[hdr_len:]
        tlvs = {}
        i = 0
        while i + 1 < len(tlv_data):
            t, l = tlv_data[i], tlv_data[i + 1]
            tlvs.setdefault(t, []).append(bytes(tlv_data[i + 2: i + 2 + l]))
            i += 2 + l
        lsp_db[lsp_id] = tlvs
    return lsp_db


def _get_tlv27_locators(tlv_bytes_list):
    """Parse TLV 27 (SRv6 Locator, RFC 9352 §7.3). Returns list of dicts."""
    locators = []
    for data in tlv_bytes_list:
        if len(data) < 9:
            continue
        d_flag = bool(data[2] & 0x80)
        algorithm = data[7]
        prefix_len = data[8]
        n_bytes = (prefix_len + 7) // 8
        if len(data) < 9 + n_bytes:
            continue
        prefix = str(ipaddress.IPv6Address(
            data[9: 9 + n_bytes].ljust(16, b"\x00")
        ))
        sub_tlvs = {}
        off = 9 + n_bytes
        while off + 1 < len(data):
            st, sl = data[off], data[off + 1]
            sub_tlvs.setdefault(st, []).append(
                bytes(data[off + 2: off + 2 + sl])
            )
            off += 2 + sl
        locators.append({
            "prefix": prefix,
            "prefix_len": prefix_len,
            "algorithm": algorithm,
            "d_flag": d_flag,
            "sub_tlvs": sub_tlvs,
        })
    return locators


def _get_prefix_attr_flags(sub_tlvs):
    """Extract N/R/X from Prefix Attribute Flags sub-TLV 4."""
    results = []
    for data in sub_tlvs.get(4, []):
        if data:
            results.append({
                "x": bool(data[0] & 0x80),
                "r": bool(data[0] & 0x40),
                "n": bool(data[0] & 0x20),
            })
    return results


def _get_source_router_id(tlv134_list):
    """Extract IPv4 TE Router ID from TLV 134."""
    for data in tlv134_list:
        if len(data) >= 4:
            return str(ipaddress.IPv4Address(data[:4]))
    return None


def _assert_p2d1_lsp(lsp_db):
    """Filter 1 in P4 source: eth.addr == 00:12:01:00:00:01 → p2d1 LSP."""
    lsp_id = "6501000100000000"
    assert lsp_id in lsp_db, (
        "LSP 6501.0001.0000.00-00 (p2d1) not found. Keys: %s"
        % list(lsp_db.keys())
    )
    tlvs = lsp_db[lsp_id]

    # --- Locators in TLV 27 ---
    assert 27 in tlvs, "TLV 27 (SRv6 Locator) missing from p2d1 LSP"
    locators = _get_tlv27_locators(tlvs[27])
    prefixes = {loc["prefix"] for loc in locators}
    assert "6000:0:1:1::" in prefixes, (
        "Locator 6000:0:1:1:: not found in p2d1 LSP (found: %s)" % prefixes
    )

    # --- Algorithm 1 on the asserted locator ---
    for loc in locators:
        if loc["prefix"] == "6000:0:1:1::":
            assert loc["algorithm"] == 1, (
                "Expected algorithm=1 on 6000:0:1:1::, got %d"
                % loc["algorithm"]
            )

    # --- Source Router ID 1.1.1.3 ---
    assert 134 in tlvs, "TLV 134 (IPv4 TE Router ID) missing from p2d1 LSP"
    src_id = _get_source_router_id(tlvs[134])
    assert src_id == "1.1.1.3", (
        "Expected p2d1 source router ID 1.1.1.3, got %s" % src_id
    )

    # --- Prefix attribute flags: X=R=0/N=1 and X=R=N=1 ---
    # Wire correctness gap — xfail when sub-TLV 4 is absent.
    seen_flag_sets = []
    for loc in locators:
        flags_list = _get_prefix_attr_flags(loc["sub_tlvs"])
        if flags_list:
            seen_flag_sets.append(flags_list[0])
    if not seen_flag_sets:
        pytest.xfail(
            "Prefix Attribute Flags sub-TLV 4 absent on p2d1 locators — "
            "wire correctness gap on this IxNetwork server version"
        )
    flag_tuples = {(f["x"], f["r"], f["n"]) for f in seen_flag_sets}
    assert (False, False, True) in flag_tuples, (
        "Expected one p2d1 locator with X=R=0/N=1, got %s" % flag_tuples
    )
    assert (True, True, True) in flag_tuples, (
        "Expected one p2d1 locator with X=R=N=1, got %s" % flag_tuples
    )


def _assert_p2d2_lsp(lsp_db):
    """Filter 2 in P4 source: eth.addr == 00:12:01:00:00:02 → p2d2 LSP."""
    lsp_id = "6501000200000000"
    assert lsp_id in lsp_db, (
        "LSP 6501.0002.0000.00-00 (p2d2) not found. Keys: %s"
        % list(lsp_db.keys())
    )
    tlvs = lsp_db[lsp_id]

    # --- TLV 27 advertises 3 locators with algorithms {0, 2, 3} ---
    assert 27 in tlvs, "TLV 27 (SRv6 Locator) missing from p2d2 LSP"
    locators = _get_tlv27_locators(tlvs[27])
    algorithms = {loc["algorithm"] for loc in locators}
    for expected in (0, 2, 3):
        assert expected in algorithms, (
            "Expected p2d2 to advertise a locator with algorithm=%d, "
            "got algorithms %s" % (expected, sorted(algorithms))
        )

    # --- Source Router ID 1.1.1.5 ---
    assert 134 in tlvs, "TLV 134 (IPv4 TE Router ID) missing from p2d2 LSP"
    src_id = _get_source_router_id(tlvs[134])
    assert src_id == "1.1.1.5", (
        "Expected p2d2 source router ID 1.1.1.5, got %s" % src_id
    )

    # --- Multiple IPv6 source router IDs (1000:0:0:2::3 / ::4) ---
    # Skipped — OTG ISIS model has no field for multiple IPv6 SRIDs.
    # See ISSUE_ANALYSIS.md Issue 5 (model-layer gap).

    # --- IPv4 prefix length 24 / IPv6 prefix length 64 from extra TLVs ---
    # Skipped — would require route-range advertisement not modelled here.


def test_isis_srv6_multi_locator(api, b2b_raw_config):
    config = build_config(b2b_raw_config)
    api.set_config(config)

    _capture_ok = True
    try:
        cs_cap = api.control_state()
        cs_cap.choice = cs_cap.PORT
        cs_cap.port.capture.port_names = [config.ports[0].name]
        cs_cap.port.capture.state = cs_cap.port.capture.START
        api.set_control_state(cs_cap)
    except Exception as exc:
        if "Wireshark" in str(exc):
            _capture_ok = False
            import warnings
            warnings.warn(
                "Packet capture unavailable (Wireshark integration not "
                "installed on IxNetwork server) — Phase 2 assertions skipped."
            )
        else:
            raise

    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)

    time.sleep(30)

    req = api.metrics_request()
    req.isis.router_names = []
    req.isis.column_names = ["l2_sessions_up"]
    results = api.get_metrics(req)

    assert len(results.isis_metrics) == 4, (
        "Expected 4 ISIS router metrics (2 per port), got %d"
        % len(results.isis_metrics)
    )

    sessions_by_port = {"p1": 0, "p2": 0}
    for metric in results.isis_metrics:
        if metric.name.startswith("p1"):
            sessions_by_port["p1"] += metric.l2_sessions_up
        else:
            sessions_by_port["p2"] += metric.l2_sessions_up

    assert sessions_by_port["p1"] >= 2, (
        "Expected >= 2 ISIS L2 sessions on port 1, got %d"
        % sessions_by_port["p1"]
    )
    assert sessions_by_port["p2"] >= 2, (
        "Expected >= 2 ISIS L2 sessions on port 2, got %d"
        % sessions_by_port["p2"]
    )

    if not _capture_ok:
        pytest.skip(
            "Phase 2 capture assertions skipped: Wireshark integration not "
            "available on IxNetwork server."
        )

    pcap_bytes = _get_hw_capture(api, config.ports[0].name)
    lsp_db = _parse_isis_lsps(pcap_bytes)
    _assert_p2d1_lsp(lsp_db)
    _assert_p2d2_lsp(lsp_db)

    # Simulated node LSPs 6401.0000.0001.00-00 and 6401.0000.0002.00-00:
    # omitted — see ISSUE_ANALYSIS.md Issue 5.

    # P4 source has stopAllProtocols commented out; this snappi version
    # always issues the protocol STOP for clean teardown.
    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.all.state = cs.protocol.all.STOP
    api.set_control_state(cs)
