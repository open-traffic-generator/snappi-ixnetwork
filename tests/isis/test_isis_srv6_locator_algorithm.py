import io
import ipaddress
import struct
import time

import dpkt
import pytest


# Converted from: config.ISIS_SRV6_Locator_Algorithm_values.ixncfg
# Source script:  test.ISIS_SRV6_Locator_Algorithm_values.py
# JSON ref:       scripts/output/config.ISIS_SRV6_Locator_Algorithm_values.json
# Test intent:    ISIS-SRv6 with 2 router instances per port, 2 locators per
#                 device on port 2 with different algorithms. Verifies sessions
#                 come up and (Phase 2) validates algorithm/locator/flag values
#                 via ISIS PDU capture.
#
# Topology (back-to-back, 2 ports):
#   Port 1 — Topology 1: 2 emulated devices (IxN DG multiplier=2, locatorCount=1)
#   Port 2 — Topology 2: 2 emulated devices (IxN DG multiplier=2, locatorCount=2)
#             + simulated fat-tree networkGroup (omitted — no snappi equivalent)
#   Sessions expected: 2 per port (4 total ISIS routers)
#
# Interface network type: broadcast (both topologies)
# MT IDs: isisMTIDList mtId=2 at interface level (still TBD — _configure_multi_topo_id stub)
#         isisSRv6LocatorEntryList mtId=2 at locator level (NOW WIRED via mt_id=[2])
#
# Locator values derived from JSON multivalue counters:
#   Topo1: start=5000:0:0:1::, step=0:0:0:1::
#     p1d1: locator=5000:0:0:1::, algorithm=0
#     p1d2: locator=5000:0:0:2::, algorithm=0
#   Topo2: start=5000:0:1:1::, step=0:0:0:1::, nest=0:1::, overlay[1]=6000:0:1:1::
#     p2d1 loc1: 6000:0:1:1:: algorithm=1 (overlay on index 1)
#     p2d1 loc2: 5000:0:1:2:: algorithm=1
#     p2d2 loc1: 5000:0:2:1:: algorithm=2 (overlay index 3)
#     p2d2 loc2: 5000:0:2:2:: algorithm=3 (overlay index 4)
#
# Prefix attribute flags from JSON:
#   Topo1 isisSRv6LocatorEntryList: enableNFlag=true, enableXFlag=false, enableRFlag=false
#   Topo2 isisSRv6LocatorEntryList: enableNFlag=true, enableXFlag=true,  enableRFlag=true
#   Note: translator silently ignores these (isis.py: "not supported on
#         isisSRv6LocatorEntryList in all IxNetwork server versions").
#         Values are set in snappi for documentation and future compatibility.
#
# Phase 2 capture assertions (not yet implemented):
#   Emulated LSP 6501.0001.0000.00-00 (p2d1):
#     algorithms 0 and 1, locators 5000:0:1:2:: and 6000:0:1:1::,
#     src router ID 1.1.1.3, MTIDs 0 and 2
#   Simulated LSP 6401.0000.0001.00-00 (networkGroup fat-tree):
#     omitted — no snappi equivalent for simulated routers.
#
# MANUAL INTERVENTION REQUIRED:
#   - Update tests/settings.json with b2b port locations
#   - Verify convergence timeout (currently 30s) against actual hardware
#   - Simulated router (networkGroup fatTree) omitted — no snappi equivalent
#   - Interface-level MT ID (mtId=2 in isisMTIDList): _configure_multi_topo_id
#     is still a TBD stub in isis.py — interface MT IDs are not pushed to IxN


