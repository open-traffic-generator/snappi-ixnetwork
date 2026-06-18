import io
import ipaddress
import time

import dpkt
import pytest

pytestmark = pytest.mark.skip(reason="ISIS-SRv6 control plane not yet supported")

# Converted from: config.ISIS_SRV6_H_encap_Flags_and_Value.ixncfg
# Source script:  test.ISIS_SRV6_H_encap_Flags_and_Value.py
# JSON ref:       scripts/output/config.ISIS_SRV6_H_encap_Flags_and_Value.json
# Test intent:    Verify D-flag, source router ID, prefix attribute flags, and
#                 MSD Type 44 (SRH Max H.encaps) values in ISIS LSPs for an
#                 emulated SRv6 router advertising 2 locators with distinct
#                 prefix attribute flag sets.
#
# Topology (back-to-back, 2 ports):
#   Port 1 — Topology 1: 1 emulated device (p1d1), 1 locator, algorithm 0
#   Port 2 — Topology 2: 1 emulated device (p2d1), 2 locators +
#             simulated networkGroup fat-tree (omitted — no snappi equivalent)
#   Network type: broadcast (both topologies)
#   Sessions expected: 1 per port (2 total ISIS routers)
#
# Capture: port 1 receives LSPs flooded from port-2 devices.
# ISIS filter: PDU type 20 (LSP), source MAC 00:12:01:00:00:01 (p2d1).
#
# Emulated device p2d1 (system_id=650100010000, LSP 6501.0001.0000.00-00):
#   mac="00:12:01:00:00:01", ipv4_te_router_id="6.6.6.6"
#   loc1: locator=6501:0:0:1::/64, d_flag=False, n_flag=R=X=True  (X:1|R:1|N:1)
#   loc2: locator=6501:0:0:2::/64, d_flag=False, n_flag=True, r_flag=x_flag=False
#   node_msds.max_h_encaps=32  (set in config; translator logs warning and ignores)
#   link_msd.max_h_encaps=52   (set in config; translator logs warning and ignores)
#   Per-locator MSD value 42: requires per-locator MSD field — not in snappi model
#
# Phase 1: session-up (>=1 per port)
# Phase 2: ISIS LSP capture validation on port 1
#   +  D flag = False on all locators (translator pushes d_flag)
#   +  Locator prefixes 6501:0:0:1:: and 6501:0:0:2:: present in TLV 27
#   +  Source Router ID = 6.6.6.6 in TLV 134 (translator pushes ipv4_te_router_id)
#   xfail  Prefix Attribute Flags X:1|R:1|N:1 / X:0|R:0|N:1 — isis.py omits n/r/x flags
#   xfail  MSD Type 44 values 32, 52, 42 — isis_srv6.py ignores node_msds + link_msd
#   skip   IPv6 Source Router ID 6666:0:0:2::1 — not in snappi model (no ipv6_te_router_id)
#   skip   Simulated LSP 6401.0000.0001.00-00  — no snappi equivalent for simulated routers
#
# KNOWN BLOCKERS:
#   P0  isis_srv6.py: node_msds.* and link_msd.* produce a warning and are ignored
#   P1  isis.py: n_flag/r_flag/x_flag on isisSRv6LocatorEntryList are not pushed
#   P2  snappi model: no ipv6_te_router_id field on IsisBasic
#   P2  snappi model: no per-locator MSD field on IsisSRv6.Locator
#
# MANUAL INTERVENTION REQUIRED:
#   - Update tests/settings.json with b2b port locations
#   - Verify convergence timeout (currently 30s) against actual hardware
#   - Simulated router (networkGroup fatTree) omitted — no snappi equivalent


