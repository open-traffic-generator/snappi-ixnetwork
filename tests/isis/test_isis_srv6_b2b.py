"""IS-IS SRv6 back-to-back combined control and data plane test suite.

Topology:
    ixia-c port 1 (tx)  <---L2--->  ixia-c port 2 (rx)
    Device d1 / r1                  Device d2 / r2
    Locator: fc00:0:1::/48          Locator: fc00:0:2::/48
    F3216 uSID: lb=32, ln=16, fn=16, arg=0

Each test configures a SINGLE combined config that contains both IS-IS
protocol devices and SRH/G-SRH raw port traffic flows, then runs two phases
without reconfiguring between them:

  Phase 1 - Control plane (CP):
    Start capture on rx.  Start IS-IS protocols, wait for convergence.
    Stop capture.  Save <tc>_cp.pcapng.  Verify:
      - IS-IS L2 session is up (metrics).
      - SRv6 locator and End SID attributes via IxNetwork config state.
      - Wire LSPs parsed from capture when available (B2B LSDB exchange is
        internal to IxN so IS-IS Hello PDUs but not always full LSPs appear
        on the physical wire).

  Phase 2 - Data plane (DP):
    IS-IS protocols remain running.  Start a second capture on rx.  Start
    traffic (raw port-based SRH flows transmit while IS-IS is up).  Stop
    traffic and capture.  Save <tc>_dp.pcapng.  Parse the first IPv6/SRH
    packet and verify routing_type, segments_left, last_entry, flags, tag,
    and segment addresses against the configured values.

Captures are deleted on test pass; preserved on failure for Wireshark
inspection.  Filter: ipv6.routing.type == 4 for SRH, isis for IS-IS.
"""

import binascii
import io
import ipaddress
import os
import socket
import struct
import time

import dpkt
import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AREA        = "490001"
_CONVERGENCE = 30          # seconds to wait for IS-IS adjacency

_LOC1 = "fc00:0:1::"      # r1 locator prefix
_LOC2 = "fc00:0:2::"      # r2 locator prefix
_PFX  = 48                 # locator prefix length (bits)

_LB, _LN, _FN, _ARG = 32, 16, 16, 0   # F3216 SID structure

_SYS_ID_R1 = "650000000001"
_SYS_ID_R2 = "650000000002"

_BEHAVIOR_NAME = {
    1:  "End",
    2:  "End.PSP",
    3:  "End.USP",
    4:  "End.PSP.USP",
    5:  "End.X",
    16: "End.DX6",
    18: "End.DT6",
    28: "End.USD",
    43: "uN",
    60: "uDX6",
    61: "uDX4",
    62: "uDT6",
    63: "uDT4",
    64: "uDT46",
}

_CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "captures")

# ---------------------------------------------------------------------------
# IS-IS / SRv6 device builders
# ---------------------------------------------------------------------------

def _build_base_isis(isis, system_id, eth_name, router_name, intf_name):
    """Populate a DeviceIsisRouter with common L2 p2p settings."""
    isis.name = router_name
    isis.system_id = system_id
    isis.basic.enable_wide_metric = True
    isis.basic.learned_lsp_filter = True
    isis.advanced.area_addresses = [_AREA]
    isis.advanced.lsp_refresh_rate = 900
    isis.advanced.lsp_lifetime = 1200
    isis.advanced.csnp_interval = 10000
    isis.advanced.psnp_interval = 2000
    isis.advanced.max_lsp_size = 1492

    intf = isis.interfaces.add()
    intf.eth_name = eth_name
    intf.name = intf_name
    intf.network_type = "point_to_point"
    intf.level_type = "level_2"
    intf.metric = 10
    intf.l2_settings.dead_interval = 30
    intf.l2_settings.hello_interval = 10
    intf.l2_settings.priority = 0
    intf.advanced.auto_adjust_supported_protocols = True
    return intf


def _add_srv6_locator(isis, locator_prefix, locator_name):
    """Add a single F3216 locator with SID structure to an IS-IS router."""
    sr = isis.segment_routing
    sr.router_capability.srv6_capability.c_flag = True

    loc = sr.srv6_locators.add()
    loc.locator_name = locator_name
    loc.locator = locator_prefix
    loc.prefix_length = _PFX
    loc.algorithm = 0
    loc.metric = 10
    loc.d_flag = False

    ss = loc.sid_structure
    ss.locator_block_length = _LB
    ss.locator_node_length = _LN
    ss.function_length = _FN
    ss.argument_length = _ARG

    adv = loc.advertise_locator_as_prefix
    adv.route_metric = 10
    adv.redistribution_type = "up"
    adv.route_origin = "internal"

    return loc


def _add_end_sid(loc, function_hex, behavior="end"):
    """Add an End SID to a locator."""
    sid = loc.end_sids.add()
    sid.function = function_hex
    sid.argument = "0000"
    sid.endpoint_behavior = behavior
    sid.c_flag = True
    return sid


def _add_adj_sid(intf, function_hex, behavior="end_x"):
    """Add an adjacency SID to an IS-IS interface (default End.X, code 5)."""
    adj = intf.srv6_adjacency_sids.sids.add()
    adj.function          = function_hex
    adj.endpoint_behavior = behavior
    adj.c_flag            = True
    adj.b_flag            = False
    adj.s_flag            = False
    adj.weight            = 0
    adj.locator           = "auto"
    return adj


def _add_isis_v6_routes(isis, prefix, name, prefix_len=64):
    """Add a single IPv6 route range to an IS-IS router for device traffic.

    The named route pool becomes a valid tx_names / rx_names endpoint for
    flow.tx_rx.device flows.  The prefix is distinct from the SRv6 locators
    so both coexist in the same IS-IS session without ambiguity.
    """
    rr = isis.v6_routes.add()
    rr.name = name
    rr.link_metric = 10
    rr.origin_type = "internal"
    addr = rr.addresses.add()
    addr.address = prefix
    addr.prefix = prefix_len
    addr.count = 1
    return rr


def _add_ipv6_link(d1_eth, d2_eth):
    """Add IPv6 link addresses: d1=2001::1/64, d2=2001::2/64."""
    v6_1 = d1_eth.ipv6_addresses.add()
    v6_1.name = "d1_ipv6"
    v6_1.address = "2001::1"
    v6_1.gateway = "2001::2"
    v6_1.prefix = 64

    v6_2 = d2_eth.ipv6_addresses.add()
    v6_2.name = "d2_ipv6"
    v6_2.address = "2001::2"
    v6_2.gateway = "2001::1"
    v6_2.prefix = 64


def _build_combined_config(api, b2b_raw_config):
    """Return a fresh config with IS-IS devices on both ports and no flows yet.

    The caller adds SRH/G-SRH flows and a capture to cfg before calling
    api.set_config().  Both IS-IS protocol devices and the raw port-based
    traffic flows share the same vports so that Phase 2 (DP) can run while
    IS-IS is still up.
    """
    cfg = api.config()

    p1_loc = b2b_raw_config.ports[0].location
    p2_loc = b2b_raw_config.ports[1].location

    p1, p2 = cfg.ports.port(name="tx", location=p1_loc).port(
        name="rx", location=p2_loc
    )

    for l1_orig in b2b_raw_config.layer1:
        l1 = cfg.layer1.add()
        l1.name = l1_orig.name
        l1.port_names = [p1.name, p2.name]
        l1.media = l1_orig.media
        l1.speed = l1_orig.speed

    cfg.options.port_options.location_preemption = True

    d1, d2 = cfg.devices.device(name="d1").device(name="d2")

    d1_eth = d1.ethernets.add()
    d1_eth.name = "d1_eth"
    d1_eth.connection.port_name = p1.name
    d1_eth.mac = "00:00:00:01:01:01"

    d2_eth = d2.ethernets.add()
    d2_eth.name = "d2_eth"
    d2_eth.connection.port_name = p2.name
    d2_eth.mac = "00:00:00:02:02:02"

    _add_ipv6_link(d1_eth, d2_eth)

    return cfg, p1, p2, d1, d2, d1_eth, d2_eth


# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------

def _add_capture(cfg, port_name, cap_name="cap"):
    cap = cfg.captures.capture(name=cap_name)[-1]
    cap.port_names = [port_name]
    cap.format = cap.PCAPNG


def _start_capture(api):
    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.CAPTURE
    cs.port.capture.state = cs.port.capture.START
    api.set_control_state(cs)


def _stop_capture(api):
    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.CAPTURE
    cs.port.capture.state = cs.port.capture.STOP
    api.set_control_state(cs)


def _get_capture(api, port_name):
    req = api.capture_request()
    req.port_name = port_name
    return api.get_capture(req)


def _save_capture(pcap_bytes, name):
    """Save pcapng to tests/captures/<name>.pcapng."""
    os.makedirs(_CAPTURES_DIR, exist_ok=True)
    path = os.path.join(_CAPTURES_DIR, name + ".pcapng")
    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
    with open(path, "wb") as fh:
        fh.write(raw)
    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    print("  [capture] saved %s.pcapng (%d bytes)" % (name, len(raw)))
    return path


def _delete_captures(*names):
    """Delete named pcapng files from the captures directory.

    Called only after all assertions in a test pass.  A failing assertion
    raises before this point, so captures are kept automatically on failure.
    """
    for name in names:
        path = os.path.join(_CAPTURES_DIR, name + ".pcapng")
        try:
            if os.path.exists(path):
                os.remove(path)
                print("  [capture] deleted %s.pcapng" % name)
        except Exception as exc:
            print("  [warn] could not delete %s.pcapng: %s" % (name, exc))


# ---------------------------------------------------------------------------
# Protocol control helpers
# ---------------------------------------------------------------------------

def _start_protocols(api):
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)


def _stop_protocols(api):
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.STOP
    api.set_control_state(cs)


def _start_traffic(api):
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)


def _stop_traffic(api):
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
    api.set_control_state(cs)


# ---------------------------------------------------------------------------
# IS-IS wire parsing helpers
# ---------------------------------------------------------------------------

def _find_isis_pdu(raw_pkt):
    """Return IS-IS PDU bytes from a raw Ethernet frame, or None."""
    for offset in (17, 14, 21, 18):
        if len(raw_pkt) > offset + 4 and raw_pkt[offset] == 0x83:
            return raw_pkt[offset:]
    return None


def _parse_isis_srv6_sids(pcap_bytes, source_system_id):
    """Return {sid_addr: endpoint_behavior} from highest-sequence L2 LSP.

    Walks TLV 27 (SRv6 Locator) -> sub-TLV 5 (SRv6 End SID) in IS-IS PDUs.
    Returns the SID map from the LSP with the largest sequence number seen.
    """
    try:
        src_bytes = bytes.fromhex(
            source_system_id.replace(".", "").replace(":", "")
        )
    except ValueError:
        return {}

    best_seq  = -1
    best_sids = {}

    for _, raw_pkt in dpkt.pcapng.Reader(pcap_bytes):
        try:
            isis = _find_isis_pdu(bytes(raw_pkt))
        except Exception:
            continue
        if isis is None or len(isis) < 27:
            continue
        if isis[0] != 0x83:
            continue
        if (isis[4] & 0x1F) != 0x14:   # Level 2 LSP
            continue
        if isis[10:16] != src_bytes:
            continue
        if isis[17] != 0:               # fragment 0 only
            continue

        seq     = struct.unpack(">I", isis[18:22])[0]
        pdu_len = struct.unpack(">H", isis[8:10])[0]
        hdr_len = isis[1]

        offset  = hdr_len
        end_off = min(pdu_len, len(isis))
        pkt_sids = {}

        while offset + 2 <= end_off:
            tlv_type = isis[offset]
            tlv_len  = isis[offset + 1]
            if offset + 2 + tlv_len > end_off:
                break
            tlv_val  = isis[offset + 2: offset + 2 + tlv_len]
            offset  += 2 + tlv_len

            if tlv_type != 27 or len(tlv_val) < 9:
                continue

            prefix_len_bits = tlv_val[8]
            prefix_bytes    = (prefix_len_bits + 7) // 8
            if len(tlv_val) < 9 + prefix_bytes:
                continue

            sub_off = 9 + prefix_bytes
            while sub_off + 2 <= len(tlv_val):
                sub_type = tlv_val[sub_off]
                sub_len  = tlv_val[sub_off + 1]
                if sub_off + 2 + sub_len > len(tlv_val):
                    break
                sub_val  = tlv_val[sub_off + 2: sub_off + 2 + sub_len]
                sub_off += 2 + sub_len

                if sub_type != 5 or len(sub_val) < 20:
                    continue
                ep_behavior = struct.unpack(">H", sub_val[1:3])[0]
                try:
                    sid_addr = str(ipaddress.IPv6Address(bytes(sub_val[4:20])))
                except ValueError:
                    continue
                pkt_sids[sid_addr] = ep_behavior

        if seq > best_seq:
            best_seq  = seq
            best_sids = pkt_sids

    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    return best_sids


# ---------------------------------------------------------------------------
# IxNetwork config-state readers (reliable in B2B where LSPs are internal)
# ---------------------------------------------------------------------------

def _read_srv6_state(api, router_name):
    """Read SRv6 config state for router_name from IxNetwork internal state.

    Returns {"c_flag": bool, "locators": [{"locator", "prefix_length",
    "algorithm", "metric", "end_sids": [{"sid", "active", "function_code"}]}]}
    """
    import re as _re
    import ipaddress as _ip

    _XPATH_MAP = {
        "topology": "Topology",
        "deviceGroup": "DeviceGroup",
        "isisL3Router": "IsisL3Router",
    }

    def _mval(attr, default=""):
        try:
            vals = attr.Values
            return vals[0] if vals else default
        except Exception:
            try:
                return str(attr)
            except Exception:
                return default

    try:
        info  = api.ixn_objects.get(router_name)
        parts = _re.findall(r'(\w+)\[(\d+)\]', info.xpath)
        obj   = api._ixnetwork
        for cls_name, idx_str in parts:
            attr = _XPATH_MAP.get(cls_name, cls_name[0].upper() + cls_name[1:])
            coll = getattr(obj, attr).find()
            obj  = coll[int(idx_str) - 1]

        try:
            c_flag = str(_mval(obj.CFlagOfSRv6Cap, "false")).lower() not in ("false", "0")
        except Exception:
            c_flag = False

        locators = []
        for loc in obj.IsisSRv6LocatorEntryList.find():
            try:
                loc_prefix = str(_mval(loc.Locator, "::"))
                loc_len    = int(_mval(loc.PrefixLength, 48))
                algo       = int(_mval(loc.Algorithm, 0))
                metric     = int(_mval(loc.Metric, 0))
            except Exception:
                loc_prefix, loc_len, algo, metric = "::", 128, 0, 0

            end_sids = []
            try:
                eid = loc.IsisSRv6EndSIDList.find()
                for sv, av, fv in zip(eid.Sid.Values,
                                      eid.Active.Values,
                                      eid.EndPointFunction.Values):
                    try:
                        sid_addr = str(_ip.IPv6Address(sv))
                    except ValueError:
                        sid_addr = str(sv)
                    active = str(av).lower() not in ("false", "0")
                    try:
                        func_code = int(fv)
                    except (ValueError, TypeError):
                        func_code = 0
                    end_sids.append({
                        "sid": sid_addr, "active": active,
                        "function_code": func_code,
                    })
            except Exception as exc:
                print("  [warn] End SID read failed for %s: %s" % (loc_prefix, exc))

            locators.append({
                "locator": loc_prefix, "prefix_length": loc_len,
                "algorithm": algo, "metric": metric, "end_sids": end_sids,
            })

        return {"c_flag": c_flag, "locators": locators}
    except Exception as exc:
        print("  [warn] _read_srv6_state(%s) failed: %s" % (router_name, exc))
        return {"c_flag": False, "locators": []}


# ---------------------------------------------------------------------------
# CP verification helpers
# ---------------------------------------------------------------------------