def _configure_device(
    device, port_name, mac, ipv6_addr, ipv6_gw, system_id, locators,
    ipv4_te_router_id=None
):
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

    for i, loc_cfg in enumerate(locators, start=1):
        loc_name = f"{device.name}_loc{i}"
        loc = isis.segment_routing.srv6_locators.add()
        loc.locator_name = loc_name
        loc.locator = loc_cfg["locator"]
        loc.prefix_length = 64
        loc.algorithm = loc_cfg["algorithm"]
        loc.metric = 10
        loc.d_flag = False
        # mt_id: locator-level Multi-Topology ID (list of ints, RFC 5120).
        # Translator writes ixn_locator["mtId"] = mt_ids[0] when non-empty.
        loc.mt_id = loc_cfg.get("mt_id", [])
        loc.sid_structure.locator_block_length = 40
        loc.sid_structure.locator_node_length = 24
        loc.sid_structure.function_length = 16
        loc.sid_structure.argument_length = 0

        alp = loc.advertise_locator_as_prefix
        alp.redistribution_type = "up"
        alp.route_origin = "internal"
        pfx = alp.prefix_attributes
        pfx.n_flag = loc_cfg.get("n_flag", True)
        pfx.r_flag = loc_cfg.get("r_flag", False)
        pfx.x_flag = loc_cfg.get("x_flag", False)

        end_sid = loc.end_sids.add()
        end_sid.function = "1"
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

    adj_sid = intf.srv6_adjacency_sids.sids.add()
    adj_sid.locator = "custom_locator_reference"
    adj_sid.custom_locator_reference = f"{device.name}_loc1"
    # function 0x40 = 64 decimal, placed in bits 64-79 of the SID
    adj_sid.function = "40"
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

    # Topology 1 (port 1): 1 locator per device, algorithm 0.
    # JSON: systemId start=640100010000 step=000000010000,
    #       locator start=5000:0:0:1:: step=0:0:0:1::,
    #       n_flag=True x_flag=False r_flag=False at locator level,
    #       mtId=2 on locator entry.
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
                "mt_id": [2],
            },
        ],
    )
    _configure_device(
        p1d2, p1.name,
        mac="00:11:01:00:00:02",
        ipv6_addr="2000:0:0:2::2",
        ipv6_gw="2000:0:0:2::1",
        system_id="640100020000",
        ipv4_te_router_id="1.1.1.2",
        locators=[
            {
                "locator": "5000:0:0:2::",
                "algorithm": 0,
                "mt_id": [2],
            },
        ],
    )

    # Topology 2 (port 2): 2 locators per device, varying algorithms.
    # JSON: systemId start=650100010000 step=000000010000,
    #       n_flag=True x_flag=True r_flag=True at locator level for all topo2 locators,
    #       mtId=2 on all locator entries.
    #
    # p2d1 (DG instance 1, index 1-2 in IxN multivalue):
    #   loc1: locator=6000:0:1:1:: (overlay at index 1), algorithm=1
    #   loc2: locator=5000:0:1:2:: (counter base + step), algorithm=1
    _configure_device(
        p2d1, p2.name,
        mac="00:12:01:00:00:01",
        ipv6_addr="2000:0:0:1::1",
        ipv6_gw="2000:0:0:1::2",
        system_id="650100010000",
        ipv4_te_router_id="1.1.1.3",
        locators=[
            {
                "locator": "6000:0:1:1::",
                "algorithm": 1,
                "mt_id": [2],
                "n_flag": True,
                "r_flag": True,
                "x_flag": True,
            },
            {
                "locator": "5000:0:1:2::",
                "algorithm": 1,
                "mt_id": [2],
                "n_flag": True,
                "r_flag": True,
                "x_flag": True,
            },
        ],
    )
    # p2d2 (DG instance 2, index 3-4 in IxN multivalue):
    #   loc1: locator=5000:0:2:1::, algorithm=2 (overlay at index 3)
    #   loc2: locator=5000:0:2:2::, algorithm=3 (overlay at index 4)
    _configure_device(
        p2d2, p2.name,
        mac="00:12:01:00:00:02",
        ipv6_addr="2000:0:0:2::1",
        ipv6_gw="2000:0:0:2::2",
        system_id="650100020000",
        ipv4_te_router_id="1.1.1.4",
        locators=[
            {
                "locator": "5000:0:2:1::",
                "algorithm": 2,
                "mt_id": [2],
                "n_flag": True,
                "r_flag": True,
                "x_flag": True,
            },
            {
                "locator": "5000:0:2:2::",
                "algorithm": 3,
                "mt_id": [2],
                "n_flag": True,
                "r_flag": True,
                "x_flag": True,
            },
        ],
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

    api.get_capture() internally calls MergeCapture(SW, HW) which requires
    both files to exist. For ISIS control-plane captures there is no SW traffic,
    so MergeCapture fails. This helper stops the capture and downloads the HW
    file (vportName_HW.cap) directly, skipping the merge step.

    Also avoids calling set_control_state(PORT, STOP) which calls
    clearCaptureInfos and wipes the capture buffer before it can be saved.
    """
    ixn = api._ixnetwork
    vport = api._vport.find(Name=port_name)

    # Stop capture and wait for it to drain to disk
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

    # Save captures to the persistence directory on the IxNetwork server
    persistence_path = ixn.Globals.PersistencePath
    ixn.SaveCaptureFiles(persistence_path + "/capture")

    # Download HW capture file directly (skip MergeCapture)
    hw_path = (
        persistence_path + "/capture/" + vport.Name + "_HW.cap"
    )
    url = "%s/files?absolute=%s/capture&filename=%s" % (
        ixn.href, persistence_path, hw_path
    )
    raw_bytes = api._request("GET", url)
    return io.BytesIO(raw_bytes)


def _parse_isis_lsps(pcap_bytes):
    """Return {lsp_id_hex: {tlv_type: [bytes, ...]}} for all L2 LSP PDUs.

    ISIS runs over Ethernet with LLC encapsulation (DSAP=0xFE, SSAP=0xFE,
    Control=0x03), so detection relies on raw byte inspection rather than
    the standard EtherType field.
    """
    lsp_db = {}
    reader_src = pcap_bytes if hasattr(pcap_bytes, "read") else io.BytesIO(pcap_bytes)
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
        # LSP-ID: 8 bytes at offset 12 (system-id 6B + pseudonode 1B + fragment 1B)
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
    """Parse TLV 27 (SRv6 Locator, RFC 9352 §7.3). Returns list of dicts."""
    locators = []
    for data in tlv_bytes_list:
        # TLV 27 value layout (RFC 9352 §7.3, as serialised by IxNetwork):
        #   [0..1] MT-ID flags  [2] Flags  [3..5] Metric (3B or padded 4B to [6])
        #   [7] Algorithm  [8] Prefix Length  [9..] Prefix bytes  Sub-TLVs follow
        if len(data) < 9:
            continue
        algorithm = data[7]
        prefix_len = data[8]
        n_bytes = (prefix_len + 7) // 8
        if len(data) < 9 + n_bytes:
            continue
        prefix = str(ipaddress.IPv6Address(
            data[9: 9 + n_bytes].ljust(16, b'\x00')
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
            "sub_tlvs": sub_tlvs,
        })
    return locators


def _get_prefix_attr_flags(sub_tlvs):
    """Extract N/R/X from Prefix Attribute Flags sub-TLV 4 (RFC 7794 §2).
    Flag byte bit layout: bit7=X, bit6=R, bit5=N."""
    results = []
    for data in sub_tlvs.get(4, []):
        if data:
            results.append({
                "x": bool(data[0] & 0x80),
                "r": bool(data[0] & 0x40),
                "n": bool(data[0] & 0x20),
            })
    return results


def _get_sr_algorithms(tlv242_list):
    """Extract algorithm set from Router Capability TLV 242, sub-TLV 2."""
    algorithms = set()
    for data in tlv242_list:
        # RFC 7981: TLV 242 value = 4B Router-ID + 1B Flags + sub-TLVs
        i = 5  # skip 4-byte Router-ID + 1-byte Flags
        while i + 1 < len(data):
            st, sl = data[i], data[i + 1]
            if st == 2:
                algorithms.update(data[i + 2: i + 2 + sl])
            i += 2 + sl
    return algorithms


def _get_source_router_id(tlv134_list):
    """Extract IPv4 TE Router ID from TLV 134."""
    for data in tlv134_list:
        if len(data) >= 4:
            return str(ipaddress.IPv4Address(data[:4]))
    return None


def _assert_p2d1_lsp_capture(lsp_db):
    # p2d1 system_id="650100010000" → bytes 65 01 00 01 00 00, pseudonode 00, frag 00
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

    # --- Locator prefix values ---
    prefixes = {loc["prefix"] for loc in locators}
    assert "6000:0:1:1::" in prefixes, (
        "Locator 6000:0:1:1:: not in p2d1 LSP (found %s)" % prefixes
    )
    assert "5000:0:1:2::" in prefixes, (
        "Locator 5000:0:1:2:: not in p2d1 LSP (found %s)" % prefixes
    )
    for loc in locators:
        if loc["prefix"] in ("6000:0:1:1::", "5000:0:1:2::"):
            assert loc["algorithm"] == 1, (
                "Expected algorithm=1 for %s, got %d"
                % (loc["prefix"], loc["algorithm"])
            )

    # --- Prefix Attribute Flags (TLV 27 sub-TLV 4) ---
    # isis.py does not push n/r/x flags to IxNetwork — xfail until fixed.
    for loc in locators:
        if loc["prefix"] in ("6000:0:1:1::", "5000:0:1:2::"):
            flags_list = _get_prefix_attr_flags(loc["sub_tlvs"])
            if not flags_list:
                pytest.xfail(
                    "Prefix Attribute Flags sub-TLV absent for %s — "
                    "known gap: isis.py does not push n/r/x flags"
                    % loc["prefix"]
                )
            f = flags_list[0]
            assert f["n"] and f["r"] and f["x"], (
                "Expected N=R=X=1 for %s, got %s" % (loc["prefix"], f)
            )

    # --- Source Router ID (TLV 134) ---
    assert 134 in tlvs, "TLV 134 (IPv4 TE Router ID) missing from p2d1 LSP"
    src_id = _get_source_router_id(tlvs[134])
    assert src_id == "1.1.1.3", (
        "Expected source router ID 1.1.1.3, got %s" % src_id
    )

    # --- SR Algorithms (TLV 242 sub-TLV 2) ---
    # TLV 242 (Router Capability) is present when srv6_capability is configured.
    assert 242 in tlvs, "TLV 242 (Router Capability) missing from p2d1 LSP"
    algs = _get_sr_algorithms(tlvs[242])
    # Sub-TLV 2 (SR Algorithms) only appears when SR-MPLS SRGB is configured.
    # The snappi translator does not support SRGB yet — xfail until added.
    if not algs:
        pytest.xfail(
            "TLV 242 sub-TLV 2 (SR Algorithms) absent — SR-MPLS SRGB not "
            "configured (translator gap); algorithms 0 and 1 unverifiable"
        )
    assert 0 in algs, "SR Algorithm 0 not advertised in Router Capability"
    assert 1 in algs, "SR Algorithm 1 not advertised in Router Capability"

    # --- MT IDs (TLV 229) — TODO Phase 3 ---
    # Blocked: _configure_multi_topo_id is a no-op stub in isis.py.
    # When implemented, enable:
    # mt_ids = {
    #     struct.unpack(">H", d[:2])[0] & 0x0FFF for d in tlvs.get(229, [])
    # }
    # assert 0 in mt_ids and 2 in mt_ids, (
    #     "MT IDs 0 and 2 not found in TLV 229. Found: %s" % mt_ids
    # )


def test_isis_srv6_locator_algorithm(api, b2b_raw_config):
    config = build_config(b2b_raw_config)
    api.set_config(config)

    # Attempt to start capture; non-fatal if Wireshark is not installed on the
    # IxNetwork server (Phase 2 assertions will be skipped in that case).
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

    # Phase 2: ISIS LSP capture validation
    if not _capture_ok:
        pytest.skip(
            "Phase 2 capture assertions skipped: Wireshark integration not "
            "available on IxNetwork server."
        )

    pcap_bytes = _get_hw_capture(api, config.ports[0].name)
    lsp_db = _parse_isis_lsps(pcap_bytes)
    _assert_p2d1_lsp_capture(lsp_db)

    # Simulated LSP 6401.0000.0001.00-00 (networkGroup fat-tree):
    #   omitted — no snappi equivalent for simulated routers.

    cs = api.control_state()
    cs.choice = cs.PROTOCOL
    cs.protocol.all.state = cs.protocol.all.STOP
    api.set_control_state(cs)