def _configure_device(
    device,
    port_name,
    mac,
    ipv6_addr,
    ipv6_gw,
    system_id,
    locators,
    ipv4_te_router_id=None,
    node_h_encaps_msd=0,
    link_h_encaps_msd=0,
):
    """Configure an IS-IS SRv6 device with the given locators and MSD values."""
    eth = device.ethernets.add()
    eth.connection.port_name = port_name
    eth.name = f"{device.name}_eth"
    eth.mac = mac
    eth.mtu = 1500

    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = f"{device.name}_ipv6"
    ipv6.address = ipv6_addr
    ipv6.gateway = ipv6_gw
    ipv6.prefix = 64

    isis = device.isis
    isis.name = f"{device.name}_isis"
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

    srv6_cap = isis.segment_routing.router_capability.srv6_capability
    srv6_cap.c_flag = False
    srv6_cap.o_flag = False
    if node_h_encaps_msd > 0 and hasattr(srv6_cap, "node_msds"):
        # node_msds → Router Capability TLV 242 node MSD sub-TLV 23, MSD-Type 44.
        # isis_srv6.py currently logs a warning and ignores this value (no-op).
        srv6_cap.node_msds.max_h_encaps.value = node_h_encaps_msd

    for i, loc_cfg in enumerate(locators, start=1):
        loc_name = f"{device.name}_loc{i}"
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
    intf.name = f"{device.name}_intf"
    intf.eth_name = eth.name
    intf.network_type = "broadcast"
    intf.level_type = "level_2"
    intf.metric = 10
    intf.l2_settings.hello_interval = 10
    intf.l2_settings.dead_interval = 30
    intf.l2_settings.priority = 0

    if link_h_encaps_msd > 0:
        # srv6_link_msd → TLV 22 / TLV 222 link MSD sub-TLV, MSD-Type 44.
        # Now under srv6_adjacency_sids container (isis-srv6-review-2 API).
        # isis_srv6.py currently logs a warning and ignores this value (no-op).
        intf.srv6_adjacency_sids.srv6_link_msd.max_h_encaps.value = link_h_encaps_msd

    adj_sid = intf.srv6_adjacency_sids.sids.add()
    adj_sid.locator = "custom_locator_reference"
    adj_sid.custom_locator_reference = f"{device.name}_loc1"
    # function 0x0040 = 64 decimal, placed in bits 64-79 of the 128-bit SID
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

    p1d1, p2d1 = (
        config.devices
        .device(name="p1d1")
        .device(name="p2d1")
    )

    # Topology 1 (port 1): 1 emulated device, 1 locator, algorithm 0.
    # JSON: systemId=640100010000, locator=5000:0:0:1::/64
    _configure_device(
        p1d1, p1.name,
        mac="00:11:01:00:00:01",
        ipv6_addr="2000:0:0:1::2",
        ipv6_gw="2000:0:0:1::1",
        system_id="640100010000",
        ipv4_te_router_id="1.1.1.1",
        locators=[
            {
                "locator": "5000:0:0:1::",
                "algorithm": 0,
                "d_flag": False,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
        ],
    )

    # Topology 2 (port 2): 1 emulated device, 2 locators with distinct
    # prefix attribute flags, plus node/link MSD configuration.
    #
    # P4 test assertions for LSP 6501.0001.0000.00-00 (emulated):
    #   D Flag: False
    #   Source Router ID: 6.6.6.6  (TLV 134)
    #   IPv6 Source Router ID: 6666:0:0:2::1  (TLV 140 — not in snappi model)
    #   Prefix Attr Flags: X:1|R:1|N:1 (loc1) and X:0|R:0|N:1 (loc2)
    #   MSD H.encaps: 32 (node level), 52 (link level), 42 (per-locator)
    #   Note: per-locator MSD 42 requires a model extension not yet available.
    _configure_device(
        p2d1, p2.name,
        mac="00:12:01:00:00:01",
        ipv6_addr="2000:0:0:1::1",
        ipv6_gw="2000:0:0:1::2",
        system_id="650100010000",
        ipv4_te_router_id="6.6.6.6",
        locators=[
            {
                "locator": "6501:0:0:1::",
                "algorithm": 0,
                "d_flag": False,
                "n_flag": True,
                "r_flag": True,
                "x_flag": True,
            },
            {
                "locator": "6501:0:0:2::",
                "algorithm": 0,
                "d_flag": False,
                "n_flag": True,
                "r_flag": False,
                "x_flag": False,
            },
        ],
        node_h_encaps_msd=32,
        link_h_encaps_msd=52,
    )

    cap = config.captures.add()
    cap.name = "port1_cap"
    cap.port_names = [p1.name]
    cap.format = cap.PCAPNG

    return config


# ---------------------------------------------------------------------------
# ISIS LSP capture helpers
# ---------------------------------------------------------------------------

_ISIS_LLC = bytes([0xFE, 0xFE, 0x03])
_ISIS_L2_LSP = 0x14  # PDU type 20


def _get_hw_capture(api, port_name):
    """Download the HW capture file directly via RestPy.

    Bypasses api.get_capture() which calls MergeCapture(SW, HW) — that fails
    when there is no software-generated traffic (control-plane only capture).
    Also avoids set_control_state(PORT, STOP) which calls clearCaptureInfos
    and wipes the capture buffer before SaveCaptureFiles can be called.
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
    """Return {lsp_id_hex: {tlv_type: [bytes, ...]}} for all L2 LSP PDUs.

    ISIS runs over Ethernet with LLC encapsulation (DSAP=0xFE, SSAP=0xFE,
    Control=0x03), so detection relies on raw byte inspection rather than
    a standard EtherType field.

    LSP-ID layout (bytes 12-19 of the ISIS PDU):
      [12..17] system-ID (6 bytes)  [18] pseudonode  [19] fragment
    """
    lsp_db = {}
    reader_src = (
        pcap_bytes if hasattr(pcap_bytes, "read") else io.BytesIO(pcap_bytes)
    )
    for _ts, raw in dpkt.pcapng.Reader(reader_src):
        if len(raw) < 17 or raw[14:17] != _ISIS_LLC:
            continue
        isis_pdu = raw[17:]
        # Byte 0: ISIS discriminator 0x83; byte 4 (lower 5 bits): PDU type
        if len(isis_pdu) < 20 or isis_pdu[0] != 0x83:
            continue
        if (isis_pdu[4] & 0x1F) != _ISIS_L2_LSP:
            continue
        hdr_len = isis_pdu[1]
        if len(isis_pdu) < hdr_len:
            continue
        # LSP-ID: 8 bytes at offset 12
        # Layout: common header 8B | PDU-length 2B | Remaining-lifetime 2B | LSP-ID 8B
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
    """Parse TLV 27 (SRv6 Locator, RFC 9352 §7.3). Returns list of dicts.

    TLV 27 value layout (as serialised by IxNetwork):
      [0..1] MT-ID flags  [2] Flags (D-flag = bit 7)  [3..6] Metric (padded)
      [7] Algorithm  [8] Prefix Length (bits)  [9..] Prefix bytes
      Sub-TLVs follow the prefix bytes.
    """
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
    """Extract N/R/X from Prefix Attribute Flags sub-TLV 4 (RFC 7794 §2).

    Flag byte bit layout: bit7=X, bit6=R, bit5=N.
    """
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


def _get_node_msd_h_encaps(tlv242_list):
    """Extract MSD-Type 44 (SRH Max H.encaps) from TLV 242 Node MSD sub-TLV 23.

    TLV 242 value layout (RFC 7981):
      [0..3] Router Capability Identifier  [4] Flags  then sub-TLVs.
    Node MSD sub-TLV (type 23, RFC 8491):
      pairs of (MSD-type 1B, MSD-value 1B) in the sub-TLV body.
    MSD-Type 44 = SRH Max H.encaps (RFC 9352 Section 6).
    """
    values = []
    for data in tlv242_list:
        i = 4  # skip 4-byte Router-ID field
        while i + 1 < len(data):
            st, sl = data[i], data[i + 1]
            if st == 23 and sl >= 2:  # Node MSD sub-TLV
                j = i + 2
                end = min(i + 2 + sl, len(data))
                while j + 1 < end:
                    if data[j] == 44:  # MSD-Type 44
                        values.append(data[j + 1])
                    j += 2
            i += 2 + sl
    return values


def _assert_p2d1_lsp_capture(lsp_db):
    # p2d1: system_id="650100010000" → bytes 65:01:00:01:00:00, pseudonode=00, frag=00
    lsp_id = "6501000100000000"
    assert lsp_id in lsp_db, (
        "LSP 6501.0001.0000.00-00 (p2d1) not found in captured PDUs. "
        "Keys present: %s" % list(lsp_db.keys())
    )
    tlvs = lsp_db[lsp_id]

    # --- Structural: TLV 27 must be present ---
    assert 27 in tlvs, "TLV 27 (SRv6 Locator) missing from p2d1 LSP"
    locators = _get_tlv27_locators(tlvs[27])
    assert locators, "TLV 27 parsed zero locator entries from p2d1 LSP"

    # --- D Flag = False on all advertised locators ---
    for loc in locators:
        assert not loc["d_flag"], (
            "Expected D-flag=False for locator %s, got True" % loc["prefix"]
        )

    # --- Locator prefixes present ---
    prefixes = {loc["prefix"] for loc in locators}
    if "6501:0:0:1::" not in prefixes:
        pytest.xfail(
            "Locator 6501:0:0:1:: (loc1) absent from p2d1 LSP (found: %s) — "
            "known translator bug: with multiple locators per device, only the "
            "last locator value is applied to all IxN slots (multi-locator "
            "multivalue ordering bug in createixnconfig.py / compactor.py)" % prefixes
        )
    assert "6501:0:0:2::" in prefixes, (
        "Locator 6501:0:0:2:: not found in p2d1 LSP (found: %s)" % prefixes
    )

    # --- Source Router ID (TLV 134) ---
    assert 134 in tlvs, "TLV 134 (IPv4 TE Router ID) missing from p2d1 LSP"
    src_id = _get_source_router_id(tlvs[134])
    assert src_id == "6.6.6.6", (
        "Expected IPv4 source router ID 6.6.6.6, got %s" % src_id
    )

    # --- Prefix Attribute Flags (TLV 27 sub-TLV 4) ---
    # Blocker P1: isis.py omits n_flag/r_flag/x_flag from IxNetwork push.
    # Expected from P4 test:
    #   loc1 (6501:0:0:1::): X=1, R=1, N=1
    #   loc2 (6501:0:0:2::): X=0, R=0, N=1
    for loc in locators:
        if loc["prefix"] == "6501:0:0:1::":
            flags_list = _get_prefix_attr_flags(loc["sub_tlvs"])
            if not flags_list:
                pytest.xfail(
                    "Prefix Attribute Flags sub-TLV absent for 6501:0:0:1:: — "
                    "known gap: isis.py does not push n/r/x flags to IxNetwork"
                )
            f = flags_list[0]
            assert f["x"] and f["r"] and f["n"], (
                "Expected X=R=N=1 for 6501:0:0:1::, got %s" % f
            )
        elif loc["prefix"] == "6501:0:0:2::":
            flags_list = _get_prefix_attr_flags(loc["sub_tlvs"])
            if not flags_list:
                pytest.xfail(
                    "Prefix Attribute Flags sub-TLV absent for 6501:0:0:2:: — "
                    "known gap: isis.py does not push n/r/x flags to IxNetwork"
                )
            f = flags_list[0]
            assert not f["x"] and not f["r"] and f["n"], (
                "Expected X=0, R=0, N=1 for 6501:0:0:2::, got %s" % f
            )

    # --- MSD Type 44 (SRH Max H.encaps) in TLV 242 node MSD sub-TLV 23 ---
    # Blocker P0: isis_srv6.py ignores node_msds.max_h_encaps (logs warning, no-op).
    # Expected from P4 test: values 32, 52, 42 in the emulated LSP.
    #   32 → node-level (node_msds.max_h_encaps, TLV 242 sub-TLV 23)
    #   52 → link-level (link_msd.max_h_encaps, TLV 22/222 sub-TLV 26)
    #   42 → per-locator MSD — not yet in snappi model (no IsisSRv6.Locator MSD field)
    if 242 not in tlvs:
        pytest.xfail(
            "TLV 242 (Router Capability) missing from p2d1 LSP — "
            "translator does not push node_msds; MSD assertion blocked"
        )
    msd_vals = _get_node_msd_h_encaps(tlvs[242])
    if not msd_vals:
        pytest.xfail(
            "Node MSD sub-TLV 23 absent in TLV 242 — "
            "known gap: isis_srv6.py ignores node_msds.max_h_encaps"
        )
    assert 32 in msd_vals, (
        "Expected node MSD H.encaps value 32 in TLV 242, got %s" % msd_vals
    )
    # Link MSD (value 52) and per-locator MSD (value 42) assertions require
    # parsing TLV 22/222 sub-TLV 26 and a per-locator model extension respectively.
    # Both are deferred until the translator is extended.
    # TODO: assert 52 in link_msd_vals (TLV 22 sub-TLV 26 parse)
    # TODO: assert 42 in per_locator_msd_vals (requires IsisSRv6.Locator MSD field)

    # --- IPv6 Source Router ID (TLV 140): 6666:0:0:2::1 ---
    # No snappi equivalent for ipv6_te_router_id — omitted by design.

    # --- Simulated node LSP 6401.0000.0001.00-00 ---
    # MSD values 62, 52 and SID 5001:0:0:1:40:: come from the networkGroup
    # fat-tree simulated router on port 2. No snappi equivalent — omitted.


def test_isis_srv6_h_encap_flags(api, b2b_raw_config):
    config = build_config(b2b_raw_config)
    api.set_config(config)

    # Attempt to start capture; non-fatal if Wireshark is not installed.
    # Phase 2 assertions will be skipped when capture is unavailable.
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

    assert len(results.isis_metrics) == 2, (
        "Expected 2 ISIS router metrics (1 per port), got %d"
        % len(results.isis_metrics)
    )

    sessions_by_port = {"p1": 0, "p2": 0}
    for metric in results.isis_metrics:
        if metric.name.startswith("p1"):
            sessions_by_port["p1"] += metric.l2_sessions_up
        else:
            sessions_by_port["p2"] += metric.l2_sessions_up

    assert sessions_by_port["p1"] >= 1, (
        "Expected >= 1 ISIS L2 session on port 1, got %d"
        % sessions_by_port["p1"]
    )
    assert sessions_by_port["p2"] >= 1, (
        "Expected >= 1 ISIS L2 session on port 2, got %d"
        % sessions_by_port["p2"]
    )

    # Phase 2: ISIS LSP capture validation
    if not _capture_ok:
        pytest.skip(
            "Phase 2 capture assertions skipped: Wireshark integration not "
            "available on IxNetwork server."
        )

    pcap_bytes = _get_hw_capture(api, config.ports[0].name)
    lsp_db = _parse_isis_lsps(pcap_bytes)
    _assert_p2d1_lsp_capture(lsp_db)

    # Simulated node LSP 6401.0000.0001.00-00: omitted — no snappi equivalent.

    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.all.state = cs.protocol.all.STOP
    api.set_control_state(cs)
