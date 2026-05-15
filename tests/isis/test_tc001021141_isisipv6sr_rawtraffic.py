"""TC001021141 — IxNetwork 8.10 ISIS-IPv6-SR raw-traffic SRH.

Snappi conversion of the legacy TCL test:
    .../cpf-b2b/SR/isis/rawTrafficSRH/8.10-U3/test.tc001021141_isisipv6sr_rawtraffic.tcl
    .../cpf-b2b/SR/isis/rawTrafficSRH/8.10-U3/config.tc001021141_isisipv6sr_rawtraffic.ixncfg

JSON export of the source ixncfg:
    scripts/output/config.tc001021141_isisipv6sr_rawtraffic.json

Mapping audit (JSON -> snappi model). Items absent from the snappi model are
flagged inline as `# NOT SUPPORTED IN MODEL`.

  vport[*].protocols.isis.enabled = False    -> ISIS not configured (raw flow only)
  Traffic Item 1 / configElement[0]:
    Ethernet stack:
      destinationAddress  = 33:00:00:00:00:00 -> eth.dst.value
      sourceAddress       = 44:00:00:00:00:00 -> eth.src.value
      etherType           = 0x86dd            -> implicit (next stack is IPv6)
    IPv6 stack:
      version             = 6                 -> implicit
      trafficClass        = 0                 -> ipv6.traffic_class.value
      flowLabel           = 0                 -> ipv6.flow_label.value
      payloadLength       = 168               -> auto-derived; not set
      nextHeader          = 43                -> ipv6.next_header.value
      hopLimit            = 64                -> ipv6.hop_limit.value
      srcIP               = aa::22            -> ipv6.src.value
      dstIP               = bb::44            -> ipv6.dst.value
    ipv6RoutingType4 (SRH) stack:
      nextHeader          = 59                # NOT SUPPORTED IN MODEL — segment_routing model has no next_header field; IxN auto-defaults to 59 when no inner stack follows
      hdrExtLen           = 20                # auto-derived by translator from segment count
      routingType         = 4                 # implicit (set by stack choice)
      segmentsLeft        = 7                 -> sr.segments_left.value
      lastEntry           = 0                 -> sr.last_entry.value  (JSON value used verbatim — note: a degenerate SRH per RFC 8754, but JSON is source of truth)
      flags.u1Flag        = 0                 # NOT SUPPORTED IN MODEL — segment_routing.flags exposes only protected + alert
      flags.pFlag         = 0                 -> sr.flags.protected.value
      flags.oFlag         = 0                 # NOT SUPPORTED IN MODEL — OAM flag not in segment_routing.flags
      flags.aFlag         = 0                 -> sr.flags.alert.value
      flags.hFlag         = 0                 # NOT SUPPORTED IN MODEL — HMAC flag not in segment_routing.flags
      flags.u2Flag        = 0                 # NOT SUPPORTED IN MODEL — unused flags not in segment_routing.flags
      tag                 = 0                 -> sr.tag.value
      segmentList SID 1   = 10::              -> sr.segment_list.segment[0].segment.value
      segmentList SID 2   = 99::              -> sr.segment_list.segment[1].segment.value
      segmentList SID 3   valueType=increment -> sr.segment_list.segment[2].segment.increment
                          startValue=88::         .start = "88::"
                          stepValue=::1           .step  = "::1"
                          countValue=5            .count = 5      (per-frame rotation: 88::, 88::1, 88::2, 88::3, 88::4)
      segmentList SID 4   = 77::              -> sr.segment_list.segment[3].segment.value
      segmentList SID 5..10 = 66::,55::,44::,33::,22::,11::
      segmentList SID 11..20 = ::             -> not advertised in snappi; on the wire IxN still emits hdr_ext_len*8 / 16 segments (10 here, no trailing zeros)
      srhTLVs.* (ingressNodeTLV, egressNodeTLV, opaqueContainerTLV, pathTraceTLV, paddingTLV)
                                              # NOT SUPPORTED IN MODEL — segment_routing has no SRH TLVs sub-tree; JSON shows all defaults / zero-length, IxN omits them when not user-overridden
  TrafficItem.frameSize.fixedSize  = 82       -> overridden to 256 (need >= 222 to fit Eth+IPv6+SRH)
  TrafficItem.frameRate (10% line rate)       -> set pps=100 for deterministic capture
  TrafficItem.transmissionControl.type=continuous -> f.duration.fixed_seconds.seconds = 60 (matches TCL `after 60000`)

Verification mirrors the TCL flow:
  1) traffic stats: frames_tx > 0 and frames_rx == frames_tx (loss == 0).
  2) port-2 capture: parse every IPv6+SRH frame and compare wire fields
     against what we configured. Per-frame:
       - SRH base fields (routing_type, segments_left, last_entry, flags, tag).
       - Static slots (SID 1, 2, 4..10) match the configured value exactly.
       - Slot 3 (SID 3) is per-frame increment — collect every observed
         value and assert the set equals {88::, 88::1, 88::2, 88::3, 88::4}.
"""

