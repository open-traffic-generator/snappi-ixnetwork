"""TC001021557 — IxNetwork 8.10 ISIS-IPv6-SR raw-traffic SRH + optional TLVs.

Snappi conversion of the legacy TCL test:
    .../cpf-b2b/SR/isis/rawTrafficSRH/8.10-U3/test.tc001021557_isis_sr_ipv6_rawtraffic_optional_tlv.tcl
    .../cpf-b2b/SR/isis/rawTrafficSRH/8.10-U3/config.tc001021557_isis_sr_ipv6_rawtraffic_optional_tlv.ixncfg

JSON export of the source ixncfg:
    scripts/output/config.tc001021557_isis_sr_ipv6_rawtraffic_optional_tlv.json

Difference vs. test_tc001021141: this config attaches five optional SRH
sub-TLVs to the segment list (Ingress Node, Egress Node, Opaque Container,
Path Trace, Padding). The snappi FlowIpv6SegmentRouting model exposes only
segments_left / last_entry / flags(protected,alert) / tag / segment_list /
routing_type — there is no `srh_tlvs` sub-tree. All five sub-TLVs are flagged
inline as `# NOT SUPPORTED IN MODEL`; the snappi-driven flow therefore emits
SRH base + segment list only (no TLVs) and capture verification checks only
the base SRH fields.

Mapping audit (JSON -> snappi model). Items absent from the snappi model are
flagged inline as `# NOT SUPPORTED IN MODEL`.

  vport[*].protocols.isis.enabled = False    -> ISIS not configured (raw flow only)
  Traffic Item 1 / configElement[0]:
    Ethernet stack:
      destinationAddress  = 00:00:00:00:00:00 -> eth.dst.value
      sourceAddress       = 00:00:00:00:00:00 -> eth.src.value
      etherType           = 0x86dd            -> implicit (next stack is IPv6)
    IPv6 stack:
      version             = 6                 -> implicit
      trafficClass        = 0                 -> ipv6.traffic_class.value
      flowLabel           = 0                 -> ipv6.flow_label.value
      payloadLength       = 232               -> auto-derived; not set
      nextHeader          = 43                -> ipv6.next_header.value
      hopLimit            = 64                -> ipv6.hop_limit.value
      srcIP               = 2001:0:1::        -> ipv6.src.value
      dstIP               = 3001:0:1::        -> ipv6.dst.value
    ipv6RoutingType4 (SRH) stack:
      nextHeader          = 59                # NOT SUPPORTED IN MODEL — segment_routing model has no next_header field; IxN auto-defaults to 59 when no inner stack follows
      hdrExtLen           = 28 (with TLVs)    # auto-derived by translator from segment count + TLVs; without TLVs the wire value is 20
      routingType         = 4                 # implicit (set by stack choice)
      segmentsLeft        = 7                 -> sr.segments_left.value
      lastEntry           = 0                 -> sr.last_entry.value  (JSON value used verbatim — TCL srCheckList(2) expects 9, but JSON is source of truth; same caveat as TC001021141)
      flags.u1Flag        = 0                 # NOT SUPPORTED IN MODEL — segment_routing.flags exposes only protected + alert
      flags.pFlag         = 0                 -> sr.flags.protected.value
      flags.oFlag         = 0                 # NOT SUPPORTED IN MODEL — OAM flag not in segment_routing.flags
      flags.aFlag         = 0                 -> sr.flags.alert.value
      flags.hFlag         = 0                 # NOT SUPPORTED IN MODEL — HMAC flag not in segment_routing.flags
      flags.u2Flag        = 0                 # NOT SUPPORTED IN MODEL — unused flags not in segment_routing.flags
      tag                 = 0                 -> sr.tag.value
      segmentList SID 1   = aa::              -> sr.segment_list.segment[0].segment.value
      segmentList SID 2   = 99::              -> sr.segment_list.segment[1].segment.value
      segmentList SID 3   = 88::              -> sr.segment_list.segment[2].segment.value
      segmentList SID 4   = 77::              -> sr.segment_list.segment[3].segment.value
      segmentList SID 5..10 = 66::,55::,44::,33::,22::,11::
      segmentList SID 11..20 = ::             -> not advertised; trailing slots are zero-padding in the IxN UI
      srhTLVs.sripv6IngressNodeTLV (type=1, length=18, flags=0, value=11::)
                                              # NOT SUPPORTED IN MODEL — segment_routing has no srh_tlvs sub-tree
      srhTLVs.sripv6EgressNodeTLV  (type=2, length=18, reserved=0, flags=0, value=aa::)
                                              # NOT SUPPORTED IN MODEL — same as above
      srhTLVs.sripv6OpaqueContainerTLV (type=3, length=18, reserved=0, flags=0, value=::22)
                                              # NOT SUPPORTED IN MODEL — same as above
      srhTLVs.pathTraceTLV (type=128, length=14, ifId/ifLd/timeStamp/sessionId/sequenceNo=0)
                                              # NOT SUPPORTED IN MODEL — same as above
      srhTLVs.sripv6PaddingTLV (type=4, length=2, pad=0x1111)
                                              # NOT SUPPORTED IN MODEL — same as above
  TrafficItem.frameSize.fixedSize  = 106      -> overridden to 256 (need >= 222 to fit Eth+IPv6+SRH=222 with margin; original 106 was too small even for the ixncfg without TLVs)
  TrafficItem.frameRate (10% line rate)       -> set pps=100 for deterministic capture
  TrafficItem.transmissionControl.type=continuous -> f.duration.fixed_seconds.seconds = 30 (matches TCL `after 30000`)

Verification mirrors the TCL flow:
  1) traffic stats: frames_tx > 0 and frames_rx == frames_tx (loss == 0).
  2) port-2 capture: parse the first IPv6+SRH frame and compare wire fields
     against what we configured. SRH TLV fields are NOT verified (not emitted
     by snappi since the model has no representation).
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
# test_tc001021141_isisipv6sr_rawtraffic.py — this conversion is standalone
# per plan.)
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


def _parse_srh_from_pcap(pcap_bytes):
    """Return SRH wire fields from the first IPv6+SRH frame, or None.

    Reads bytes directly (RFC 8754 layout) — robust across dpkt versions.
    Frame layout assumed: Eth(14) + IPv6(40) + SRH at offset 54.
    """
    if pcap_bytes is None:
        return None
    raw = (
        pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
    )
    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    if not raw:
        return None
    try:
        pcap = dpkt.pcapng.Reader(io.BytesIO(raw))
    except Exception:
        try:
            pcap = dpkt.pcap.Reader(io.BytesIO(raw))
        except Exception:
            return None

    seen = 0
    for _, pkt_data in pcap:
        try:
            buf = bytes(pkt_data)
            seen += 1
            if len(buf) < 62:
                continue
            eth_type = struct.unpack("!H", buf[12:14])[0]
            if eth_type == 0x8100:
                if len(buf) < 66:
                    continue
                eth_type = struct.unpack("!H", buf[16:18])[0]
                ip6_off = 18
            else:
                ip6_off = 14
            if eth_type != 0x86DD:
                continue
            if ip6_off + 40 > len(buf):
                continue
            if buf[ip6_off + 6] != 43:
                continue
            srh_off = ip6_off + 40
            if srh_off + 8 > len(buf):
                continue
            if buf[srh_off + 2] != 4:
                continue
            srh_next_header = buf[srh_off + 0]
            hdr_ext_len = buf[srh_off + 1]
            segments_left = buf[srh_off + 3]
            last_entry = buf[srh_off + 4]
            flags_byte = buf[srh_off + 5]
            tag = struct.unpack("!H", buf[srh_off + 6 : srh_off + 8])[0]
            seg_count = last_entry + 1
            segments = []
            for idx in range(seg_count):
                off = srh_off + 8 + idx * 16
                if off + 16 > len(buf):
                    break
                segments.append(
                    str(ipaddress.IPv6Address(buf[off : off + 16]))
                )
            return {
                "srh_next_header": srh_next_header,
                "hdr_ext_len": hdr_ext_len,
                "routing_type": 4,
                "segments_left": segments_left,
                "last_entry": last_entry,
                "flags_byte": flags_byte,
                "tag": tag,
                "segments": segments,
            }
        except Exception:
            continue
    print("  [pcap] scanned %d packets; no IPv6/SRH frame found" % seen)
    return None


# ---------------------------------------------------------------------------
# Configured wire values (from JSON export of source ixncfg)
# ---------------------------------------------------------------------------

ETH_DST = "00:00:00:00:00:00"
ETH_SRC = "00:00:00:00:00:00"
IPV6_SRC = "2001:0:1::"
IPV6_DST = "3001:0:1::"
IPV6_HOP_LIMIT = 64

SEGMENTS_LEFT = 7
LAST_ENTRY = (
    0  # source JSON value; TCL srCheckList(2) expects 9 — see docstring
)
TAG = 0
FLAG_PROTECTED = 0
FLAG_ALERT = 0

# Slot order from JSON ipv6SID1..ipv6SID10. Differs from TC001021141: the
# first slot here is aa:: (was 10::), then 99::, 88::, ... 11::.
SEGMENTS = [
    "aa::",
    "99::",
    "88::",
    "77::",
    "66::",
    "55::",
    "44::",
    "33::",
    "22::",
    "11::",
]


def _build_config(b2b_raw_config):
    config = b2b_raw_config
    config.flows.clear()
    p1, p2 = config.ports

    f = config.flows.add(name="srh_tc1021557")
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_seconds.seconds = 30
    f.size.fixed = 256  # JSON had 106 (too small for SRH); 256 fits Eth+IPv6+SRH=222 with margin
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
    for addr in SEGMENTS:
        sr.segment_list.segment()[-1].segment.value = addr

    # NOT SUPPORTED IN MODEL — five SRH optional sub-TLVs from JSON have no
    # snappi representation:
    #   sripv6IngressNodeTLV    (type=1, length=18, flags=0, value=11::)
    #   sripv6EgressNodeTLV     (type=2, length=18, reserved=0, flags=0, value=aa::)
    #   sripv6OpaqueContainerTLV (type=3, length=18, reserved=0, flags=0, value=::22)
    #   pathTraceTLV            (type=128, length=14, ifId/ifLd/timeStamp/
    #                            sessionId/sequenceNo all 0)
    #   sripv6PaddingTLV        (type=4, length=2, pad=0x1111)
    # The snappi-driven flow emits SRH base + segment list only.

    _add_capture(config, p2.name)
    return config


def test_tc001021557_isis_sr_ipv6_rawtraffic_optional_tlv(
    api, b2b_raw_config, utils
):
    tc = "test_tc001021557_isis_sr_ipv6_rawtraffic_optional_tlv"
    api.set_config(api.config())
    config = _build_config(b2b_raw_config)
    api.set_config(config)

    _start_capture(api)
    _start_traffic(api)
    time.sleep(32)  # 30 s traffic + 2 s drain (matches TCL `after 30000`)
    _stop_traffic(api)
    _stop_capture(api)

    # ── Phase A — TCL parity (loss check, lines 245–262) ───────────────────
    req = api.metrics_request()
    req.flow.flow_names = ["srh_tc1021557"]
    metrics = api.get_metrics(req).flow_metrics
    assert len(metrics) == 1
    m = metrics[0]
    print("\n  [stats] frames_tx=%d frames_rx=%d" % (m.frames_tx, m.frames_rx))
    assert m.frames_tx > 0, "no frames sent"
    assert (
        m.frames_rx == m.frames_tx
    ), "loss != 0: frames_tx=%d frames_rx=%d" % (m.frames_tx, m.frames_rx)

    # ── Phase B — SRH wire content (TCL match list lines 349–413) ─────────
    # NOTE: the TCL srCheckList(2) also asserts SRH optional TLV contents
    # (Ingress/Egress/Opaque/Padding/Path-Trace). Those TLVs are NOT
    # configured by this snappi flow (no model representation) and so are
    # NOT verified here.
    pcap = _get_capture(api, config.ports[1].name)
    _save_capture(pcap, tc)
    srh = _parse_srh_from_pcap(pcap)
    assert srh is not None, "no SRH packet found in capture"

    sep = "=" * 62
    print("\n%s\n  %s  [SRH wire verify]\n%s" % (sep, tc, "-" * 62))
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
    for i, s in enumerate(srh["segments"]):
        exp = _norm(SEGMENTS[i]) if i < len(SEGMENTS) else "?"
        print("  segment[%d]      : %-36s  (expect %s)" % (i, s, exp))
    print(sep)

    assert srh["routing_type"] == 4
    assert srh["segments_left"] == SEGMENTS_LEFT
    assert srh["last_entry"] == LAST_ENTRY
    assert srh["flags_byte"] == 0x00
    assert srh["tag"] == TAG

    # last_entry from JSON is 0 -> only segment[0] is "valid" per RFC 8754;
    # the parser reads (last_entry+1) segments, so we compare exactly that
    # many entries against the configured slot order.
    expected = [_norm(a) for a in SEGMENTS[: srh["last_entry"] + 1]]
    actual = [_norm(s) for s in srh["segments"]]
    assert actual == expected, (
        "Segment list mismatch (last_entry=%d).\n  configured slots: %s\n  on wire:          %s"
        % (srh["last_entry"], expected, actual)
    )

    _delete_capture(tc)