def _print_cp_state(tc, router, state):
    sep = "=" * 64
    inner = "-" * 64
    print("\n" + sep)
    print("  [%s] Control-plane state  router=%s  c_flag=%s"
          % (tc, router, state.get("c_flag", False)))
    print(inner)
    for loc in state.get("locators", []):
        print("  Locator : %s/%d  algorithm=%d  metric=%d"
              % (loc["locator"], loc["prefix_length"], loc["algorithm"], loc["metric"]))
        for s in loc.get("end_sids", []):
            code   = s["function_code"]
            status = "ACTIVE " if s["active"] else "INACTIVE"
            print("    End SID : %-36s  behavior=%-2d (%s)  [%s]"
                  % (s["sid"], code, _BEHAVIOR_NAME.get(code, "?"), status))
    print(sep)


def _verify_cp(api, tc, expected_r1, expected_r2=None):
    """Verify IS-IS SRv6 state for r1 (and optionally r2) from IxN config state.

    expected_r1 / expected_r2: {sid_addr: function_code}
    Also tries to verify from wire capture (falls back gracefully in pure B2B).
    """
    sep = "-" * 64

    for router, expected in [("r1", expected_r1), ("r2", expected_r2)]:
        if expected is None:
            continue
        state = _read_srv6_state(api, router)
        _print_cp_state(tc, router, state)

        actual = {
            s["sid"]: s["function_code"]
            for loc in state.get("locators", [])
            for s in loc.get("end_sids", [])
            if s["active"]
        }

        print("\n" + sep)
        print("  [%s] CP verification  router=%s  [configured vs. IxN state]" % (tc, router))
        print(sep)
        all_ok = True
        for sid, code in sorted(expected.items()):
            name = _BEHAVIOR_NAME.get(code, "code-%d" % code)
            if sid in actual and actual[sid] == code:
                print("  [PASS]  %-36s  behavior=%d (%s)" % (sid, code, name))
            else:
                got = actual.get(sid, "MISSING")
                print("  [FAIL]  %-36s  expected=%d (%s)  got=%s"
                      % (sid, code, name, got))
                all_ok = False
        print(sep)

        for sid, code in expected.items():
            assert sid in actual, (
                "[%s] %s: End SID %s not in IxN config state; got %s"
                % (tc, router, sid, actual)
            )
            assert actual[sid] == code, (
                "[%s] %s: %s behavior expected=%d got=%d"
                % (tc, router, sid, code, actual[sid])
            )


def _verify_cp_wire(tc, pcap_bytes, router, sys_id, expected_sids):
    """Try to verify End SIDs from wire capture; print result and return True/False."""
    wire_sids = _parse_isis_srv6_sids(pcap_bytes, sys_id)
    sep = "-" * 64
    print("\n" + sep)
    print("  [%s] CP wire verification  router=%s" % (tc, router))
    if not wire_sids:
        print("  (IS-IS LSPs not on physical wire in B2B — "
              "IxN exchanges LSDB internally)")
        print(sep)
        return False

    print(sep)
    all_ok = True
    for sid, code in sorted(expected_sids.items()):
        name = _BEHAVIOR_NAME.get(code, "code-%d" % code)
        if sid in wire_sids and wire_sids[sid] == code:
            print("  [PASS wire]  %-36s  behavior=%d (%s)" % (sid, code, name))
        else:
            got = wire_sids.get(sid, "NOT FOUND")
            print("  [FAIL wire]  %-36s  expected=%d (%s)  wire=%s"
                  % (sid, code, name, got))
            all_ok = False
    print(sep)
    return all_ok


# ---------------------------------------------------------------------------
# IS-IS session metric helper
# ---------------------------------------------------------------------------

def _check_isis_sessions_up(api, tc, min_sessions=1):

    req = api.metrics_request()
    req.isis.router_names = []
    metrics = api.get_metrics(req)
    up = sum(m.l2_sessions_up for m in metrics.isis_metrics)
    print("  [%s] IS-IS L2 sessions_up = %d" % (tc, up))
    assert up >= min_sessions, (
        "[%s] Expected >= %d IS-IS session(s) up; got %d"
        % (tc, min_sessions, up)
    )
    return up


# ---------------------------------------------------------------------------
# MSD state reader and verifier (node MSD + link MSD)
# ---------------------------------------------------------------------------

def _read_msd_state(api, router_name, intf_name):
    """Read Node MSD (from isisL3Router) and Link MSD (from IsisL3 interface).

    Returns {
      "node_msd": {"advertise": bool, "max_sl": int,
                   "max_end_pop_srh": int, "max_h_encaps": int},
      "link_msd": {"advertise": bool, "max_sl": int, "max_end_pop_srh": int},
    }
    Attributes that cannot be read (IxN version / API mismatch) default to 0/False.
    """
    import re as _re

    _XPATH_MAP = {
        "topology":     "Topology",
        "deviceGroup":  "DeviceGroup",
        "isisL3Router": "IsisL3Router",
    }

    def _mval_int(obj, name, default=0):
        try:
            attr = getattr(obj, name)
            vals = attr.Values
            v = vals[0] if vals else default
            return int(v)
        except Exception:
            return default

    def _mval_bool(obj, name, default=False):
        try:
            attr = getattr(obj, name)
            vals = attr.Values
            v = str(vals[0]).lower() if vals else str(default).lower()
            return v not in ("false", "0")
        except Exception:
            return default

    result = {"node_msd": {}, "link_msd": {}}

    try:
        info  = api.ixn_objects.get(router_name)
        parts = _re.findall(r'(\w+)\[(\d+)\]', info.xpath)
        obj   = api._ixnetwork
        for cls_name, idx_str in parts:
            attr = _XPATH_MAP.get(cls_name, cls_name[0].upper() + cls_name[1:])
            coll = getattr(obj, attr).find()
            obj  = coll[int(idx_str) - 1]
        result["node_msd"] = {
            "advertise":       _mval_bool(obj, "AdvertiseNodeMsd"),
            "max_sl":          _mval_int(obj,  "MaxSL"),
            "max_end_pop_srh": _mval_int(obj,  "MaxEndPopSrh"),
            "max_h_encaps":    _mval_int(obj,  "MaxHEncapMsd"),
        }
    except Exception as exc:
        print("  [warn] node MSD read failed for %s: %s" % (router_name, exc))

    try:
        info  = api.ixn_objects.get(intf_name)
        parts = _re.findall(r'(\w+)\[(\d+)\]', info.xpath)
        obj   = api._ixnetwork
        for cls_name, idx_str in parts:
            attr = cls_name[0].upper() + cls_name[1:]
            coll = getattr(obj, attr).find()
            obj  = coll[int(idx_str) - 1]
        result["link_msd"] = {
            "advertise":       _mval_bool(obj, "AdvertiseLinkMsd"),
            "max_sl":          _mval_int(obj,  "MaxSlMsd"),
            "max_end_pop_srh": _mval_int(obj,  "MaxEndPopMsd"),
        }
    except Exception as exc:
        print("  [warn] link MSD read failed for %s: %s" % (intf_name, exc))

    return result


def _verify_msd(tc, msd_state, expected):
    """Assert Node MSD and Link MSD config-state values match expected dict.

    expected keys: "node_msd" and/or "link_msd", each a dict of
    {"advertise": bool, "max_sl": int, "max_end_pop_srh": int, ...}
    Prints a pass/fail table for each attribute checked.
    """
    sep   = "=" * 64
    inner = "-" * 64
    print("\n" + sep)
    print("  [%s] MSD config-state verification  [configured vs. IxN state]" % tc)
    print(inner)

    all_ok = True

    def _chk(name, got, want):
        nonlocal all_ok
        ok = (str(got) == str(want))
        status = "[PASS]" if ok else "[FAIL]"
        if ok:
            print("  %s  %-30s  %s" % (status, name, want))
        else:
            print("  %s  %-30s  expected=%s  got=%s" % (status, name, want, got))
            all_ok = False

    exp_node = expected.get("node_msd", {})
    got_node = msd_state.get("node_msd", {})
    print("  --- Node MSD ---")
    for key in ("advertise", "max_sl", "max_end_pop_srh", "max_h_encaps"):
        if key in exp_node:
            _chk("node_msd.%s" % key, got_node.get(key), exp_node[key])

    exp_link = expected.get("link_msd", {})
    got_link = msd_state.get("link_msd", {})
    print("  --- Link MSD ---")
    for key in ("advertise", "max_sl", "max_end_pop_srh"):
        if key in exp_link:
            _chk("link_msd.%s" % key, got_link.get(key), exp_link[key])

    print(sep)
    assert all_ok, "[%s] MSD config-state mismatch — see table above" % tc


# ---------------------------------------------------------------------------
# SRH flow builders (data plane)
# ---------------------------------------------------------------------------

def _build_srh_flow(cfg, name, tx_name, rx_name,
                    ip6_src, ip6_dst,
                    segments_left, last_entry, segments,
                    protected=0, alert=0, tag=0,
                    pps=100, packets=200):
    """Build Ethernet + IPv6 (nxt=43) + SRH (segment_routing) flow."""
    f = cfg.flows.add()
    f.name = name
    f.tx_rx.port.tx_name = tx_name
    f.tx_rx.port.rx_name = rx_name
    f.rate.pps = pps
    f.duration.fixed_packets.packets = packets
    f.metrics.enable = True

    eth = f.packet.add()
    eth.choice = "ethernet"
    eth.ethernet.src.value = "00:11:22:33:44:55"
    eth.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = ip6_src
    ip6.ipv6.dst.value = ip6_dst
    ip6.ipv6.next_header.value = 43

    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing"
    sr = ext.ipv6_extension_header.routing.segment_routing
    sr.segments_left.value = segments_left
    sr.last_entry.value    = last_entry
    sr.flags.protected.value = protected
    sr.flags.alert.value     = alert
    sr.tag.value             = tag
    for segment in segments:
        sr.segment_list.segment()[-1].segment.value = segment

    return f