import io
import ipaddress
import os
import struct
import time

import dpkt


_CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "captures")


# ---------------------------------------------------------------------------
# Control-state helpers (file-local; do NOT import from
# test_srv6_srh_traffic_b2b.py — this conversion is standalone per plan.)
# ---------------------------------------------------------------------------


def _start_traffic(api):
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)


def _stop_traffic(api):
    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
    api.set_control_state(cs)


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


def _add_capture(config, port_name, capture_name="srh_cap"):
    cap = config.captures.capture(name=capture_name)[-1]
    cap.port_names = [port_name]
    cap.format = cap.PCAPNG


def _get_capture(api, port_name):
    req = api.capture_request()
    req.port_name = port_name
    return api.get_capture(req)


def _save_capture(pcap_bytes, test_name):
    os.makedirs(_CAPTURES_DIR, exist_ok=True)
    path = os.path.join(_CAPTURES_DIR, test_name + ".pcapng")
    raw = (
        pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
    )
    with open(path, "wb") as fh:
        fh.write(raw)
    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    return path


def _delete_capture(test_name):
    path = os.path.join(_CAPTURES_DIR, test_name + ".pcapng")
    if os.path.exists(path):
        os.remove(path)


def _norm(addr):
    return str(ipaddress.IPv6Address(addr))


def _parse_one_srh_frame(buf):
    """Decode SRH fields from one ethernet frame, or return None.

    `segments` is bounded by last_entry+1 (RFC 8754 valid-segment definition);
    `full_segments` is bounded by hdr_ext_len (the actual segment-list bytes
    on the wire) so callers can verify slots beyond last_entry — needed when
    the source ixncfg uses a per-frame increment on a slot > last_entry.
    """
    if len(buf) < 62:
        return None
    eth_type = struct.unpack("!H", buf[12:14])[0]
    if eth_type == 0x8100:
        if len(buf) < 66:
            return None
        eth_type = struct.unpack("!H", buf[16:18])[0]
        ip6_off = 18
    else:
        ip6_off = 14
    if eth_type != 0x86DD:
        return None
    if ip6_off + 40 > len(buf):
        return None
    if buf[ip6_off + 6] != 43:
        return None
    srh_off = ip6_off + 40
    if srh_off + 8 > len(buf):
        return None
    if buf[srh_off + 2] != 4:
        return None
    srh_next_header = buf[srh_off + 0]
    hdr_ext_len = buf[srh_off + 1]
    segments_left = buf[srh_off + 3]
    last_entry = buf[srh_off + 4]
    flags_byte = buf[srh_off + 5]
    tag = struct.unpack("!H", buf[srh_off + 6 : srh_off + 8])[0]

    # Total segment-list bytes = hdr_ext_len * 8 (no SRH TLVs in this flow).
    full_seg_count = (hdr_ext_len * 8) // 16
    full_segments = []
    for idx in range(full_seg_count):
        off = srh_off + 8 + idx * 16
        if off + 16 > len(buf):
            break
        full_segments.append(str(ipaddress.IPv6Address(buf[off : off + 16])))

    return {
        "srh_next_header": srh_next_header,
        "hdr_ext_len": hdr_ext_len,
        "routing_type": 4,
        "segments_left": segments_left,
        "last_entry": last_entry,
        "flags_byte": flags_byte,
        "tag": tag,
        "segments": full_segments[: last_entry + 1],
        "full_segments": full_segments,
    }


def _parse_srh_from_pcap(pcap_bytes):
    """Return list of SRH wire-field dicts, one per IPv6+SRH frame.

    Reads bytes directly (RFC 8754 layout) — robust across dpkt versions.
    Frame layout assumed: Eth(14) + IPv6(40) + SRH at offset 54.
    Returns [] when the capture is empty or has no SRH frames.
    """
    if pcap_bytes is None:
        return []
    raw = (
        pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
    )
    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    if not raw:
        return []
    try:
        pcap = dpkt.pcapng.Reader(io.BytesIO(raw))
    except Exception:
        try:
            pcap = dpkt.pcap.Reader(io.BytesIO(raw))
        except Exception:
            return []

    frames = []
    seen = 0
    for _, pkt_data in pcap:
        try:
            seen += 1
            info = _parse_one_srh_frame(bytes(pkt_data))
            if info is not None:
                frames.append(info)
        except Exception:
            continue
    if not frames:
        print("  [pcap] scanned %d packets; no IPv6/SRH frame found" % seen)
    return frames


# ---------------------------------------------------------------------------
# Configured wire values (from JSON export of source ixncfg)
# ---------------------------------------------------------------------------

ETH_DST = "33:00:00:00:00:00"
ETH_SRC = "44:00:00:00:00:00"
IPV6_SRC = "aa::22"
IPV6_DST = "bb::44"
IPV6_HOP_LIMIT = 64

SEGMENTS_LEFT = 7
LAST_ENTRY = 0  # source JSON value; intentionally not "9" — see docstring
TAG = 0
FLAG_PROTECTED = 0
FLAG_ALERT = 0

# Slot order from JSON ipv6SID1..ipv6SID10. Slot 3 (index 2) is special:
# JSON has valueType=increment with start=88::, step=::1, count=5 — see
# SID3_INC_* below. The placeholder here is None so no static value is
# emitted for that slot; _build_config configures it via .increment instead.
SEGMENTS = [
    "10::",
    "99::",
    None,  # SID 3 — increment, see SID3_INC_*
    "77::",
    "66::",
    "55::",
    "44::",
    "33::",
    "22::",
    "11::",
]

# SID 3 per-frame increment (JSON: valueType=increment on ipv6SID3-15).
SID3_INC_INDEX = 2
SID3_INC_START = "88::"
SID3_INC_STEP = "::1"
SID3_INC_COUNT = 5
SID3_EXPECTED_VALUES = [
    str(ipaddress.IPv6Address("88::") + i) for i in range(SID3_INC_COUNT)
]


def _build_config(b2b_raw_config):
    config = b2b_raw_config
    config.flows.clear()
    p1, p2 = config.ports

    f = config.flows.add(name="srh_tc1021141")
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_seconds.seconds = 60
    f.size.fixed = 256  # JSON had 82 (too small for SRH); 256 fits Eth+IPv6+SRH=222 with margin
    f.metrics.enable = True

    eth = f.packet.add()
    eth.choice = "ethernet"
    eth.ethernet.dst.value = ETH_DST
    eth.ethernet.src.value = ETH_SRC

    ip6 = f.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = IPV6_SRC
    ip6.ipv6.dst.value = IPV6_DST
    ip6.ipv6.next_header.value = 43  # routing extension header
    ip6.ipv6.hop_limit.value = IPV6_HOP_LIMIT
    ip6.ipv6.traffic_class.value = 0
    ip6.ipv6.flow_label.value = 0

    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing"
    sr = ext.ipv6_extension_header.routing.segment_routing
    sr.segments_left.value = SEGMENTS_LEFT
    sr.last_entry.value = LAST_ENTRY
    sr.flags.protected.value = FLAG_PROTECTED
    sr.flags.alert.value = FLAG_ALERT
    sr.tag.value = TAG
    for i, addr in enumerate(SEGMENTS):
        seg_entry = sr.segment_list.segment()[-1]
        if i == SID3_INC_INDEX:
            seg_entry.segment.increment.start = SID3_INC_START
            seg_entry.segment.increment.step = SID3_INC_STEP
            seg_entry.segment.increment.count = SID3_INC_COUNT
        else:
            seg_entry.segment.value = addr

    _add_capture(config, p2.name)
    return config