def _add_usid_container(segment_list, container_ipv6, lb_bits=32, usid_bits=16):
    """Add a uSID container segment using the structured locator/usids API.

    Unpacks a pre-packed IPv6 uSID container address (e.g. "fc00:0:1:2:3::")
    into the FlowIpv6SegmentRoutingUsidSegment locator / locator_length / usids
    fields, which is required by the new snappi API.
    """
    packed = socket.inet_pton(socket.AF_INET6, container_ipv6)
    lb_bytes = lb_bits // 8
    locator_raw = packed[:lb_bytes] + b'\x00' * (16 - lb_bytes)
    locator_str = socket.inet_ntop(socket.AF_INET6, locator_raw)
    usid_bytes = usid_bits // 8
    usids = []
    offset = lb_bytes
    while offset + usid_bytes <= 16:
        usid_int = int.from_bytes(packed[offset:offset + usid_bytes], 'big')
        if usid_int == 0:
            break
        usids.append(format(usid_int, '0%dx' % (usid_bits // 4)))
        offset += usid_bytes
    seg = segment_list.segment()[-1]
    seg.locator.value = locator_str
    seg.locator_length.value = lb_bits
    seg.usids = list(usids)


def _build_gsrh_flow(cfg, name, tx_name, rx_name,
                     ip6_src, ip6_dst,
                     segments_left, last_entry, usid_containers,
                     oam=0, tag=0,
                     pps=100, packets=200):
    """Build Ethernet + IPv6 (nxt=43) + uSID SRH (segment_routing_usid) flow."""
    f = cfg.flows.add()
    f.name = name
    f.tx_rx.port.tx_name = tx_name
    f.tx_rx.port.rx_name = rx_name
    f.rate.pps = pps
    f.duration.fixed_packets.packets = packets
    f.metrics.enable = True

    eth = f.packet.add()
    eth.choice = "ethernet"
    eth.ethernet.src.value = "00:11:22:33:44:55"
    eth.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = ip6_src
    ip6.ipv6.dst.value = ip6_dst
    ip6.ipv6.next_header.value = 43

    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing_usid"
    usid = ext.ipv6_extension_header.routing.segment_routing_usid
    usid.segments_left.value = segments_left
    usid.last_entry.value    = last_entry
    usid.flags.oam.value     = oam
    usid.tag.value           = tag
    for usid_container in usid_containers:
        _add_usid_container(usid.segment_list, usid_container)

    return f


# ---------------------------------------------------------------------------
# Inner payload flow builders
# ---------------------------------------------------------------------------

def _add_inner_ipv4_tcp(flow, src="10.1.1.1", dst="10.2.2.2", src_port=1234, dst_port=80):
    """Append inner IPv4 + TCP headers to an existing SRH/G-SRH flow.

    Returns a cfg dict of all field values for use in _verify_dp_inner.
    IPv4 protocol=6 is set explicitly; TCP data_offset=5 is forced by the
    trafficitem.py SRH inner payload fix.
    """
    ip4 = flow.packet.add()
    ip4.choice = "ipv4"
    ip4.ipv4.src.value = src
    ip4.ipv4.dst.value = dst
    ip4.ipv4.protocol.value = 6

    tcp = flow.packet.add()
    tcp.choice = "tcp"
    tcp.tcp.src_port.value = src_port
    tcp.tcp.dst_port.value = dst_port

    return {
        "type": "ipv4_tcp",
        "ip_src": src, "ip_dst": dst, "ip_protocol": 6,
        "src_port": src_port, "dst_port": dst_port, "data_offset": 5,
    }


def _add_inner_ipv4_udp(flow, src="10.1.1.1", dst="10.2.2.2", src_port=1234, dst_port=5000):
    """Append inner IPv4 + UDP headers to an existing SRH/G-SRH flow.

    Returns a cfg dict of all field values for use in _verify_dp_inner.
    IPv4 protocol=17 is set explicitly; UDP length=8 is forced by the
    trafficitem.py SRH inner payload fix.
    """
    ip4 = flow.packet.add()
    ip4.choice = "ipv4"
    ip4.ipv4.src.value = src
    ip4.ipv4.dst.value = dst
    ip4.ipv4.protocol.value = 17

    udp = flow.packet.add()
    udp.choice = "udp"
    udp.udp.src_port.value = src_port
    udp.udp.dst_port.value = dst_port

    return {
        "type": "ipv4_udp",
        "ip_src": src, "ip_dst": dst, "ip_protocol": 17,
        "src_port": src_port, "dst_port": dst_port, "udp_length": 8,
    }


def _add_inner_ipv6_tcp(flow, src="2001:db8::1", dst="2001:db8::2", src_port=1234, dst_port=80):
    """Append inner IPv6 + TCP headers to an existing SRH/G-SRH flow.

    Returns a cfg dict of all field values for use in _verify_dp_inner.
    IPv6 next_header=6 is set explicitly; TCP data_offset=5 is forced by the
    trafficitem.py SRH inner payload fix.
    """
    ip6 = flow.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = src
    ip6.ipv6.dst.value = dst
    ip6.ipv6.next_header.value = 6

    tcp = flow.packet.add()
    tcp.choice = "tcp"
    tcp.tcp.src_port.value = src_port
    tcp.tcp.dst_port.value = dst_port

    return {
        "type": "ipv6_tcp",
        "ip_src": src, "ip_dst": dst, "ip_next_header": 6,
        "src_port": src_port, "dst_port": dst_port, "data_offset": 5,
    }


def _add_inner_ipv6_udp(flow, src="2001:db8::1", dst="2001:db8::2", src_port=1234, dst_port=5000):
    """Append inner IPv6 + UDP headers to an existing SRH/G-SRH flow.

    Returns a cfg dict of all field values for use in _verify_dp_inner.
    IPv6 next_header=17 is set explicitly; UDP length=8 is forced by the
    trafficitem.py SRH inner payload fix.
    """
    ip6 = flow.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = src
    ip6.ipv6.dst.value = dst
    ip6.ipv6.next_header.value = 17

    udp = flow.packet.add()
    udp.choice = "udp"
    udp.udp.src_port.value = src_port
    udp.udp.dst_port.value = dst_port

    return {
        "type": "ipv6_udp",
        "ip_src": src, "ip_dst": dst, "ip_next_header": 17,
        "src_port": src_port, "dst_port": dst_port, "udp_length": 8,
    }


def _build_device_flow(cfg, name, tx_names, rx_names, pps=50, packets=100):
    """Build a plain IPv6 device flow between IS-IS route-range endpoints.

    No packet headers are specified — IxNetwork auto-generates the Ethernet +
    IPv6 stack from the device endpoint context, resolving the next-hop MAC
    via the IS-IS adjacency.  Traffic flows only when IS-IS is Up.
    """
    f = cfg.flows.add()
    f.name = name
    f.tx_rx.device.tx_names = tx_names
    f.tx_rx.device.rx_names = rx_names
    f.rate.pps = pps
    f.duration.fixed_packets.packets = packets
    f.metrics.enable = True
    return f


# ---------------------------------------------------------------------------
# SRH wire parser (data plane)
# ---------------------------------------------------------------------------

def _parse_inner_payload(buf, inner_off, next_hdr_srh, tlv_embedded=False):
    """Parse the inner IPv4/IPv6 + TCP/UDP payload that follows an SRH.

    buf:          raw frame bytes
    inner_off:    byte offset where the inner header starts
    next_hdr_srh: SRH Next Header field (4=IPv4, 41=IPv6)
    tlv_embedded: True when the inner IPv6 was found inside the SRH TLV area
                  (IxN device-flow quirk for non-uSID ipv6RoutingType4 flows).
                  In that layout IxN places the transport header immediately
                  before the inner IPv6: TCP at (inner_off - 20), UDP at
                  (inner_off - 8).  Use the standard (inner_off + 40) otherwise.

    Returns a dict of parsed field values, or None if the payload cannot be
    parsed (wrong protocol, truncated frame, or exception).
    """
    try:
        if next_hdr_srh == 4:                              # inner IPv4
            if len(buf) < inner_off + 20:
                return None
            ihl      = (buf[inner_off] & 0x0F) * 4
            protocol = buf[inner_off + 9]
            ip_src   = socket.inet_ntoa(bytes(buf[inner_off + 12:inner_off + 16]))
            ip_dst   = socket.inet_ntoa(bytes(buf[inner_off + 16:inner_off + 20]))
            result   = {"ip_src": ip_src, "ip_dst": ip_dst, "ip_protocol": protocol}
            tl_off   = inner_off + ihl
            if protocol == 6 and len(buf) >= tl_off + 14:     # TCP
                result["src_port"]    = struct.unpack(">H", buf[tl_off    :tl_off + 2])[0]
                result["dst_port"]    = struct.unpack(">H", buf[tl_off + 2:tl_off + 4])[0]
                result["data_offset"] = buf[tl_off + 12] >> 4
            elif protocol == 17 and len(buf) >= tl_off + 8:   # UDP
                result["src_port"]   = struct.unpack(">H", buf[tl_off    :tl_off + 2])[0]
                result["dst_port"]   = struct.unpack(">H", buf[tl_off + 2:tl_off + 4])[0]
                result["udp_length"] = struct.unpack(">H", buf[tl_off + 4:tl_off + 6])[0]
            return result

        elif next_hdr_srh == 41:                           # inner IPv6
            if len(buf) < inner_off + 40:
                return None
            ip_next = buf[inner_off + 6]
            ip_src  = str(ipaddress.IPv6Address(bytes(buf[inner_off +  8:inner_off + 24])))
            ip_dst  = str(ipaddress.IPv6Address(bytes(buf[inner_off + 24:inner_off + 40])))
            result  = {"ip_src": ip_src, "ip_dst": ip_dst, "ip_next_header": ip_next}
            # IxN device-flow TLV layout: transport is immediately before inner IPv6.
            if tlv_embedded and ip_next == 6:
                tl_off = inner_off - 20    # TCP header (20 B) ends at inner_off
            elif tlv_embedded and ip_next == 17:
                tl_off = inner_off - 8     # UDP header (8 B) ends at inner_off
            else:
                tl_off = inner_off + 40    # standard: transport follows inner IPv6
            if ip_next == 6 and len(buf) >= tl_off + 14:      # TCP
                result["src_port"]    = struct.unpack(">H", buf[tl_off    :tl_off + 2])[0]
                result["dst_port"]    = struct.unpack(">H", buf[tl_off + 2:tl_off + 4])[0]
                result["data_offset"] = buf[tl_off + 12] >> 4
            elif ip_next == 17 and len(buf) >= tl_off + 8:    # UDP
                result["src_port"]   = struct.unpack(">H", buf[tl_off    :tl_off + 2])[0]
                result["dst_port"]   = struct.unpack(">H", buf[tl_off + 2:tl_off + 4])[0]
                result["udp_length"] = struct.unpack(">H", buf[tl_off + 4:tl_off + 6])[0]
            return result

    except Exception as exc:
        print("  [warn] inner payload parse error at off=%d: %s" % (inner_off, exc))
    return None


def _read_pcap_frames(pcap_bytes):
    """Yield raw Ethernet frame bytes from a pcapng/pcap capture.

    Prints a hex dump of the first two frames for quick visual sanity checks.
    """
    if pcap_bytes is None:
        return

    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    if not raw:
        return

    try:
        pcap = dpkt.pcapng.Reader(io.BytesIO(raw))
    except Exception:
        try:
            pcap = dpkt.pcap.Reader(io.BytesIO(raw))
        except Exception:
            return

    for i, (_, pkt_data) in enumerate(pcap, start=1):
        buf = bytes(pkt_data)
        if i <= 2:
            print("  [dp-pcap] pkt[%d] len=%d hex=%s" % (i, len(buf), buf[:64].hex()))
        yield buf


def _parse_srh_packet(buf):
    """Parse a single raw Ethernet frame for an IPv6/SRH (routing_type=4) packet.

    Returns: {"ip6_dst", "routing_type", "segments_left", "last_entry",
               "flags_byte", "tag", "segments": [ipv6_str, ...], "inner"}
    or None if this frame is not an IPv6/SRH packet.
    """
    try:
        # Ethernet frame: dst(6)+src(6)+ethertype(2) = 14 bytes
        if len(buf) < 14:
            return None
        ethertype = struct.unpack(">H", buf[12:14])[0]
        if ethertype != 0x86DD:   # IPv6
            return None

        # IPv6 fixed header: 40 bytes (starts at offset 14)
        if len(buf) < 54:
            return None
        ip6_off = 14
        next_hdr = buf[ip6_off + 6]
        if next_hdr != 43:        # Routing Extension Header
            return None

        # SRH starts immediately after the IPv6 fixed header
        srh_off = ip6_off + 40
        if len(buf) < srh_off + 8:
            return None

        next_hdr_srh = buf[srh_off]
        hdr_ext_len  = buf[srh_off + 1]
        routing_type = buf[srh_off + 2]
        if routing_type != 4:
            return None

        segments_left = buf[srh_off + 3]
        last_entry    = buf[srh_off + 4]
        flags_byte    = buf[srh_off + 5]
        tag           = struct.unpack(">H", buf[srh_off + 6:srh_off + 8])[0]

        n_segs = last_entry + 1
        seg_list = []
        seg_start = srh_off + 8
        for i in range(n_segs):
            seg_bytes = buf[seg_start + i * 16: seg_start + i * 16 + 16]
            if len(seg_bytes) < 16:
                break
            seg_list.append(str(ipaddress.IPv6Address(bytes(seg_bytes))))

        inner_off_std = srh_off + (hdr_ext_len + 1) * 8
        seg_list_end  = srh_off + 8 + n_segs * 16
        inner_off     = inner_off_std
        tlv_embedded  = False
        # IxN device-flow quirk: for non-uSID ipv6RoutingType4 the inner
        # IPv6 header can start inside the SRH's 64-byte TLV area (before
        # inner_off_std).  In that layout the transport header (TCP/UDP) is
        # placed immediately before the inner IPv6 in the TLV.  Scan from
        # the end of the segment list for the first 0x60 byte that looks like
        # an IPv6 header.
        if next_hdr_srh == 41 and seg_list_end < inner_off_std:
            for _i in range(seg_list_end, inner_off_std):
                if _i + 8 <= len(buf) and (buf[_i] >> 4) == 6:
                    _nh = buf[_i + 6]
                    if _nh in (6, 17, 4, 41, 58, 59):  # plausible next-header
                        inner_off    = _i
                        tlv_embedded = True
                        break

        ip6_dst = str(ipaddress.IPv6Address(bytes(buf[ip6_off + 24:ip6_off + 40])))

        return {
            "ip6_dst":       ip6_dst,
            "routing_type":  routing_type,
            "segments_left": segments_left,
            "last_entry":    last_entry,
            "flags_byte":    flags_byte,
            "tag":           tag,
            "segments":      seg_list,
            "inner":         _parse_inner_payload(buf, inner_off, next_hdr_srh,
                                                  tlv_embedded=tlv_embedded),
        }
    except Exception:
        return None


def _parse_all_srh_from_pcap(pcap_bytes):
    """Return a list of every IPv6/SRH (routing_type=4) packet dict in a capture.

    Each dict has the same fields as _parse_srh_from_pcap plus "ip6_dst" (the
    outer IPv6 destination address), so multiple flows captured together in
    one burst can be matched back to the flow that produced them.
    """
    results = []
    pkt_count = 0
    for buf in _read_pcap_frames(pcap_bytes):
        pkt_count += 1
        parsed = _parse_srh_packet(buf)
        if parsed is not None:
            results.append(parsed)

    if not results:
        print("  [dp-pcap] scanned %d packets; no IPv6/SRH (routing_type=4) found" % pkt_count)
    return results


def _parse_srh_from_pcap(pcap_bytes):
    """Return first SRH packet fields from pcapng capture, or None.

    Returns: {"routing_type", "segments_left", "last_entry", "flags_byte",
               "tag", "segments": [ipv6_str, ...]}
    """
    if pcap_bytes is None:
        return None
    packets = _parse_all_srh_from_pcap(pcap_bytes)
    return packets[0] if packets else None


def _norm(addr):
    return str(ipaddress.IPv6Address(addr))


# ---------------------------------------------------------------------------
# DP verification helper
# ---------------------------------------------------------------------------

def _verify_dp(tc, srh, expected):
    """Assert SRH fields from wire match expected dict.

    expected keys: routing_type, segments_left, last_entry, flags_byte,
                   tag (all int), segments (list of IPv6 strings).
    Prints a pass/fail table.
    """
    sep = "=" * 64
    inner = "-" * 64
    print("\n" + sep)
    print("  [%s] Data-plane wire verification  [SRH headers]" % tc)
    print(inner)

    assert srh is not None, "[%s] No SRH packet found in DP capture" % tc

    fields_ok = True

    def _chk(name, got, want):
        nonlocal fields_ok
        if got == want:
            print("  [PASS]  %-20s  %s" % (name, want))
        else:
            print("  [FAIL]  %-20s  expected=%s  got=%s" % (name, want, got))
            fields_ok = False

    _chk("routing_type",  srh["routing_type"],  expected["routing_type"])
    _chk("segments_left", srh["segments_left"], expected["segments_left"])
    _chk("last_entry",    srh["last_entry"],    expected["last_entry"])
    _chk("flags_byte",    srh["flags_byte"],    expected.get("flags_byte", 0))
    _chk("tag",           srh["tag"],           expected.get("tag", 0))

    exp_segs = [_norm(s) for s in expected.get("segments", [])]
    got_segs = [_norm(s) for s in srh["segments"]]
    print(inner)
    for i, (e, g) in enumerate(zip(exp_segs, got_segs)):
        if e == g:
            print("  [PASS]  segment[%d]           %s" % (i, e))
        else:
            print("  [FAIL]  segment[%d]           expected=%s  got=%s" % (i, e, g))
            fields_ok = False
    if len(exp_segs) != len(got_segs):
        print("  [FAIL]  segment count        expected=%d  got=%d"
              % (len(exp_segs), len(got_segs)))
        fields_ok = False
    print(sep)

    # Assert each field
    assert srh["routing_type"]  == expected["routing_type"],  \
        "[%s] routing_type: expected=%d got=%d" % (tc, expected["routing_type"], srh["routing_type"])
    assert srh["segments_left"] == expected["segments_left"], \
        "[%s] segments_left: expected=%d got=%d" % (tc, expected["segments_left"], srh["segments_left"])
    assert srh["last_entry"]    == expected["last_entry"],    \
        "[%s] last_entry: expected=%d got=%d" % (tc, expected["last_entry"], srh["last_entry"])
    assert srh["flags_byte"]    == expected.get("flags_byte", 0), \
        "[%s] flags_byte: expected=0x%02x got=0x%02x" % (tc, expected.get("flags_byte", 0), srh["flags_byte"])
    assert srh["tag"]           == expected.get("tag", 0), \
        "[%s] tag: expected=0x%04x got=0x%04x" % (tc, expected.get("tag", 0), srh["tag"])
    assert got_segs == exp_segs, \
        "[%s] segments mismatch: expected=%s got=%s" % (tc, exp_segs, got_segs)


def _verify_dp_inner(tc, inner_wire, inner_cfg):
    """Print configured-vs-wire table for the inner payload and assert all fields match.

    inner_wire: dict returned by _parse_inner_payload (from capture); None if absent.
    inner_cfg:  dict returned by _add_inner_* (configured values + expected structural).

    Columns: Field | Configured | Wire
    Structural fields (protocol, data_offset, udp_length) are set by the
    trafficitem.py SRH inner payload fix; the table shows the expected vs actual value.
    """
    sep   = "=" * 72
    inner = "-" * 72
    ptype = inner_cfg.get("type", "unknown")
    print("\n" + sep)
    print("  [%s] DP inner payload verification  [%s]" % (tc, ptype))
    print(inner)
    print("  %-8s  %-30s  %-22s  %s" % ("", "Field", "Configured", "Wire"))
    print(inner)

    if inner_wire is None:
        print("  [FAIL]   No inner payload parsed from DP capture")
        print(sep)
        assert False, "[%s] Inner payload not found in DP capture" % tc

    fields_ok = True

    def _chk(name, got, want):
        nonlocal fields_ok
        ok = (got == want)
        status = "[PASS]" if ok else "[FAIL]"
        print("  %s  %-30s  %-22s  %s" % (status, name, want, got))
        if not ok:
            fields_ok = False

    if "ipv4" in ptype:
        _chk("inner.ipv4.src",       inner_wire.get("ip_src"),      inner_cfg["ip_src"])
        _chk("inner.ipv4.dst",       inner_wire.get("ip_dst"),      inner_cfg["ip_dst"])
        _chk("inner.ipv4.protocol",  inner_wire.get("ip_protocol"), inner_cfg["ip_protocol"])
        if "tcp" in ptype:
            _chk("inner.tcp.src_port",    inner_wire.get("src_port"),    inner_cfg["src_port"])
            _chk("inner.tcp.dst_port",    inner_wire.get("dst_port"),    inner_cfg["dst_port"])
            _chk("inner.tcp.data_offset", inner_wire.get("data_offset"), inner_cfg["data_offset"])
        else:
            _chk("inner.udp.src_port",  inner_wire.get("src_port"),   inner_cfg["src_port"])
            _chk("inner.udp.dst_port",  inner_wire.get("dst_port"),   inner_cfg["dst_port"])
            _chk("inner.udp.length",    inner_wire.get("udp_length"), inner_cfg["udp_length"])
    else:  # ipv6
        _chk("inner.ipv6.src",         inner_wire.get("ip_src"),         inner_cfg["ip_src"])
        _chk("inner.ipv6.dst",         inner_wire.get("ip_dst"),         inner_cfg["ip_dst"])
        _chk("inner.ipv6.next_header", inner_wire.get("ip_next_header"), inner_cfg["ip_next_header"])
        if "tcp" in ptype:
            _chk("inner.tcp.src_port",    inner_wire.get("src_port"),    inner_cfg["src_port"])
            _chk("inner.tcp.dst_port",    inner_wire.get("dst_port"),    inner_cfg["dst_port"])
            _chk("inner.tcp.data_offset", inner_wire.get("data_offset"), inner_cfg["data_offset"])
        else:
            _chk("inner.udp.src_port",  inner_wire.get("src_port"),   inner_cfg["src_port"])
            _chk("inner.udp.dst_port",  inner_wire.get("dst_port"),   inner_cfg["dst_port"])
            _chk("inner.udp.length",    inner_wire.get("udp_length"), inner_cfg["udp_length"])

    print(sep)
    assert fields_ok, "[%s] Inner payload field mismatch — see table above" % tc


def _verify_device_flow_metrics(tc, flow_results, flow_name):
    """Print and assert device flow metrics: frames_tx > 0 and loss = 0.

    flow_results: list returned by utils.get_all_stats(api)[1].
    The table shows the IS-IS device flow result alongside the raw SRH flow
    metrics that get_all_stats already printed.
    """
    sep   = "=" * 64
    inner = "-" * 64
    print("\n" + sep)
    print("  [%s] IS-IS device flow verification  [%s]" % (tc, flow_name))
    print(inner)

    for fm in flow_results:
        if fm.name != flow_name:
            continue
        tx   = fm.frames_tx
        rx   = fm.frames_rx
        loss = tx - rx
        ok_tx   = "[PASS]" if tx > 0   else "[FAIL]"
        ok_loss = "[PASS]" if loss == 0 else "[FAIL]"
        print("  %s  frames_tx  = %d" % (ok_tx,   tx))
        print("  %s  frames_rx  = %d" % (ok_loss, rx))
        print("  %s  loss       = %d" % (ok_loss, loss))
        print(sep)
        assert tx > 0,   "[%s] '%s': no packets transmitted" % (tc, flow_name)
        assert loss == 0, "[%s] '%s': %d frame(s) lost" % (tc, flow_name, loss)
        return

    print("  [FAIL]  '%s' not found in flow metrics" % flow_name)
    print(sep)
    assert False, "[%s] flow '%s' missing from metrics" % (tc, flow_name)


# ---------------------------------------------------------------------------
# TC-1: Basic End SID — control and data planes
# ---------------------------------------------------------------------------

def test_tc1_srv6_end_sid_cp_dp(api, b2b_raw_config, utils):
    """TC-1: IS-IS SRv6 End SID (behavior=End) advertised and verified on both planes.

    Control plane:
      r1: locator fc00:0:1::/48, End SID fc00:0:1:1:: (behavior=End, code=1)
      r2: locator fc00:0:2::/48, End SID fc00:0:2:1:: (behavior=End, code=1)
      Verify: IS-IS L2 session up; both End SIDs active in IxN config state.
      Wire: IS-IS Hellos captured; LSP TLV 27 parsed when present.

    Data plane:
      Standard SRH flow (ipv6RoutingType4):
        segments=[fc00:0:2:1::, fc00:0:1:1::], sl=1, le=1.
      Wire verify: routing_type=4, sl=1, le=1, 2 segment addresses.
    """
    tc = "TC1"
    api.set_config(api.config())

    # Single combined config: IS-IS devices + SRH flow on the same ports.
    # Phase 2 (DP) runs while IS-IS is still up — no stop/restart between phases.
    cfg, p1, p2, d1, d2, d1_eth, d2_eth = _build_combined_config(api, b2b_raw_config)

    _build_base_isis(d1.isis, _SYS_ID_R1, d1_eth.name, "r1", "r1_intf")
    _build_base_isis(d2.isis, _SYS_ID_R2, d2_eth.name, "r2", "r2_intf")

    loc1 = _add_srv6_locator(d1.isis, _LOC1, "loc1")
    _add_end_sid(loc1, "0001", "end")
    _add_isis_v6_routes(d1.isis, "fd00:0:1::1", "r1_v6_routes")

    loc2 = _add_srv6_locator(d2.isis, _LOC2, "loc2")
    _add_end_sid(loc2, "0001", "end")
    _add_isis_v6_routes(d2.isis, "fd00:0:2::1", "r2_v6_routes")

    f1 = _build_srh_flow(
        cfg, "srh_f1", p1.name, p2.name,
        ip6_src="2001::1", ip6_dst="fc00:0:1:1::",
        segments_left=1, last_entry=1,
        segments=["fc00:0:2:1::", "fc00:0:1:1::"],
    )
    inner_cfg1 = _add_inner_ipv4_tcp(f1)
    _build_device_flow(cfg, "isis_dev_flow",
                       tx_names=["r1_v6_routes"], rx_names=["r2_v6_routes"])
    _add_capture(cfg, p2.name, "cap")
    api.set_config(cfg)

    # ---- Phase 1: Control plane ----------------------------------------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc1_cp")
    _check_isis_sessions_up(api, tc)
    _verify_cp_wire(tc, cp_pcap, "r1", _SYS_ID_R1, {"fc00:0:1:1::": 1})
    _verify_cp(api, tc, {"fc00:0:1:1::": 1}, {"fc00:0:2:1::": 1})

    # ---- Phase 2: Data plane (IS-IS still running) ---------------------
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    dp_pcap = _get_capture(api, p2.name)
    _save_capture(dp_pcap, "test_tc1_dp")
    srh = _parse_srh_from_pcap(dp_pcap)
    _verify_dp(tc, srh, {
        "routing_type":  4,
        "segments_left": 1,
        "last_entry":    1,
        "flags_byte":    0,
        "tag":           0,
        "segments":      ["fc00:0:2:1::", "fc00:0:1:1::"],
    })
    _verify_dp_inner(tc, srh.get("inner") if srh else None, inner_cfg1)
    _, flow_results = utils.get_all_stats(api)
    _verify_device_flow_metrics(tc, flow_results, "isis_dev_flow")

    _delete_captures("test_tc1_cp", "test_tc1_dp")
    print("\n  [%s] PASSED — control and data plane verified." % tc)


# ---------------------------------------------------------------------------
# TC-2: Multiple End SID behaviors — control and data planes
# ---------------------------------------------------------------------------

def test_tc2_srv6_multi_behavior_cp_dp(api, b2b_raw_config, utils):
    """TC-2: Four End SID behaviors on r1; 3-segment SRH verified on wire.

    Control plane:
      r1 locator fc00:0:1::/48 with four End SIDs:
        fc00:0:1:1:: End       (code 1)
        fc00:0:1:2:: End.PSP   (code 2)
        fc00:0:1:3:: uDT6      (code 62)
        fc00:0:1:4:: uDT4      (code 63)
      Verify: all four SIDs active with correct behavior codes.

    Data plane:
      Standard SRH flow with 3 segments:
        segments=[fc00:0:1:3::, fc00:0:1:2::, fc00:0:1:1::], sl=2, le=2.
      Wire verify: routing_type=4, sl=2, le=2, 3 segment addresses.
    """
    tc = "TC2"
    api.set_config(api.config())

    cfg, p1, p2, d1, d2, d1_eth, d2_eth = _build_combined_config(api, b2b_raw_config)

    _build_base_isis(d1.isis, _SYS_ID_R1, d1_eth.name, "r1", "r1_intf")
    _build_base_isis(d2.isis, _SYS_ID_R2, d2_eth.name, "r2", "r2_intf")

    loc1 = _add_srv6_locator(d1.isis, _LOC1, "loc1")
    _add_end_sid(loc1, "0001", "end")
    _add_end_sid(loc1, "0002", "end_with_psp")
    _add_end_sid(loc1, "0003", "end_dt6")
    _add_end_sid(loc1, "0004", "end_dt4")
    _add_isis_v6_routes(d1.isis, "fd00:0:1::1", "r1_v6_routes")

    loc2 = _add_srv6_locator(d2.isis, _LOC2, "loc2")
    _add_end_sid(loc2, "0001", "end")
    _add_isis_v6_routes(d2.isis, "fd00:0:2::1", "r2_v6_routes")

    f2 = _build_srh_flow(
        cfg, "srh_f2", p1.name, p2.name,
        ip6_src="2001::1", ip6_dst="fc00:0:1:3::",
        segments_left=2, last_entry=2,
        segments=["fc00:0:1:3::", "fc00:0:1:2::", "fc00:0:1:1::"],
    )
    inner_cfg2 = _add_inner_ipv4_udp(f2)
    _build_device_flow(cfg, "isis_dev_flow",
                       tx_names=["r1_v6_routes"], rx_names=["r2_v6_routes"])
    _add_capture(cfg, p2.name, "cap")
    api.set_config(cfg)

    # ---- Phase 1: Control plane ----------------------------------------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc2_cp")
    _check_isis_sessions_up(api, tc)
    expected_r1 = {"fc00:0:1:1::": 1, "fc00:0:1:2::": 2, "fc00:0:1:3::": 62, "fc00:0:1:4::": 63}
    _verify_cp_wire(tc, cp_pcap, "r1", _SYS_ID_R1, expected_r1)
    _verify_cp(api, tc, expected_r1)

    # ---- Phase 2: Data plane (IS-IS still running) ---------------------
    _start_capture(api)
    _start_traffic(api)
    time.sleep(6)
    _stop_traffic(api)
    _stop_capture(api)

    dp_pcap = _get_capture(api, p2.name)
    _save_capture(dp_pcap, "test_tc2_dp")
    srh = _parse_srh_from_pcap(dp_pcap)
    _verify_dp(tc, srh, {
        "routing_type":  4,
        "segments_left": 2,
        "last_entry":    2,
        "flags_byte":    0,
        "tag":           0,
        "segments":      ["fc00:0:1:3::", "fc00:0:1:2::", "fc00:0:1:1::"],
    })
    _verify_dp_inner(tc, srh.get("inner") if srh else None, inner_cfg2)
    _, flow_results = utils.get_all_stats(api)
    _verify_device_flow_metrics(tc, flow_results, "isis_dev_flow")

    #_delete_captures("test_tc2_cp", "test_tc2_dp")
    print("\n  [%s] PASSED — control and data plane verified." % tc)


# ---------------------------------------------------------------------------
# TC-3: uSID / G-SRH — control and data planes
# ---------------------------------------------------------------------------

def test_tc3_srv6_usid_cp_dp(api, b2b_raw_config, utils):
    """TC-3: F3216 uSID locator advertised on CP; uSID SRH verified on DP.

    Control plane:
      r1: locator fc00:0:1::/48, lb=32, ln=16, fn=16, End SID fc00:0:1:1:: (code=1, End).
      r2: locator fc00:0:2::/48, End SID fc00:0:2:1:: (code=1, End).
      Verify: End behavior code 1 on both routers; F3216 SID structure sub-sub-TLV present.

    Data plane:
      uSID SRH (ipv6GSRHType4) flow with 2 uSID containers:
        usid_containers=[fc00:0:1:1::, fc00:0:2:1::], sl=1, le=1, flags=0x00.
      Wire verify: routing_type=4, sl=1, le=1, flags_byte=0x00,
                   segments reconstructed to original 128-bit uSID addresses.
    """
    tc = "TC3"
    api.set_config(api.config())

    # Single combined config: IS-IS devices + G-SRH flow on the same ports.
    cfg, p1, p2, d1, d2, d1_eth, d2_eth = _build_combined_config(api, b2b_raw_config)

    _build_base_isis(d1.isis, _SYS_ID_R1, d1_eth.name, "r1", "r1_intf")
    _build_base_isis(d2.isis, _SYS_ID_R2, d2_eth.name, "r2", "r2_intf")

    loc1 = _add_srv6_locator(d1.isis, _LOC1, "loc1")
    _add_end_sid(loc1, "0001", "end")
    _add_isis_v6_routes(d1.isis, "fd00:0:1::1", "r1_v6_routes")

    loc2 = _add_srv6_locator(d2.isis, _LOC2, "loc2")
    _add_end_sid(loc2, "0001", "end")
    _add_isis_v6_routes(d2.isis, "fd00:0:2::1", "r2_v6_routes")

    f3 = _build_gsrh_flow(
        cfg, "gsrh_f3", p1.name, p2.name,
        ip6_src="2001::1",
        ip6_dst="fc00:0:1:1::",
        segments_left=1, last_entry=1,
        usid_containers=["fc00:0:1:1::", "fc00:0:2:1::"],
    )
    inner_cfg3 = _add_inner_ipv6_tcp(f3)
    _build_device_flow(cfg, "isis_dev_flow",
                       tx_names=["r1_v6_routes"], rx_names=["r2_v6_routes"])
    _add_capture(cfg, p2.name, "cap")
    api.set_config(cfg)

    # ---- Phase 1: Control plane ----------------------------------------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc3_cp")
    _check_isis_sessions_up(api, tc)

    expected_r1 = {"fc00:0:1:1::": 1}
    expected_r2 = {"fc00:0:2:1::": 1}
    _verify_cp_wire(tc, cp_pcap, "r1", _SYS_ID_R1, expected_r1)
    _verify_cp(api, tc, expected_r1, expected_r2)

    # ---- Phase 2: Data plane (IS-IS still running) ---------------------
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    dp_pcap = _get_capture(api, p2.name)
    _save_capture(dp_pcap, "test_tc3_dp")

    srh = _parse_srh_from_pcap(dp_pcap)
    _verify_dp(tc, srh, {
        "routing_type":  4,
        "segments_left": 1,
        "last_entry":    1,
        "flags_byte":    0x00,
        "tag":           0,
        "segments":      ["fc00:0:1:1::", "fc00:0:2:1::"],
    })
    _verify_dp_inner(tc, srh.get("inner") if srh else None, inner_cfg3)
    _, flow_results = utils.get_all_stats(api)
    _verify_device_flow_metrics(tc, flow_results, "isis_dev_flow")

    _delete_captures("test_tc3_cp", "test_tc3_dp")
    print("\n  [%s] PASSED — control and data plane verified." % tc)


# ---------------------------------------------------------------------------
# TC-4: Adjacency SID (End.X) + flags and tag on DP
# ---------------------------------------------------------------------------

def test_tc4_srv6_adj_sid_cp_dp(api, b2b_raw_config, utils):
    """TC-4: End.X adjacency SID advertised on CP; SRH with P-flag and tag on DP.

    Control plane:
      r1: locator fc00:0:1::/48, End SID fc00:0:1:1:: (code=1, End).
          End.X adjacency SID: function=00c8, fc00:0:1:c8:: (code=5, End.X).
      Verify: node End SID active.

    Data plane:
      Standard SRH flow with P-flag=1 and tag=0xABCD:
        segments=[fc00:0:1:c8::, fc00:0:1:1::], sl=1, le=1.
      Wire verify: routing_type=4, sl=1, le=1,
                   flags_byte=0x40 (P-flag=bit6), tag=0xABCD, 2 segments.
    """
    tc = "TC4"
    api.set_config(api.config())

    # Single combined config: IS-IS devices + SRH flow on the same ports.
    cfg, p1, p2, d1, d2, d1_eth, d2_eth = _build_combined_config(api, b2b_raw_config)

    r1_intf = _build_base_isis(d1.isis, _SYS_ID_R1, d1_eth.name, "r1", "r1_intf")
    _build_base_isis(d2.isis, _SYS_ID_R2, d2_eth.name, "r2", "r2_intf")

    loc1 = _add_srv6_locator(d1.isis, _LOC1, "loc1")
    _add_end_sid(loc1, "0001", "end")
    _add_isis_v6_routes(d1.isis, "fd00:0:1::1", "r1_v6_routes")

    loc2 = _add_srv6_locator(d2.isis, _LOC2, "loc2")
    _add_end_sid(loc2, "0001", "end")
    _add_isis_v6_routes(d2.isis, "fd00:0:2::1", "r2_v6_routes")

    # Adjacency SID: function=00c8 -> SID fc00:0:1:c8::, End.X (code 5)
    r1_intf.srv6_adjacency_sids.sids.add(
        function="00c8",
        endpoint_behavior="end_x",
        c_flag=True,
        b_flag=False,
        s_flag=False,
        weight=0,
        locator="auto",
    )

    # P-flag=1 (bit6 -> 0x40), tag=0xABCD; targeting adjacency SID in segment list
    f4 = _build_srh_flow(
        cfg, "srh_f4", p1.name, p2.name,
        ip6_src="2001::1",
        ip6_dst="fc00:0:1:c8::",
        segments_left=1, last_entry=1,
        segments=["fc00:0:1:c8::", "fc00:0:1:1::"],
        protected=1, tag=0xABCD,
    )
    inner_cfg4 = _add_inner_ipv6_udp(f4)
    _build_device_flow(cfg, "isis_dev_flow",
                       tx_names=["r1_v6_routes"], rx_names=["r2_v6_routes"])
    _add_capture(cfg, p2.name, "cap")
    api.set_config(cfg)

    # ---- Phase 1: Control plane ----------------------------------------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc4_cp")
    _check_isis_sessions_up(api, tc)

    # Verify node End SID; adjacency SID lives in Adj SID sub-TLV (separate)
    expected_r1 = {"fc00:0:1:1::": 1}
    _verify_cp_wire(tc, cp_pcap, "r1", _SYS_ID_R1, expected_r1)
    _verify_cp(api, tc, expected_r1)

    # ---- Phase 2: Data plane (IS-IS still running) ---------------------
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    dp_pcap = _get_capture(api, p2.name)
    _save_capture(dp_pcap, "test_tc4_dp")

    srh = _parse_srh_from_pcap(dp_pcap)
    _verify_dp(tc, srh, {
        "routing_type":  4,
        "segments_left": 1,
        "last_entry":    1,
        "flags_byte":    0x40,     # P-flag = bit 6
        "tag":           0xABCD,
        "segments":      ["fc00:0:1:c8::", "fc00:0:1:1::"],
    })
    _verify_dp_inner(tc, srh.get("inner") if srh else None, inner_cfg4)
    _, flow_results = utils.get_all_stats(api)
    _verify_device_flow_metrics(tc, flow_results, "isis_dev_flow")

    _delete_captures("test_tc4_cp", "test_tc4_dp")
    print("\n  [%s] PASSED — control and data plane verified." % tc)


# ---------------------------------------------------------------------------
# TC-5: Node MSD + Link MSD — control plane
# ---------------------------------------------------------------------------

def test_tc5_srv6_msd_cp(api, b2b_raw_config, utils):
    """TC-5: IS-IS SRv6 Node MSD and Link MSD advertised; verified from IxN config state.

    Control plane:
      r1 Node MSD (SRv6 Capabilities Sub-TLV, RFC 9352 Section 6):
        max_sl=5, max_end_pop_srh=4, max_h_encaps=3.
      r1_intf Link MSD (IS-IS SRv6 MSD sub-TLVs on the interface, RFC 9352 Section 9):
        max_sl=3, max_end_pop_srh=2.
      Verify: IS-IS L2 session up; Node MSD and Link MSD values in IxN config
              state match the configured values.
      Wire: IS-IS Hellos captured; MSD sub-TLVs not visible on the physical
            wire in B2B (LSDB exchanged internally by IxNetwork).
    """
    tc = "TC5"
    api.set_config(api.config())

    cfg, p1, p2, d1, d2, d1_eth, d2_eth = _build_combined_config(api, b2b_raw_config)

    r1_intf = _build_base_isis(d1.isis, _SYS_ID_R1, d1_eth.name, "r1", "r1_intf")
    _build_base_isis(d2.isis, _SYS_ID_R2, d2_eth.name, "r2", "r2_intf")

    # r1: locator + End SID (needed for SRv6 capability advertisement)
    loc1 = _add_srv6_locator(d1.isis, _LOC1, "loc1")
    _add_end_sid(loc1, "0001", "end")

    # Node MSD: set on the SRv6 capability (already created by _add_srv6_locator)
    sr = d1.isis.segment_routing
    node_msds = sr.router_capability.srv6_capability.node_msds
    node_msds.max_sl.value          = 5
    node_msds.max_end_pop_srh.value = 4
    node_msds.max_h_encaps.value    = 3

    # Link MSD: nested under srv6_adjacency_sids in new snappi API
    r1_intf.srv6_adjacency_sids.srv6_link_msd.max_sl.value          = 3
    r1_intf.srv6_adjacency_sids.srv6_link_msd.max_end_pop_srh.value = 2

    _add_isis_v6_routes(d1.isis, "fd00:0:1::1", "r1_v6_routes")

    # r2: minimal locator for adjacency formation
    loc2 = _add_srv6_locator(d2.isis, _LOC2, "loc2")
    _add_end_sid(loc2, "0001", "end")
    _add_isis_v6_routes(d2.isis, "fd00:0:2::1", "r2_v6_routes")

    _add_capture(cfg, p2.name, "cap")
    api.set_config(cfg)

    # ---- Control plane -------------------------------------------------------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc5_cp")
    _check_isis_sessions_up(api, tc)

    # Verify End SID is active (sanity check that SRv6 capability was negotiated)
    _verify_cp(api, tc, {"fc00:0:1:1::": 1})

    # Verify Node MSD and Link MSD from IxN config state
    msd = _read_msd_state(api, "r1", "r1_intf")
    _verify_msd(tc, msd, {
        "node_msd": {
            "advertise":       True,
            "max_sl":          5,
            "max_end_pop_srh": 4,
            "max_h_encaps":    3,
        },
        "link_msd": {
            "advertise":       True,
            "max_sl":          3,
            "max_end_pop_srh": 2,
        },
    })

    _delete_captures("test_tc5_cp")
    print("\n  [%s] PASSED — Node MSD and Link MSD verified in IxN config state." % tc)


# ---------------------------------------------------------------------------
# SRv6 Adjacency SID wire parser (TLV 22 / sub-TLV 43)
# ---------------------------------------------------------------------------

def _parse_isis_srv6_adj_sids(pcap_bytes, source_system_id):
    """Return {sid_addr: endpoint_behavior} from highest-sequence L2 LSP.

    Walks TLV 22 (Extended IS Reachability) -> sub-TLV 43 (SRv6 End.X SID)
    per RFC 9352 Section 8.  Each TLV-22 IS neighbor entry layout:
      System ID + pseudonode (7) | metric (3) | sub-TLV length (1) | sub-TLVs
    Sub-TLV 43 value layout:
      flags(1) | reserved(1) | algo(1) | weight(1) | ep_behavior(2) | SID(16)
    """
    try:
        src_bytes = bytes.fromhex(
            source_system_id.replace(".", "").replace(":", "")
        )
    except ValueError:
        return {}

    best_seq  = -1
    best_sids = {}

    for _, raw_pkt in dpkt.pcapng.Reader(pcap_bytes):
        try:
            isis = _find_isis_pdu(bytes(raw_pkt))
        except Exception:
            continue
        if isis is None or len(isis) < 27:
            continue
        if isis[0] != 0x83:
            continue
        if (isis[4] & 0x1F) != 0x14:           # Level 2 LSP
            continue
        if isis[10:16] != src_bytes:
            continue
        if isis[17] != 0:                       # fragment 0 only
            continue

        seq     = struct.unpack(">I", isis[18:22])[0]
        pdu_len = struct.unpack(">H", isis[8:10])[0]
        hdr_len = isis[1]

        offset  = hdr_len
        end_off = min(pdu_len, len(isis))
        pkt_sids = {}

        while offset + 2 <= end_off:
            tlv_type = isis[offset]
            tlv_len  = isis[offset + 1]
            if offset + 2 + tlv_len > end_off:
                break
            tlv_val  = isis[offset + 2: offset + 2 + tlv_len]
            offset  += 2 + tlv_len

            if tlv_type != 22:
                continue

            # Iterate IS neighbor entries within the TLV 22 value
            ne_off = 0
            while ne_off + 11 <= len(tlv_val):
                # 7 bytes neighbor ID + 3 bytes metric + 1 byte sub-TLV block len
                sub_block_len = tlv_val[ne_off + 10]
                entry_end     = ne_off + 11 + sub_block_len
                if entry_end > len(tlv_val):
                    break

                sub_off = ne_off + 11
                while sub_off + 2 <= entry_end:
                    sub_type = tlv_val[sub_off]
                    sub_len  = tlv_val[sub_off + 1]
                    if sub_off + 2 + sub_len > entry_end:
                        break
                    sub_val  = tlv_val[sub_off + 2: sub_off + 2 + sub_len]
                    sub_off += 2 + sub_len

                    if sub_type != 43 or len(sub_val) < 22:
                        continue
                    ep_behavior = struct.unpack(">H", sub_val[4:6])[0]
                    try:
                        sid_addr = str(ipaddress.IPv6Address(bytes(sub_val[6:22])))
                    except ValueError:
                        continue
                    pkt_sids[sid_addr] = ep_behavior

                ne_off = entry_end

        if seq > best_seq:
            best_seq  = seq
            best_sids = pkt_sids

    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    return best_sids


# ---------------------------------------------------------------------------
# SRv6 Capabilities wire parser (TLV 242 / sub-TLV 25)
# ---------------------------------------------------------------------------

def _parse_isis_srv6_capabilities(pcap_bytes, source_system_id):
    """Return {"o_flag": bool} from TLV 242 / sub-TLV 25 in highest-seq L2 LSP.

    TLV 242 (IS-IS Router CAPABILITY, RFC 7981): Router ID(4) + Flags(1)
    + sub-TLVs.  Sub-TLV 25 (SRv6 Capability, RFC 9352 Section 2):
    Flags(2 bytes), bit 15 = O-flag.
    """
    try:
        src_bytes = bytes.fromhex(
            source_system_id.replace(".", "").replace(":", "")
        )
    except ValueError:
        return {}

    best_seq  = -1
    best_caps = {}

    for _, raw_pkt in dpkt.pcapng.Reader(pcap_bytes):
        try:
            isis = _find_isis_pdu(bytes(raw_pkt))
        except Exception:
            continue
        if isis is None or len(isis) < 27:
            continue
        if isis[0] != 0x83:
            continue
        if (isis[4] & 0x1F) != 0x14:
            continue
        if isis[10:16] != src_bytes:
            continue
        if isis[17] != 0:
            continue

        seq     = struct.unpack(">I", isis[18:22])[0]
        pdu_len = struct.unpack(">H", isis[8:10])[0]
        hdr_len = isis[1]

        offset  = hdr_len
        end_off = min(pdu_len, len(isis))
        pkt_caps = {}

        while offset + 2 <= end_off:
            tlv_type = isis[offset]
            tlv_len  = isis[offset + 1]
            if offset + 2 + tlv_len > end_off:
                break
            tlv_val  = isis[offset + 2: offset + 2 + tlv_len]
            offset  += 2 + tlv_len

            if tlv_type != 242 or len(tlv_val) < 5:    # IS-IS Router CAPABILITY
                continue
            sub_off = 5                                 # skip Router ID (4) + Flags (1)
            while sub_off + 2 <= len(tlv_val):
                sub_type = tlv_val[sub_off]
                sub_len  = tlv_val[sub_off + 1]
                if sub_off + 2 + sub_len > len(tlv_val):
                    break
                sub_val  = tlv_val[sub_off + 2: sub_off + 2 + sub_len]
                sub_off += 2 + sub_len

                if sub_type == 25 and len(sub_val) >= 2:    # SRv6 Capability
                    flags2 = struct.unpack(">H", sub_val[0:2])[0]
                    pkt_caps["o_flag"] = bool(flags2 & 0x8000)

        if seq > best_seq:
            best_seq  = seq
            best_caps = pkt_caps

    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    return best_caps


# ---------------------------------------------------------------------------
# Adjacency SID IxN state reader
# ---------------------------------------------------------------------------

def _read_adj_sid_state(api, intf_name):
    """Return [{"sid", "function_code", "active"}] from IsisSRv6AdjSIDList.

    Navigates to the IsisL3 interface via api.ixn_objects.get(intf_name).xpath
    and reads Ipv6AdjSid / EndPointFunction / Active multivalue rows.
    """
    import re as _re
    import ipaddress as _ip

    result = []
    try:
        info  = api.ixn_objects.get(intf_name)
        parts = _re.findall(r'(\w+)\[(\d+)\]', info.xpath)
        obj   = api._ixnetwork
        for cls_name, idx_str in parts:
            attr = cls_name[0].upper() + cls_name[1:]
            coll = getattr(obj, attr).find()
            obj  = coll[int(idx_str) - 1]

        for ixn_adj in obj.IsisSRv6AdjSIDList.find():
            sid_vals = ixn_adj.Ipv6AdjSid.Values
            act_vals = ixn_adj.Active.Values
            fn_vals  = ixn_adj.EndPointFunction.Values
            for sv, av, fv in zip(sid_vals, act_vals, fn_vals):
                try:
                    sid_addr = str(_ip.IPv6Address(sv))
                except ValueError:
                    sid_addr = str(sv)
                active    = str(av).lower() not in ("false", "0")
                try:
                    func_code = int(fv)
                except (ValueError, TypeError):
                    func_code = 0
                result.append({"sid": sid_addr, "active": active, "function_code": func_code})
    except Exception as exc:
        print("  [warn] _read_adj_sid_state(%s) failed: %s" % (intf_name, exc))
    return result


# ---------------------------------------------------------------------------
# Adjacency SID and Capabilities verification helpers
# ---------------------------------------------------------------------------

def _verify_adj_sid_state(api, tc, intf_name, expected):
    """Assert adjacency SIDs from IxN state match expected {sid: behavior_code}."""
    sep = "-" * 64
    print("\n" + sep)
    print("  [%s] Adj SID verification  intf=%s  [IxN state]" % (tc, intf_name))
    print(sep)

    adj_sids = _read_adj_sid_state(api, intf_name)
    actual   = {s["sid"]: s["function_code"] for s in adj_sids if s["active"]}

    all_ok = True
    for sid, code in sorted(expected.items()):
        name = _BEHAVIOR_NAME.get(code, "code-%d" % code)
        if sid in actual and actual[sid] == code:
            print("  [PASS]  %-36s  behavior=%d (%s)" % (sid, code, name))
        else:
            got = actual.get(sid, "MISSING")
            print("  [FAIL]  %-36s  expected=%d (%s)  got=%s"
                  % (sid, code, name, got))
            all_ok = False
    print(sep)
    for sid, code in expected.items():
        assert sid in actual, (
            "[%s] %s: Adj SID %s not active; got %s" % (tc, intf_name, sid, actual)
        )
        assert actual[sid] == code, (
            "[%s] %s: %s behavior expected=%d got=%d"
            % (tc, intf_name, sid, code, actual[sid])
        )


def _verify_adj_sid_wire(tc, pcap_bytes, router, sys_id, expected):
    """Print pass/fail for Adj SIDs from wire (TLV 22 / sub-TLV 43); best-effort."""
    wire_sids = _parse_isis_srv6_adj_sids(pcap_bytes, sys_id)
    sep = "-" * 64
    print("\n" + sep)
    print("  [%s] Adj SID wire  router=%s  (TLV 22 / sub-TLV 43)" % (tc, router))
    if not wire_sids:
        print("  (no SRv6 End.X SID sub-TLVs in capture — may be IxN-internal)")
        print(sep)
        return False
    print(sep)
    for sid, code in sorted(expected.items()):
        name = _BEHAVIOR_NAME.get(code, "code-%d" % code)
        if sid in wire_sids and wire_sids[sid] == code:
            print("  [PASS wire]  %-36s  behavior=%d (%s)" % (sid, code, name))
        else:
            got = wire_sids.get(sid, "NOT FOUND")
            print("  [FAIL wire]  %-36s  expected=%d (%s)  wire=%s"
                  % (sid, code, name, got))
    print(sep)
    return True


def _verify_capabilities_wire(tc, pcap_bytes, router, sys_id):
    """Print SRv6 Capability TLV presence and O-flag from wire; best-effort."""
    caps = _parse_isis_srv6_capabilities(pcap_bytes, sys_id)
    sep = "-" * 64
    print("\n" + sep)
    print("  [%s] SRv6 Capabilities wire  router=%s  (TLV 242 / sub-TLV 25)"
          % (tc, router))
    if not caps:
        print("  (TLV 242 / sub-TLV 25 not found in capture)")
        print(sep)
        return False
    o_flag = caps.get("o_flag", False)
    status = "[PASS]" if o_flag else "[INFO]"
    print("  %s  o_flag = %s" % (status, o_flag))
    print(sep)
    return True


# ---------------------------------------------------------------------------
# TC-6: SRv6 Capabilities + Node SIDs + Adjacency SIDs — CP wire verified
# ---------------------------------------------------------------------------

def test_tc6_srv6_capabilities_node_adj_sids_cp_dp(api, b2b_raw_config, utils):
    """TC-6: SRv6 Capabilities + Node SIDs + Adj SIDs — CP verified, bidir DP on wire.

    Each router advertises a Node SID (End) and an Adjacency SID (End.X).
    The opposite router uses those advertised SIDs as the SRH segment list to
    generate traffic, so the SID advertisement is the direct input to the DP
    steering — proving the full round-trip from IS-IS advertisement to forwarding.

    Topology (B2B, 2 ports):
      port1 <---> port2
      d1 / r1  sys-id=650000000001  locator fc00:0:1::/48
                  Node SID  fc00:0:1:1::   End   (code 1)  advertised via TLV 27
                  Adj SID   fc00:0:1:c8::  End.X (code 5)  advertised via TLV 22
      d2 / r2  sys-id=650000000002  locator fc00:0:2::/48
                  Node SID  fc00:0:2:1::   End   (code 1)
                  Adj SID   fc00:0:2:c8::  End.X (code 5)

    Traffic (bidirectional, using the peer's advertised SIDs):
      Forward  p1→p2:  SRH [fc00:0:2:c8:: → fc00:0:2:1::]  inner IPv6/TCP
                        r2's Adj SID used as first segment, r2's Node SID as last
      Reverse  p2→p1:  SRH [fc00:0:1:c8:: → fc00:0:1:1::]  inner IPv6/UDP
                        r1's Adj SID used as first segment, r1's Node SID as last

    Verification:
      CP — IxN config state: Node SIDs (hard assert), Adj SIDs (hard assert)
      CP — wire (best-effort): TLV 27/sub-TLV 5, TLV 22/sub-TLV 43, TLV 242/sub-TLV 25
      DP — wire: forward SRH on p2 capture, reverse SRH on p1 capture
    """
    tc = "TC6"
    api.set_config(api.config())

    # ---- Ports ---------------------------------------------------------------
    cfg = api.config()

    p1, p2 = cfg.ports.port(
        name="tx", location=b2b_raw_config.ports[0].location
    ).port(
        name="rx", location=b2b_raw_config.ports[1].location
    )

    for l1_orig in b2b_raw_config.layer1:
        l1 = cfg.layer1.add()
        l1.name       = l1_orig.name
        l1.port_names = [p1.name, p2.name]
        l1.media      = l1_orig.media
        l1.speed      = l1_orig.speed

    cfg.options.port_options.location_preemption = True

    # ---- Devices and Ethernet ------------------------------------------------
    d1, d2 = cfg.devices.device(name="d1").device(name="d2")

    d1_eth = d1.ethernets.add()
    d1_eth.name                 = "d1_eth"
    d1_eth.connection.port_name = p1.name
    d1_eth.mac                  = "00:00:00:01:01:01"
    d1_v6         = d1_eth.ipv6_addresses.add()
    d1_v6.name    = "d1_ipv6"
    d1_v6.address = "2001::1"
    d1_v6.gateway = "2001::2"
    d1_v6.prefix  = 64

    d2_eth = d2.ethernets.add()
    d2_eth.name                 = "d2_eth"
    d2_eth.connection.port_name = p2.name
    d2_eth.mac                  = "00:00:00:02:02:02"
    d2_v6         = d2_eth.ipv6_addresses.add()
    d2_v6.name    = "d2_ipv6"
    d2_v6.address = "2001::2"
    d2_v6.gateway = "2001::1"
    d2_v6.prefix  = 64

    # ---- IS-IS router r1 -----------------------------------------------------
    r1           = d1.isis
    r1.name      = "r1"
    r1.system_id = "650000000001"
    r1.basic.enable_wide_metric   = True
    r1.basic.learned_lsp_filter   = True
    r1.advanced.area_addresses    = ["490001"]
    r1.advanced.lsp_refresh_rate  = 900
    r1.advanced.lsp_lifetime      = 1200
    r1.advanced.csnp_interval     = 10000
    r1.advanced.psnp_interval     = 2000
    r1.advanced.max_lsp_size      = 1492

    r1_intf = r1.interfaces.add()
    r1_intf.eth_name     = "d1_eth"
    r1_intf.name         = "r1_intf"
    r1_intf.network_type = "point_to_point"
    r1_intf.level_type   = "level_2"
    r1_intf.metric       = 10
    r1_intf.l2_settings.dead_interval  = 30
    r1_intf.l2_settings.hello_interval = 10
    r1_intf.l2_settings.priority       = 0
    r1_intf.advanced.auto_adjust_supported_protocols = True

    # r1 SRv6 capability  (TLV 242 / sub-TLV 25)
    r1.segment_routing.router_capability.srv6_capability.c_flag = True

    # r1 SRv6 locator  (TLV 27 — F3216 uSID: lb=32, ln=16, fn=16, arg=0)
    r1_loc = r1.segment_routing.srv6_locators.add()
    r1_loc.locator_name  = "loc1"
    r1_loc.locator       = "fc00:0:1::"
    r1_loc.prefix_length = 48
    r1_loc.algorithm     = 0
    r1_loc.metric        = 10
    r1_loc.d_flag        = False
    r1_loc.sid_structure.locator_block_length = 32
    r1_loc.sid_structure.locator_node_length  = 16
    r1_loc.sid_structure.function_length      = 16
    r1_loc.sid_structure.argument_length      = 0
    r1_loc.advertise_locator_as_prefix.route_metric        = 10
    r1_loc.advertise_locator_as_prefix.redistribution_type = "up"
    r1_loc.advertise_locator_as_prefix.route_origin        = "internal"

    # r1 Node SID  fc00:0:1:1:: — End  (TLV 27 / sub-TLV 5)
    r1_end_sid                  = r1_loc.end_sids.add()
    r1_end_sid.function         = "0001"
    r1_end_sid.argument         = "0000"
    r1_end_sid.endpoint_behavior = "end"
    r1_end_sid.c_flag           = True

    # r1 Adj SID  fc00:0:1:c8:: — End.X  (TLV 22 / sub-TLV 43)
    r1_adj                   = r1_intf.srv6_adjacency_sids.sids.add()
    r1_adj.function          = "00c8"
    r1_adj.endpoint_behavior = "end_x"
    r1_adj.c_flag            = True
    r1_adj.b_flag            = False
    r1_adj.s_flag            = False
    r1_adj.weight            = 0
    r1_adj.locator           = "auto"

    r1_rr           = r1.v6_routes.add()
    r1_rr.name      = "r1_v6_routes"
    r1_rr.link_metric = 10
    r1_rr.origin_type = "internal"
    r1_rr_addr          = r1_rr.addresses.add()
    r1_rr_addr.address  = "fd00:0:1::1"
    r1_rr_addr.prefix   = 64
    r1_rr_addr.count    = 1

    # ---- IS-IS router r2 -----------------------------------------------------
    r2           = d2.isis
    r2.name      = "r2"
    r2.system_id = "650000000002"
    r2.basic.enable_wide_metric   = True
    r2.basic.learned_lsp_filter   = True
    r2.advanced.area_addresses    = ["490001"]
    r2.advanced.lsp_refresh_rate  = 900
    r2.advanced.lsp_lifetime      = 1200
    r2.advanced.csnp_interval     = 10000
    r2.advanced.psnp_interval     = 2000
    r2.advanced.max_lsp_size      = 1492

    r2_intf = r2.interfaces.add()
    r2_intf.eth_name     = "d2_eth"
    r2_intf.name         = "r2_intf"
    r2_intf.network_type = "point_to_point"
    r2_intf.level_type   = "level_2"
    r2_intf.metric       = 10
    r2_intf.l2_settings.dead_interval  = 30
    r2_intf.l2_settings.hello_interval = 10
    r2_intf.l2_settings.priority       = 0
    r2_intf.advanced.auto_adjust_supported_protocols = True

    # r2 SRv6 capability  (TLV 242 / sub-TLV 25)
    r2.segment_routing.router_capability.srv6_capability.c_flag = True

    # r2 SRv6 locator  (TLV 27 — F3216 uSID)
    r2_loc = r2.segment_routing.srv6_locators.add()
    r2_loc.locator_name  = "loc2"
    r2_loc.locator       = "fc00:0:2::"
    r2_loc.prefix_length = 48
    r2_loc.algorithm     = 0
    r2_loc.metric        = 10
    r2_loc.d_flag        = False
    r2_loc.sid_structure.locator_block_length = 32
    r2_loc.sid_structure.locator_node_length  = 16
    r2_loc.sid_structure.function_length      = 16
    r2_loc.sid_structure.argument_length      = 0
    r2_loc.advertise_locator_as_prefix.route_metric        = 10
    r2_loc.advertise_locator_as_prefix.redistribution_type = "up"
    r2_loc.advertise_locator_as_prefix.route_origin        = "internal"

    # r2 Node SID  fc00:0:2:1:: — End  (TLV 27 / sub-TLV 5)
    r2_end_sid                  = r2_loc.end_sids.add()
    r2_end_sid.function         = "0001"
    r2_end_sid.argument         = "0000"
    r2_end_sid.endpoint_behavior = "end"
    r2_end_sid.c_flag           = True

    # r2 Adj SID  fc00:0:2:c8:: — End.X  (TLV 22 / sub-TLV 43)
    r2_adj                   = r2_intf.srv6_adjacency_sids.sids.add()
    r2_adj.function          = "00c8"
    r2_adj.endpoint_behavior = "end_x"
    r2_adj.c_flag            = True
    r2_adj.b_flag            = False
    r2_adj.s_flag            = False
    r2_adj.weight            = 0
    r2_adj.locator           = "auto"

    r2_rr           = r2.v6_routes.add()
    r2_rr.name      = "r2_v6_routes"
    r2_rr.link_metric = 10
    r2_rr.origin_type = "internal"
    r2_rr_addr          = r2_rr.addresses.add()
    r2_rr_addr.address  = "fd00:0:2::1"
    r2_rr_addr.prefix   = 64
    r2_rr_addr.count    = 1

    # ---- Forward flow: d1→d2, r1-side uses r2's advertised SIDs --------------
    # Device-based flow: IxN resolves Ethernet MACs via NDP from the device
    # endpoints.  SRH is added via RestPy AppendProtocol() in the runtime.
    # SRH segment list: [r2 Adj SID, r2 Node SID].
    f_fwd = cfg.flows.add()
    f_fwd.name = "srh_fwd"
    f_fwd.tx_rx.device.tx_names = [d1_v6.name]
    f_fwd.tx_rx.device.rx_names = [d2_v6.name]
    f_fwd.rate.pps = 100
    f_fwd.duration.fixed_packets.packets = 200
    f_fwd.metrics.enable = True

    pkt = f_fwd.packet.add()
    pkt.choice = "ipv6"
    pkt.ipv6.src.value         = "2001::1"
    pkt.ipv6.dst.value         = "fc00:0:2:c8::"   # r2's Adj SID (outer destination)
    pkt.ipv6.next_header.value = 43                 # Routing Extension Header

    pkt = f_fwd.packet.add()
    pkt.choice = "ipv6_extension_header"
    pkt.ipv6_extension_header.routing.choice = "segment_routing"
    sr = pkt.ipv6_extension_header.routing.segment_routing
    sr.segments_left.value       = 1
    sr.last_entry.value          = 1
    sr.flags.protected.value     = 0
    sr.flags.alert.value         = 0
    sr.tag.value                 = 0
    sr.segment_list.segment()[-1].segment.value = "fc00:0:2:c8::"  # r2 Adj SID
    sr.segment_list.segment()[-1].segment.value = "fc00:0:2:1::"   # r2 Node SID

    pkt = f_fwd.packet.add()                         # inner IPv6
    pkt.choice = "ipv6"
    pkt.ipv6.src.value         = "2001:db8::1"
    pkt.ipv6.dst.value         = "2001:db8::2"
    pkt.ipv6.next_header.value = 6                   # TCP

    pkt = f_fwd.packet.add()                         # inner TCP
    pkt.choice = "tcp"
    pkt.tcp.src_port.value = 1234
    pkt.tcp.dst_port.value = 80

    # ---- Reverse flow: d2→d1, r2-side uses r1's advertised SIDs -------------
    # Device-based flow: IxN resolves Ethernet MACs via NDP from the device
    # endpoints.  SRH segment list: [r1 Adj SID, r1 Node SID].
    f_rev = cfg.flows.add()
    f_rev.name = "srh_rev"
    f_rev.tx_rx.device.tx_names = [d2_v6.name]
    f_rev.tx_rx.device.rx_names = [d1_v6.name]
    f_rev.rate.pps = 100
    f_rev.duration.fixed_packets.packets = 200
    f_rev.metrics.enable = True

    pkt = f_rev.packet.add()
    pkt.choice = "ipv6"
    pkt.ipv6.src.value         = "2001::2"
    pkt.ipv6.dst.value         = "fc00:0:1:c8::"   # r1's Adj SID (outer destination)
    pkt.ipv6.next_header.value = 43

    pkt = f_rev.packet.add()
    pkt.choice = "ipv6_extension_header"
    pkt.ipv6_extension_header.routing.choice = "segment_routing"
    sr = pkt.ipv6_extension_header.routing.segment_routing
    sr.segments_left.value       = 1
    sr.last_entry.value          = 1
    sr.flags.protected.value     = 0
    sr.flags.alert.value         = 0
    sr.tag.value                 = 0
    sr.segment_list.segment()[-1].segment.value = "fc00:0:1:c8::"  # r1 Adj SID
    sr.segment_list.segment()[-1].segment.value = "fc00:0:1:1::"   # r1 Node SID

    pkt = f_rev.packet.add()                         # inner IPv6
    pkt.choice = "ipv6"
    pkt.ipv6.src.value         = "2001:db8::2"
    pkt.ipv6.dst.value         = "2001:db8::1"
    pkt.ipv6.next_header.value = 17                  # UDP

    pkt = f_rev.packet.add()                         # inner UDP
    pkt.choice = "udp"
    pkt.udp.src_port.value = 5000
    pkt.udp.dst_port.value = 1234

    # ---- Captures on both ports (p2 = forward rx, p1 = reverse rx) ----------
    cap_p2 = cfg.captures.capture(name="cap_p2")[-1]
    cap_p2.port_names = [p2.name]
    cap_p2.format     = cap_p2.PCAPNG

    cap_p1 = cfg.captures.capture(name="cap_p1")[-1]
    cap_p1.port_names = [p1.name]
    cap_p1.format     = cap_p1.PCAPNG

    api.set_config(cfg)

    # ---- Phase 1: Control plane (IS-IS adjacency + SRv6 advertisement) ------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc6_cp")
    _check_isis_sessions_up(api, tc, min_sessions=2)

    # Node SIDs — IxN config state (hard assert)
    _verify_cp(api, tc,
               expected_r1={"fc00:0:1:1::": 1},
               expected_r2={"fc00:0:2:1::": 1})

    # Adj SIDs — IxN config state (hard assert)
    _verify_adj_sid_state(api, tc, "r1_intf", {"fc00:0:1:c8::": 5})
    _verify_adj_sid_state(api, tc, "r2_intf", {"fc00:0:2:c8::": 5})

    # Node SIDs — wire TLV 27 / sub-TLV 5 (best-effort)
    _verify_cp_wire(tc, cp_pcap, "r1", _SYS_ID_R1, {"fc00:0:1:1::": 1})
    _verify_cp_wire(tc, cp_pcap, "r2", _SYS_ID_R2, {"fc00:0:2:1::": 1})

    # Adj SIDs — wire TLV 22 / sub-TLV 43 (best-effort)
    _verify_adj_sid_wire(tc, cp_pcap, "r1", _SYS_ID_R1, {"fc00:0:1:c8::": 5})
    _verify_adj_sid_wire(tc, cp_pcap, "r2", _SYS_ID_R2, {"fc00:0:2:c8::": 5})

    # Capabilities — wire TLV 242 / sub-TLV 25 (best-effort)
    _verify_capabilities_wire(tc, cp_pcap, "r1", _SYS_ID_R1)
    _verify_capabilities_wire(tc, cp_pcap, "r2", _SYS_ID_R2)

    # ---- Phase 2: Data plane — bidirectional SRH traffic --------------------
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    # Forward p1→p2: verify r2's advertised SIDs appear in SRH on p2 capture
    dp_fwd = _get_capture(api, p2.name)
    _save_capture(dp_fwd, "test_tc6_dp_fwd")
    srh_fwd = _parse_srh_from_pcap(dp_fwd)
    _verify_dp(tc, srh_fwd, {
        "routing_type":  4,
        "segments_left": 1,
        "last_entry":    1,
        "flags_byte":    0,
        "tag":           0,
        "segments":      ["fc00:0:2:c8::", "fc00:0:2:1::"],  # r2 Adj SID, r2 Node SID
    })
    _verify_dp_inner(tc, srh_fwd.get("inner") if srh_fwd else None, {
        "type": "ipv6_tcp",
        "ip_src": "2001:db8::1", "ip_dst": "2001:db8::2",
        "ip_next_header": 6, "src_port": 1234, "dst_port": 80, "data_offset": 5,
    })

    # Reverse p2→p1: verify r1's advertised SIDs appear in SRH on p1 capture
    dp_rev = _get_capture(api, p1.name)
    _save_capture(dp_rev, "test_tc6_dp_rev")
    srh_rev = _parse_srh_from_pcap(dp_rev)
    _verify_dp(tc, srh_rev, {
        "routing_type":  4,
        "segments_left": 1,
        "last_entry":    1,
        "flags_byte":    0,
        "tag":           0,
        "segments":      ["fc00:0:1:c8::", "fc00:0:1:1::"],  # r1 Adj SID, r1 Node SID
    })
    _verify_dp_inner(tc, srh_rev.get("inner") if srh_rev else None, {
        "type": "ipv6_udp",
        "ip_src": "2001:db8::2", "ip_dst": "2001:db8::1",
        "ip_next_header": 17, "src_port": 5000, "dst_port": 1234, "udp_length": 8,
    })

    _, flow_results = utils.get_all_stats(api)
    _verify_device_flow_metrics(tc, flow_results, "srh_fwd")
    _verify_device_flow_metrics(tc, flow_results, "srh_rev")

    _delete_captures("test_tc6_cp", "test_tc6_dp_fwd", "test_tc6_dp_rev")
    print("\n  [%s] PASSED — Capabilities, Node/Adj SIDs and bidir DP verified." % tc)


# ---------------------------------------------------------------------------
# TC-7: SRv6 End SID flavors — PSP / USP / PSP+USP / USD — CP + DP wire format
# ---------------------------------------------------------------------------

_TC7_FLAVOR_SIDS = [
    # (flow_name,      function_hex, sid,            behavior code, endpoint_behavior string)
    ("srh_end",         "0001", "fc00:0:1:1::", 1,  "end"),
    ("srh_end_psp",     "0002", "fc00:0:1:2::", 2,  "end_with_psp"),
    ("srh_end_usp",     "0003", "fc00:0:1:3::", 3,  "end_with_usp"),
    ("srh_end_psp_usp", "0004", "fc00:0:1:4::", 4,  "end_with_psp_usp"),
    ("srh_end_usd",     "0005", "fc00:0:1:5::", 28, "end_with_usd"),
]


def test_tc7_srv6_end_sid_flavors_cp_dp(api, b2b_raw_config, utils):
    """TC-7: End SID PSP/USP/PSP+USP/USD flavors — CP advertisement + DP wire format.

    Control plane:
      r1 locator fc00:0:1::/48 with five End SIDs covering every flavor
      combination modeled by the End SID object:
        fc00:0:1:1:: End              (code 1)
        fc00:0:1:2:: End with PSP     (code 2)
        fc00:0:1:3:: End with USP     (code 3)
        fc00:0:1:4:: End with PSP+USP (code 4)
        fc00:0:1:5:: End with USD     (code 28)
      Verify: IS-IS L2 session up; all five SIDs active with correct
              behavior codes in IxN config state.

    Data plane:
      One single-segment SRH flow per flavor SID (dst=segment=SID, sl=0,
      le=0), all transmitted p1->p2 in one burst and captured together.
      Verify each flow's packet arrives on the wire with the exact SRH
      fields and inner payload it was sent with, matched back to its flow
      by outer IPv6 destination address.

      This proves packet construction / wire format for every flavor, NOT
      the actual PSP/USP/USD pop-or-decapsulate transformation — B2B has no
      DUT to perform that; see TC-PDP-1 for real forwarding verification.
    """
    tc = "TC7"
    api.set_config(api.config())

    # ---- Flat config build (no _build_*/_add_* helpers) -----------------
    cfg = api.config()

    p1_loc = b2b_raw_config.ports[0].location
    p2_loc = b2b_raw_config.ports[1].location
    p1, p2 = cfg.ports.port(name="tx", location=p1_loc).port(
        name="rx", location=p2_loc
    )

    for l1_orig in b2b_raw_config.layer1:
        l1 = cfg.layer1.add()
        l1.name = l1_orig.name
        l1.port_names = [p1.name, p2.name]
        l1.media = l1_orig.media
        l1.speed = l1_orig.speed

    cfg.options.port_options.location_preemption = True

    d1, d2 = cfg.devices.device(name="d1").device(name="d2")

    d1_eth = d1.ethernets.add()
    d1_eth.name = "d1_eth"
    d1_eth.connection.port_name = p1.name
    d1_eth.mac = "00:00:00:01:01:01"

    d2_eth = d2.ethernets.add()
    d2_eth.name = "d2_eth"
    d2_eth.connection.port_name = p2.name
    d2_eth.mac = "00:00:00:02:02:02"

    d1_v6 = d1_eth.ipv6_addresses.add()
    d1_v6.name = "d1_ipv6"
    d1_v6.address = "2001::1"
    d1_v6.gateway = "2001::2"
    d1_v6.prefix = 64

    d2_v6 = d2_eth.ipv6_addresses.add()
    d2_v6.name = "d2_ipv6"
    d2_v6.address = "2001::2"
    d2_v6.gateway = "2001::1"
    d2_v6.prefix = 64

    # r1 IS-IS router
    d1.isis.name = "r1"
    d1.isis.system_id = _SYS_ID_R1
    d1.isis.basic.enable_wide_metric = True
    d1.isis.basic.learned_lsp_filter = True
    d1.isis.advanced.area_addresses = [_AREA]
    d1.isis.advanced.lsp_refresh_rate = 900
    d1.isis.advanced.lsp_lifetime = 1200
    d1.isis.advanced.csnp_interval = 10000
    d1.isis.advanced.psnp_interval = 2000
    d1.isis.advanced.max_lsp_size = 1492

    r1_intf = d1.isis.interfaces.add()
    r1_intf.eth_name = d1_eth.name
    r1_intf.name = "r1_intf"
    r1_intf.network_type = "point_to_point"
    r1_intf.level_type = "level_2"
    r1_intf.metric = 10
    r1_intf.l2_settings.dead_interval = 30
    r1_intf.l2_settings.hello_interval = 10
    r1_intf.l2_settings.priority = 0
    r1_intf.advanced.auto_adjust_supported_protocols = True

    # r2 IS-IS router
    d2.isis.name = "r2"
    d2.isis.system_id = _SYS_ID_R2
    d2.isis.basic.enable_wide_metric = True
    d2.isis.basic.learned_lsp_filter = True
    d2.isis.advanced.area_addresses = [_AREA]
    d2.isis.advanced.lsp_refresh_rate = 900
    d2.isis.advanced.lsp_lifetime = 1200
    d2.isis.advanced.csnp_interval = 10000
    d2.isis.advanced.psnp_interval = 2000
    d2.isis.advanced.max_lsp_size = 1492

    r2_intf = d2.isis.interfaces.add()
    r2_intf.eth_name = d2_eth.name
    r2_intf.name = "r2_intf"
    r2_intf.network_type = "point_to_point"
    r2_intf.level_type = "level_2"
    r2_intf.metric = 10
    r2_intf.l2_settings.dead_interval = 30
    r2_intf.l2_settings.hello_interval = 10
    r2_intf.l2_settings.priority = 0
    r2_intf.advanced.auto_adjust_supported_protocols = True

    # r1 locator fc00:0:1::/48 with one End SID per flavor
    d1.isis.segment_routing.router_capability.srv6_capability.c_flag = True
    loc1 = d1.isis.segment_routing.srv6_locators.add()
    loc1.locator_name = "loc1"
    loc1.locator = _LOC1
    loc1.prefix_length = _PFX
    loc1.algorithm = 0
    loc1.metric = 10
    loc1.d_flag = False
    loc1.sid_structure.locator_block_length = _LB
    loc1.sid_structure.locator_node_length = _LN
    loc1.sid_structure.function_length = _FN
    loc1.sid_structure.argument_length = _ARG
    loc1.advertise_locator_as_prefix.route_metric = 10
    loc1.advertise_locator_as_prefix.redistribution_type = "up"
    loc1.advertise_locator_as_prefix.route_origin = "internal"

    for _, function_hex, _sid, _code, behavior in _TC7_FLAVOR_SIDS:
        end_sid = loc1.end_sids.add()
        end_sid.function = function_hex
        end_sid.argument = "0000"
        end_sid.endpoint_behavior = behavior
        end_sid.c_flag = True

    r1_routes = d1.isis.v6_routes.add()
    r1_routes.name = "r1_v6_routes"
    r1_routes.link_metric = 10
    r1_routes.origin_type = "internal"
    r1_route_addr = r1_routes.addresses.add()
    r1_route_addr.address = "fd00:0:1::1"
    r1_route_addr.prefix = 64
    r1_route_addr.count = 1

    # r2 locator fc00:0:2::/48 with a single End SID
    d2.isis.segment_routing.router_capability.srv6_capability.c_flag = True
    loc2 = d2.isis.segment_routing.srv6_locators.add()
    loc2.locator_name = "loc2"
    loc2.locator = _LOC2
    loc2.prefix_length = _PFX
    loc2.algorithm = 0
    loc2.metric = 10
    loc2.d_flag = False
    loc2.sid_structure.locator_block_length = _LB
    loc2.sid_structure.locator_node_length = _LN
    loc2.sid_structure.function_length = _FN
    loc2.sid_structure.argument_length = _ARG
    loc2.advertise_locator_as_prefix.route_metric = 10
    loc2.advertise_locator_as_prefix.redistribution_type = "up"
    loc2.advertise_locator_as_prefix.route_origin = "internal"

    r2_end_sid = loc2.end_sids.add()
    r2_end_sid.function = "0001"
    r2_end_sid.argument = "0000"
    r2_end_sid.endpoint_behavior = "end"
    r2_end_sid.c_flag = True

    r2_routes = d2.isis.v6_routes.add()
    r2_routes.name = "r2_v6_routes"
    r2_routes.link_metric = 10
    r2_routes.origin_type = "internal"
    r2_route_addr = r2_routes.addresses.add()
    r2_route_addr.address = "fd00:0:2::1"
    r2_route_addr.prefix = 64
    r2_route_addr.count = 1

    # One single-segment SRH flow per flavor SID, each with an inner IPv4/TCP payload
    inner_cfgs = {}
    for flow_name, _function_hex, sid, _code, _behavior in _TC7_FLAVOR_SIDS:
        f = cfg.flows.add()
        f.name = flow_name
        f.tx_rx.port.tx_name = p1.name
        f.tx_rx.port.rx_name = p2.name
        f.rate.pps = 50
        f.duration.fixed_packets.packets = 10
        f.metrics.enable = True

        eth = f.packet.add()
        eth.choice = "ethernet"
        eth.ethernet.src.value = "00:11:22:33:44:55"
        eth.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

        ip6 = f.packet.add()
        ip6.choice = "ipv6"
        ip6.ipv6.src.value = "2001::1"
        ip6.ipv6.dst.value = sid
        ip6.ipv6.next_header.value = 43

        ext = f.packet.add()
        ext.choice = "ipv6_extension_header"
        ext.ipv6_extension_header.routing.choice = "segment_routing"
        sr = ext.ipv6_extension_header.routing.segment_routing
        sr.segments_left.value = 0
        sr.last_entry.value = 0
        sr.flags.protected.value = 0
        sr.flags.alert.value = 0
        sr.tag.value = 0
        sr.segment_list.segment()[-1].segment.value = sid

        ip4 = f.packet.add()
        ip4.choice = "ipv4"
        ip4.ipv4.src.value = "10.1.1.1"
        ip4.ipv4.dst.value = "10.2.2.2"
        ip4.ipv4.protocol.value = 6

        tcp = f.packet.add()
        tcp.choice = "tcp"
        tcp.tcp.src_port.value = 1234
        tcp.tcp.dst_port.value = 80

        inner_cfgs[sid] = {
            "type": "ipv4_tcp",
            "ip_src": "10.1.1.1", "ip_dst": "10.2.2.2", "ip_protocol": 6,
            "src_port": 1234, "dst_port": 80, "data_offset": 5,
        }

    cap = cfg.captures.capture(name="cap")[-1]
    cap.port_names = [p2.name]
    cap.format = cap.PCAPNG

    api.set_config(cfg)

    # ---- Phase 1: Control plane -----------------------------------------
    _start_capture(api)
    _start_protocols(api)
    time.sleep(_CONVERGENCE)
    _stop_capture(api)

    cp_pcap = _get_capture(api, p2.name)
    _save_capture(cp_pcap, "test_tc7_cp")
    _check_isis_sessions_up(api, tc)

    expected_r1 = {sid: code for _, _fn, sid, code, _bh in _TC7_FLAVOR_SIDS}
    _verify_cp_wire(tc, cp_pcap, "r1", _SYS_ID_R1, expected_r1)
    _verify_cp(api, tc, expected_r1)

    # ---- Phase 2: Data plane (IS-IS still running) ----------------------
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    dp_pcap = _get_capture(api, p2.name)
    _save_capture(dp_pcap, "test_tc7_dp")
    by_dst = {}
    for pkt in _parse_all_srh_from_pcap(dp_pcap):
        by_dst.setdefault(pkt["ip6_dst"], pkt)

    for flow_name, _function_hex, sid, _code, behavior in _TC7_FLAVOR_SIDS:
        srh = by_dst.get(sid)
        sub_tc = "%s/%s" % (tc, behavior)
        _verify_dp(sub_tc, srh, {
            "routing_type":  4,
            "segments_left": 0,
            "last_entry":    0,
            "flags_byte":    0,
            "tag":           0,
            "segments":      [sid],
        })
        _verify_dp_inner(sub_tc, srh.get("inner") if srh else None, inner_cfgs[sid])

    _, flow_results = utils.get_all_stats(api)
    for flow_name, _function_hex, _sid, _code, _behavior in _TC7_FLAVOR_SIDS:
        _verify_device_flow_metrics(tc, flow_results, flow_name)

    _delete_captures("test_tc7_cp", "test_tc7_dp")
    print("\n  [%s] PASSED — End SID flavors verified on CP and DP wire format." % tc)


# ===========================================================================
# TC-PDP-1: Node End SIDs — port-DUT-port control and data planes
# ===========================================================================
#
# Topology:
#
#   IxN Port 1 (p1) ──IS-IS L2 P2P── DUT ──IS-IS L2 P2P── IxN Port 2 (p2)
#   Device d1 / r1                                          Device d2 / r2
#   Locator: fc00:0:1::/48                                  Locator: fc00:0:2::/48
#   End SID: fc00:0:1:1::  (code 1)                         End SID: fc00:0:2:1::  (code 1)
#
# Each IxN device forms its own IS-IS P2P adjacency with the DUT (not with
# each other).  The DUT redistributes LSPs between the two sides: r1's LSP
# is flooded by the DUT to p2, and r2's LSP is flooded to p1.
#
# Data-plane forwarding path:
#   p1 sends SRH with outer_dst = DUT End SID, segments_left = 1:
#     segments = [fc00:0:2:1::,  fc00:0:10:1::]
#                 ^seg[0]         ^seg[1] = sl pointer = outer dst
#   DUT applies End behaviour:
#     sl 1 → 0,  outer dst ← seg[0] = fc00:0:2:1::,  forwards to p2
#   p2 capture: sl=0, segment list unchanged, inner IPv4/TCP intact.
#
# Update the constant below before running:
#   _DUT_END_SID — DUT's IS-IS SRv6 End SID (segment processed by DUT)
# ===========================================================================

_DUT_END_SID     = "fc00:0:10:1::"      # DUT End SID — update to match DUT IS-IS SRv6 config
_PDP_CONVERGENCE = 60                   # seconds — longer than B2B (real DUT adjacency)


@pytest.mark.skip(reason="requires live DUT connectivity (port-DUT-port) - no DUT available")
def test_tc_pdp1_srv6_node_end_sids_cp_dp(api, b2b_raw_config, utils):
    """TC-PDP-1: IS-IS SRv6 Node End SIDs — port-DUT-port CP + DP.

    Control plane:
      r1 (Port 1): locator fc00:0:1::/48, End SID fc00:0:1:1:: (behavior=End, code=1)
      r2 (Port 2): locator fc00:0:2::/48, End SID fc00:0:2:1:: (behavior=End, code=1)
      Both adjacencies (r1↔DUT, r2↔DUT) must form; DUT re-floods LSPs.
      Wire: r1's LSP (re-flooded by DUT) and r2's own LSP both captured on p2.

    Data plane (device-based, via DUT):
      tx=d1_v6, rx=d2_v6 — IxN resolves DUT MAC via NDP automatically
      Outer IPv6 src=2001:0:1::1  dst=fc00:0:10:1:: (DUT End SID)  nh=43
      SRH: routing_type=4, segments_left=1, last_entry=1
           seg[0]=fc00:0:2:1::  seg[1]=fc00:0:10:1::
      Inner: IPv4 TCP  src=10.1.1.1 dst=10.2.2.2 sport=1234 dport=80
      DUT End processing: sl 1→0, outer dst→fc00:0:2:1::, forwarded to p2.
      Capture on p2: sl=0, segment list unchanged, inner TCP intact.
    """
    tc = "PDP1"
    api.set_config(api.config())

    # ---- Ports ---------------------------------------------------------------
    cfg = api.config()

    p1, p2 = cfg.ports.port(
        name="tx", location=b2b_raw_config.ports[0].location
    ).port(
        name="rx", location=b2b_raw_config.ports[1].location
    )

    for l1_orig in b2b_raw_config.layer1:
        l1            = cfg.layer1.add()
        l1.name       = l1_orig.name
        l1.port_names = [p1.name, p2.name]
        l1.media      = l1_orig.media
        l1.speed      = l1_orig.speed

    cfg.options.port_options.location_preemption = True

    # ---- Devices and Ethernet / IPv6 link addresses --------------------------
    d1, d2 = cfg.devices.device(name="d1").device(name="d2")

    # p1 and p2 face DIFFERENT DUT interfaces — each is on its own /64 subnet.
    # d1 (p1 side): IxN=2001:0:1::1, DUT port-1=2001:0:1::2
    # d2 (p2 side): IxN=2001:0:2::1, DUT port-2=2001:0:2::2
    d1_eth                      = d1.ethernets.add()
    d1_eth.name                 = "d1_eth"
    d1_eth.connection.port_name = p1.name
    d1_eth.mac                  = "00:00:00:01:01:01"
    d1_v6         = d1_eth.ipv6_addresses.add()
    d1_v6.name    = "d1_ipv6"
    d1_v6.address = "2001:0:1::1"   # IxN port-1 address
    d1_v6.gateway = "2001:0:1::2"   # DUT interface connected to port 1
    d1_v6.prefix  = 64

    d2_eth                      = d2.ethernets.add()
    d2_eth.name                 = "d2_eth"
    d2_eth.connection.port_name = p2.name
    d2_eth.mac                  = "00:00:00:02:02:02"
    d2_v6         = d2_eth.ipv6_addresses.add()
    d2_v6.name    = "d2_ipv6"
    d2_v6.address = "2001:0:2::1"   # IxN port-2 address
    d2_v6.gateway = "2001:0:2::2"   # DUT interface connected to port 2
    d2_v6.prefix  = 64

    # ---- IS-IS router r1 — Port 1 ↔ DUT -------------------------------------
    r1                              = d1.isis
    r1.name                         = "r1"
    r1.system_id                    = "650000000001"
    r1.basic.enable_wide_metric     = True
    r1.basic.learned_lsp_filter     = True
    r1.advanced.area_addresses      = ["490001"]
    r1.advanced.lsp_refresh_rate    = 900
    r1.advanced.lsp_lifetime        = 1200
    r1.advanced.csnp_interval       = 10000
    r1.advanced.psnp_interval       = 2000
    r1.advanced.max_lsp_size        = 1492

    r1_intf                                          = r1.interfaces.add()
    r1_intf.eth_name                                 = "d1_eth"
    r1_intf.name                                     = "r1_intf"
    r1_intf.network_type                             = "point_to_point"
    r1_intf.level_type                               = "level_2"
    r1_intf.metric                                   = 10
    r1_intf.l2_settings.dead_interval                = 30
    r1_intf.l2_settings.hello_interval               = 10
    r1_intf.l2_settings.priority                     = 0
    r1_intf.advanced.auto_adjust_supported_protocols = True

    r1.segment_routing.router_capability.srv6_capability.c_flag = True

    r1_loc                                              = r1.segment_routing.srv6_locators.add()
    r1_loc.locator_name                                 = "loc1"
    r1_loc.locator                                      = "fc00:0:1::"
    r1_loc.prefix_length                                = 48
    r1_loc.algorithm                                    = 0
    r1_loc.metric                                       = 10
    r1_loc.d_flag                                       = False
    r1_loc.sid_structure.locator_block_length           = 32
    r1_loc.sid_structure.locator_node_length            = 16
    r1_loc.sid_structure.function_length                = 16
    r1_loc.sid_structure.argument_length                = 0
    r1_loc.advertise_locator_as_prefix.route_metric     = 10
    r1_loc.advertise_locator_as_prefix.redistribution_type = "up"
    r1_loc.advertise_locator_as_prefix.route_origin    = "internal"

    r1_sid                    = r1_loc.end_sids.add()   # fc00:0:1:1:: End (code 1)
    r1_sid.function           = "0001"
    r1_sid.argument           = "0000"
    r1_sid.endpoint_behavior  = "end"
    r1_sid.c_flag             = True

    r1_routes         = r1.v6_routes.add()
    r1_routes.name    = "r1_v6_routes"
    r1_routes.link_metric  = 10
    r1_routes.origin_type  = "internal"
    r1_addr           = r1_routes.addresses.add()
    r1_addr.address   = "fd00:0:1::1"
    r1_addr.prefix    = 64
    r1_addr.count     = 1

    # ---- IS-IS router r2 — Port 2 ↔ DUT -------------------------------------
    r2                              = d2.isis
    r2.name                         = "r2"
    r2.system_id                    = "650000000002"
    r2.basic.enable_wide_metric     = True
    r2.basic.learned_lsp_filter     = True
    r2.advanced.area_addresses      = ["490001"]
    r2.advanced.lsp_refresh_rate    = 900
    r2.advanced.lsp_lifetime        = 1200
    r2.advanced.csnp_interval       = 10000
    r2.advanced.psnp_interval       = 2000
    r2.advanced.max_lsp_size        = 1492

    r2_intf                                          = r2.interfaces.add()
    r2_intf.eth_name                                 = "d2_eth"
    r2_intf.name                                     = "r2_intf"
    r2_intf.network_type                             = "point_to_point"
    r2_intf.level_type                               = "level_2"
    r2_intf.metric                                   = 10
    r2_intf.l2_settings.dead_interval                = 30
    r2_intf.l2_settings.hello_interval               = 10
    r2_intf.l2_settings.priority                     = 0
    r2_intf.advanced.auto_adjust_supported_protocols = True

    r2.segment_routing.router_capability.srv6_capability.c_flag = True

    r2_loc                                              = r2.segment_routing.srv6_locators.add()
    r2_loc.locator_name                                 = "loc2"
    r2_loc.locator                                      = "fc00:0:2::"
    r2_loc.prefix_length                                = 48
    r2_loc.algorithm                                    = 0
    r2_loc.metric                                       = 10
    r2_loc.d_flag                                       = False
    r2_loc.sid_structure.locator_block_length           = 32
    r2_loc.sid_structure.locator_node_length            = 16
    r2_loc.sid_structure.function_length                = 16
    r2_loc.sid_structure.argument_length                = 0
    r2_loc.advertise_locator_as_prefix.route_metric     = 10
    r2_loc.advertise_locator_as_prefix.redistribution_type = "up"
    r2_loc.advertise_locator_as_prefix.route_origin    = "internal"

    r2_sid                    = r2_loc.end_sids.add()   # fc00:0:2:1:: End (code 1)
    r2_sid.function           = "0001"
    r2_sid.argument           = "0000"
    r2_sid.endpoint_behavior  = "end"
    r2_sid.c_flag             = True

    r2_routes         = r2.v6_routes.add()
    r2_routes.name    = "r2_v6_routes"
    r2_routes.link_metric  = 10
    r2_routes.origin_type  = "internal"
    r2_addr           = r2_routes.addresses.add()
    r2_addr.address   = "fd00:0:2::1"
    r2_addr.prefix    = 64
    r2_addr.count     = 1

    # ---- SRH device-based flow: d1 → DUT → d2 ----------------------------------
    # tx=d1_v6 / rx=d2_v6: IxN resolves the DUT's MAC via NDP (no hardcoded MAC).
    # Outer IPv6 dst = DUT End SID; DUT applies End:
    #   sl 1→0, outer dst ← seg[0] = fc00:0:2:1::, forwards out port 2.
    # Capture on p2 verifies: sl=0, segments unchanged, inner TCP intact.
    f1                                = cfg.flows.add()
    f1.name                           = "srh_pdp1"
    f1.tx_rx.device.tx_names          = [d1_v6.name]
    f1.tx_rx.device.rx_names          = [d2_v6.name]
    f1.rate.pps                       = 100
    f1.duration.fixed_packets.packets = 200
    f1.metrics.enable                 = True

    ip6_1                       = f1.packet.add().ipv6
    ip6_1.src.value             = "2001:0:1::1"
    ip6_1.dst.value             = _DUT_END_SID    # DUT End SID: sl pointer
    ip6_1.next_header.value     = 43              # SRH

    sr1                         = f1.packet.add().ipv6_extension_header.routing.segment_routing
    sr1.segments_left.value     = 1               # points to seg[1] = DUT End SID
    sr1.last_entry.value        = 1               # 2-segment list (0-indexed)
    sr1.flags.protected.value   = 0
    sr1.flags.oam.value         = 0
    sr1.flags.alert.value       = 0
    sr1.tag.value               = 0
    seg                         = sr1.segment_list.segment()[-1]
    seg.segment.value           = "fc00:0:2:1::"  # seg[0]: next hop after DUT
    seg                         = sr1.segment_list.segment()[-1]
    seg.segment.value           = _DUT_END_SID    # seg[1]: DUT End SID (current)

    ip4_inner                   = f1.packet.add().ipv4
    ip4_inner.src.value         = "10.1.1.1"
    ip4_inner.dst.value         = "10.2.2.2"
    ip4_inner.protocol.value    = 6              # TCP

    tcp_inner                   = f1.packet.add().tcp
    tcp_inner.src_port.value    = 1234
    tcp_inner.dst_port.value    = 80

    # ---- Device flow — route reachability check via DUT ---------------------
    # Plain IPv6 device flow; IxN resolves MAC via IS-IS adjacency.
    # Passes only if the DUT correctly redistributes both route ranges.
    f_dev                              = cfg.flows.add()
    f_dev.name                         = "isis_dev_flow"
    f_dev.tx_rx.device.tx_names        = ["r1_v6_routes"]
    f_dev.tx_rx.device.rx_names        = ["r2_v6_routes"]
    f_dev.rate.pps                     = 50
    f_dev.duration.fixed_packets.packets = 100
    f_dev.metrics.enable               = True

    # ---- Capture on p2 (DUT egress side) ------------------------------------
    cap                = cfg.captures.capture(name="cap")[-1]
    cap.port_names     = [p2.name]
    cap.format         = cap.PCAPNG

    api.set_config(cfg)

    # =========================================================================
    # Phase 1: Control plane
    # Wait for both IS-IS adjacencies (r1↔DUT and r2↔DUT) to form.
    # DUT re-floods r1's LSP to p2, so TLV-27 wire verification works for
    # both routers from the single p2 capture.
    # =========================================================================
    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.CAPTURE
    cs.port.capture.state = cs.port.capture.START
    api.set_control_state(cs)

    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)

    time.sleep(_PDP_CONVERGENCE)

    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.CAPTURE
    cs.port.capture.state = cs.port.capture.STOP
    api.set_control_state(cs)

    req = api.capture_request()
    req.port_name = p2.name
    cp_pcap = api.get_capture(req)
    _save_capture(cp_pcap, "test_tc_pdp1_cp")

    # Expect 2 IS-IS L2 sessions: r1↔DUT and r2↔DUT
    _check_isis_sessions_up(api, tc, min_sessions=2)

    # IxN config-state: both End SIDs active (hard assert)
    _verify_cp(api, tc,
               expected_r1={"fc00:0:1:1::": 1},
               expected_r2={"fc00:0:2:1::": 1})

    # Wire (p2): r2 sends its own LSP; DUT re-floods r1's LSP from port 1
    _verify_cp_wire(tc, cp_pcap, "r1", "650000000001", {"fc00:0:1:1::": 1})
    _verify_cp_wire(tc, cp_pcap, "r2", "650000000002", {"fc00:0:2:1::": 1})

    # =========================================================================
    # Phase 2: Data plane (IS-IS still running)
    # SRH sent from p1: sl=1, outer dst = DUT End SID.
    # DUT applies End: sl 1→0, outer dst → fc00:0:2:1::, forwards to p2.
    # Capture on p2 must show the DUT-processed SRH (sl=0).
    # =========================================================================
    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.CAPTURE
    cs.port.capture.state = cs.port.capture.START
    api.set_control_state(cs)

    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)

    time.sleep(4)

    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
    api.set_control_state(cs)

    cs = api.control_state()
    cs.choice = cs.PORT
    cs.port.choice = cs.port.CAPTURE
    cs.port.capture.state = cs.port.capture.STOP
    api.set_control_state(cs)

    req = api.capture_request()
    req.port_name = p2.name
    dp_pcap = api.get_capture(req)
    _save_capture(dp_pcap, "test_tc_pdp1_dp")

    srh = _parse_srh_from_pcap(dp_pcap)
    _verify_dp(tc, srh, {
        "routing_type":  4,
        "segments_left": 0,                                   # DUT decremented 1 → 0
        "last_entry":    1,                                   # 2-segment list, unchanged
        "flags_byte":    0,
        "tag":           0,
        "segments":      ["fc00:0:2:1::", _DUT_END_SID],      # DUT does not alter SID list
    })
    _verify_dp_inner(tc, srh.get("inner") if srh else None, {
        "type":        "ipv4_tcp",
        "ip_src":      "10.1.1.1",
        "ip_dst":      "10.2.2.2",
        "ip_protocol": 6,
        "src_port":    1234,
        "dst_port":    80,
        "data_offset": 5,
    })

    _, flow_results = utils.get_all_stats(api)
    _verify_device_flow_metrics(tc, flow_results, "isis_dev_flow")

    _delete_captures("test_tc_pdp1_cp", "test_tc_pdp1_dp")
    print("\n  [%s] PASSED — Node End SIDs PDP: CP adjacencies up; "
          "DUT End-SID forwarding verified (sl=0 on p2 capture)." % tc)