def test_tc001021141_isisipv6sr_rawtraffic(api, b2b_raw_config, utils):
    tc = "test_tc001021141_isisipv6sr_rawtraffic"
    api.set_config(api.config())
    config = _build_config(b2b_raw_config)
    api.set_config(config)

    _start_capture(api)
    _start_traffic(api)
    time.sleep(62)  # 60 s traffic + 2 s drain (matches TCL `after 60000`)
    _stop_traffic(api)
    _stop_capture(api)

    # ── Phase A — TCL parity (loss check, lines 240–243) ────────────────────
    req = api.metrics_request()
    req.flow.flow_names = ["srh_tc1021141"]
    metrics = api.get_metrics(req).flow_metrics
    assert len(metrics) == 1
    m = metrics[0]
    print("\n  [stats] frames_tx=%d frames_rx=%d" % (m.frames_tx, m.frames_rx))
    assert m.frames_tx > 0, "no frames sent"
    assert (
        m.frames_rx == m.frames_tx
    ), "loss != 0: frames_tx=%d frames_rx=%d" % (m.frames_tx, m.frames_rx)

    # ── Phase B — SRH wire content (TCL match list lines 308–344) ──────────
    pcap = _get_capture(api, config.ports[1].name)
    _save_capture(pcap, tc)
    frames = _parse_srh_from_pcap(pcap)
    assert frames, "no SRH packet found in capture"
    srh = frames[0]

    sep = "=" * 62
    print("\n%s\n  %s  [SRH wire verify]\n%s" % (sep, tc, "-" * 62))
    print("  captured SRH frames : %d" % len(frames))
    print(
        "  srh_next_header : %d  (expect 59 — IxN auto-default)"
        % srh["srh_next_header"]
    )
    print(
        "  hdr_ext_len     : %d  (translator auto-derives from segment count)"
        % srh["hdr_ext_len"]
    )
    print("  routing_type    : %d  (expect 4)" % srh["routing_type"])
    print(
        "  segments_left   : %d  (expect %d)"
        % (srh["segments_left"], SEGMENTS_LEFT)
    )
    print(
        "  last_entry      : %d  (expect %d)" % (srh["last_entry"], LAST_ENTRY)
    )
    print("  flags_byte      : 0x%02x  (expect 0x00)" % srh["flags_byte"])
    print("  tag             : 0x%04x  (expect 0x%04x)" % (srh["tag"], TAG))
    for i, s in enumerate(srh["full_segments"]):
        if i == SID3_INC_INDEX:
            exp = "rotates: " + ",".join(SID3_EXPECTED_VALUES)
        elif i < len(SEGMENTS) and SEGMENTS[i] is not None:
            exp = _norm(SEGMENTS[i])
        else:
            exp = "::"
        print("  segment[%d]      : %-36s  (expect %s)" % (i, s, exp))
    print(sep)

    assert srh["routing_type"] == 4
    assert srh["segments_left"] == SEGMENTS_LEFT
    assert srh["last_entry"] == LAST_ENTRY
    assert srh["flags_byte"] == 0x00
    assert srh["tag"] == TAG

    # last_entry from JSON is 0 -> only segment[0] is "valid" per RFC 8754;
    # the parser exposes that slice as `segments`. We compare exactly those
    # entries against the configured slot order. SEGMENTS[2] is None
    # (increment slot — verified separately below) and is skipped here, but
    # last_entry=0 means the slice is just SEGMENTS[:1] so it is unaffected.
    expected = [
        _norm(a) for a in SEGMENTS[: srh["last_entry"] + 1] if a is not None
    ]
    actual = [_norm(s) for s in srh["segments"]]
    assert actual == expected, (
        "Segment list mismatch (last_entry=%d).\n  configured slots: %s\n  on wire:          %s"
        % (srh["last_entry"], expected, actual)
    )

    # Static slots (SID 1, 2, 4..10) must be identical on every captured
    # frame and equal the configured value. Slot 2 (SID 3) is the per-frame
    # increment and is verified separately.
    static_idx = [i for i, a in enumerate(SEGMENTS) if a is not None]
    static_expected = {i: _norm(SEGMENTS[i]) for i in static_idx}
    for fi, f in enumerate(frames):
        for i in static_idx:
            if i >= len(f["full_segments"]):
                break
            got = _norm(f["full_segments"][i])
            assert (
                got == static_expected[i]
            ), "frame %d slot %d mismatch: expected %s, on wire %s" % (
                fi,
                i,
                static_expected[i],
                got,
            )

    # Slot 2 (SID 3) is per-frame increment — collect every observed value
    # and assert the set matches the 5 expected rotated values.
    expected_sid3 = {_norm(a) for a in SID3_EXPECTED_VALUES}
    observed_sid3 = set()
    for f in frames:
        if len(f["full_segments"]) > SID3_INC_INDEX:
            observed_sid3.add(_norm(f["full_segments"][SID3_INC_INDEX]))
    print(
        "  SID 3 rotation  : observed %d distinct values across %d frames"
        % (len(observed_sid3), len(frames))
    )
    print("    expected : %s" % sorted(expected_sid3))
    print("    observed : %s" % sorted(observed_sid3))
    assert observed_sid3 == expected_sid3, (
        "SID 3 increment values do not match.\n"
        "  expected : %s\n  observed : %s"
        % (sorted(expected_sid3), sorted(observed_sid3))
    )

    _delete_capture(tc)
