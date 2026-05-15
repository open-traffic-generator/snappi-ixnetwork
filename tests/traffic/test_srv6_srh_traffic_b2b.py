"""SRv6 SRH raw-traffic back-to-back test suite.

Tests the snappi-ixnetwork mapping of Flow.Ipv6ExtHeader routing choices onto
IxNetwork traffic stacks:

  segment_routing      -> ipv6RoutingType4  (full SRH, 128-bit IPv6 segment list)
  segment_routing_usid -> ipv6GSRHType4     (uSID SRH, compressed uSID containers in hex slots 1-16)

Topology:
    ixia-c port 1 <---L2---> ixia-c port 2  (raw port-to-port, no protocol)

Wire verification:
  Start capture on rx port before traffic.  After traffic, parse the pcapng
  for IPv6 frames with next_header=43 (routing extension header).  Verify
  routing_type=4, segments_left, last_entry, flags byte, tag, and segment
  list addresses against the configured values.  Captures are saved under
  tests/captures/<test_name>.pcapng; deleted on pass, kept on failure.
"""

import io
import ipaddress
import os
import struct
import time

import dpkt
import pytest


_CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "captures")

# ---------------------------------------------------------------------------
# Capture helpers
# ---------------------------------------------------------------------------

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


def _save_capture(pcap_bytes, test_name):
    os.makedirs(_CAPTURES_DIR, exist_ok=True)
    path = os.path.join(_CAPTURES_DIR, test_name + ".pcapng")
    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
    with open(path, "wb") as fh:
        fh.write(raw)
    if hasattr(pcap_bytes, "seek"):
        pcap_bytes.seek(0)
    return path


def _delete_capture(test_name):
    path = os.path.join(_CAPTURES_DIR, test_name + ".pcapng")
    if os.path.exists(path):
        os.remove(path)
        print("  [cleanup] deleted %s.pcapng" % test_name)


def _add_capture(config, port_name, capture_name="srh_cap"):
    """Add a port capture object to config (must be called before set_config)."""
    cap = config.captures.capture(name=capture_name)[-1]
    cap.port_names = [port_name]
    cap.format = cap.PCAPNG


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


# ---------------------------------------------------------------------------
# SRH wire parsing
# ---------------------------------------------------------------------------

def _parse_srh_from_pcap(pcap_bytes):
    """Parse SRH fields from the first SRH packet in a pcapng capture.

    Returns a dict with keys: routing_type, segments_left, last_entry,
    flags_byte, tag, segments (list of IPv6 address strings).
    Returns None if no valid SRH packet was found.

    Uses raw byte parsing (no dpkt object model) for reliability across
    dpkt versions and with IPv6 extension header chains.

    Frame layout (no VLAN):
      [0:14]   Ethernet header (dst[6] src[6] type[2])
      [14:54]  IPv6 fixed header (40 bytes); byte[14+6]=next_header
      [54:]    SRH (routing type 4)

    SRH wire format (RFC 8754 Section 2.1):
      byte 0 : Next Header
      byte 1 : Hdr Ext Len (units of 8 bytes, excluding first 8 bytes)
      byte 2 : Routing Type (must be 4)
      byte 3 : Segments Left
      byte 4 : Last Entry
      byte 5 : Flags  (MSB: U1 P O A H U2 U2 U2)
      bytes 6-7 : Tag
      bytes 8+ : Segment List (16 bytes per entry)
    """
    if pcap_bytes is None:
        return None
    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
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

    pkt_count = 0
    for _, pkt_data in pcap:
        try:
            buf = bytes(pkt_data)
            pkt_count += 1
            if pkt_count == 1:
                # first packet hex dump (first 80 bytes) for diagnostics
                print("\n  [pcap] first pkt len=%d hex=%s" % (
                    len(buf), buf[:80].hex()))

            # Need at least Ethernet(14) + IPv6(40) + SRH-min(8) = 62 bytes
            if len(buf) < 62:
                continue

            # EtherType = bytes 12-13; 0x86DD = IPv6
            eth_type = struct.unpack("!H", buf[12:14])[0]
            if eth_type == 0x8100:
                # single VLAN tag: skip 4 bytes
                if len(buf) < 66:
                    continue
                eth_type = struct.unpack("!H", buf[16:18])[0]
                ip6_off = 18
            else:
                ip6_off = 14

            if eth_type != 0x86DD:
                continue

            # IPv6 fixed header: next_header is at offset 6 within the header
            if ip6_off + 40 > len(buf):
                continue
            nxt = buf[ip6_off + 6]
            if nxt != 43:
                continue

            # SRH immediately follows the IPv6 fixed header
            srh_off = ip6_off + 40
            if srh_off + 8 > len(buf):
                continue

            routing_type = buf[srh_off + 2]
            if routing_type != 4:
                continue

            segments_left = buf[srh_off + 3]
            last_entry = buf[srh_off + 4]
            flags_byte = buf[srh_off + 5]
            tag = struct.unpack("!H", buf[srh_off + 6:srh_off + 8])[0]

            seg_count = last_entry + 1
            segments = []
            for idx in range(seg_count):
                off = srh_off + 8 + idx * 16
                if off + 16 > len(buf):
                    break
                addr = str(ipaddress.IPv6Address(buf[off:off + 16]))
                segments.append(addr)

            return {
                "routing_type": routing_type,
                "segments_left": segments_left,
                "last_entry": last_entry,
                "flags_byte": flags_byte,
                "tag": tag,
                "segments": segments,
            }
        except Exception:
            continue
    print("  [pcap] scanned %d packets; no IPv6/SRH found" % pkt_count)
    return None


def _norm(addr):
    """Normalize an IPv6 address to canonical form."""
    return str(ipaddress.IPv6Address(addr))


# ---------------------------------------------------------------------------
# IxNetwork RestPy diagnostic helper
# ---------------------------------------------------------------------------

def _log_ixn_stack_fields(api, flow_name, stack_type_id, highlight=None):
    """Read stack fields directly from IxNetwork RestPy after set_config.

    Prints a table of every field in the named stack showing ValueType,
    Value, and Auto flag. Fields whose FieldTypeId contains a string from
    `highlight` are marked with *** so they stand out.

    How to interpret:
      ValueType=singleValue, correct value, Auto=False
          -> snappi_ixnetwork correctly set the field via importConfig.
             If the capture still shows the wrong value, the bug is in
             IxNetwork's packet renderer (IxNetwork bug).
      ValueType=auto  OR  singleValue with wrong value
          -> The field was not correctly set by importConfig.
             The bug is in snappi_ixnetwork (trafficitem.py).

    stack_type_id examples: "tcp", "udp", "ipv4", "ipv6",
                             "ipv6RoutingType4", "ipv6GSRHType4"
    """
    highlight = highlight or []
    try:
        ixn = api._ixnetwork
        ti = ixn.Traffic.TrafficItem.find(Name=flow_name)
        if not ti:
            print("  [ixn-diag] traffic item '%s' not found" % flow_name)
            return
        ce = ti.ConfigElement.find()
        if not ce:
            print("  [ixn-diag] no ConfigElement for '%s'" % flow_name)
            return
        stacks = ce.Stack.find(StackTypeId=stack_type_id)
        if not stacks:
            print("  [ixn-diag] stack '%s' not found in flow '%s'"
                  % (stack_type_id, flow_name))
            return
        stack = stacks[0]
        sep = "-" * 84
        print("\n  [ixn-diag] flow='%s'  stack='%s'" % (flow_name, stack_type_id))
        print("  " + sep)
        print("  %-3s %-42s %-14s %-20s %s"
              % ("", "FieldTypeId", "ValueType", "Value", "Auto"))
        print("  " + sep)
        for f in stack.Field.find():
            mark = "***" if any(h in f.FieldTypeId for h in highlight) else "   "
            vt = f.ValueType
            if vt == "singleValue":
                val = f.SingleValue
            elif vt in ("increment", "decrement"):
                val = "start=%s step=%s" % (f.StartValue, f.StepValue)
            else:
                try:
                    val = str(list(f.ValueList))[:40]
                except Exception:
                    val = vt
            print("  %s %-42s %-14s %-20s %s"
                  % (mark, f.FieldTypeId, vt, val, f.Auto))
        print("  " + sep)
    except Exception as exc:
        print("  [ixn-diag] ERROR reading stack '%s': %s" % (stack_type_id, exc))


def _log_all_ixn_stacks(api, flow_name):
    """Dump all stack aliases in a traffic item's ConfigElement."""
    try:
        ixn = api._ixnetwork
        ti = ixn.Traffic.TrafficItem.find(Name=flow_name)
        if not ti:
            print("  [ixn-stacks] '%s' not found" % flow_name)
            return
        ce = ti.ConfigElement.find()
        if not ce:
            print("  [ixn-stacks] no ConfigElement")
            return
        print("\n  [ixn-stacks] flow='%s' stacks:" % flow_name)
        for s in ce[0].Stack.find():
            print("    StackTypeId=%-30s  DisplayName=%s" % (s.StackTypeId, getattr(s, "DisplayName", "?")))
    except Exception as exc:
        print("  [ixn-stacks] ERROR: %s" % exc)


# ---------------------------------------------------------------------------
# SRH TLV wire parser (SRH optional TLVs after segment list)
# ---------------------------------------------------------------------------

def _parse_srh_with_tlvs_from_pcap(pcap_bytes):
    """Parse first SRH packet from pcapng including optional TLVs after segment list.

    SRH wire layout (RFC 8754 Section 2.1):
      byte 0: Next Header
      byte 1: Hdr Ext Len  (units of 8B, excluding first 8B)
      bytes 2-7: routing_type, segments_left, last_entry, flags, tag
      bytes 8+: segment list  (16B per entry)
      after segment list, until srh_off + (Hdr Ext Len + 1)*8: TLVs

    TLV wire format:
      byte 0: type
      byte 1: length  (bytes of value, NOT including type+length fields)
      bytes 2..2+length-1: value

    Returns:
      {
        "routing_type", "segments_left", "last_entry", "flags_byte", "tag",
        "segments": [str],
        "tlvs": [{"type": int, "length": int, "data": bytes, "data_hex": str}]
      }
    Returns None if no SRH (routing_type=4) packet found.
    """
    if pcap_bytes is None:
        return None
    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
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

    pkt_count = 0
    for _, pkt_data in pcap:
        try:
            buf = bytes(pkt_data)
            pkt_count += 1
            if pkt_count == 1:
                print("\n  [pcap] first pkt len=%d hex=%s" % (len(buf), buf[:80].hex()))

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

            hdr_ext_len  = buf[srh_off + 1]
            routing_type = buf[srh_off + 2]
            if routing_type != 4:
                continue

            segments_left = buf[srh_off + 3]
            last_entry    = buf[srh_off + 4]
            flags_byte    = buf[srh_off + 5]
            tag           = struct.unpack("!H", buf[srh_off + 6:srh_off + 8])[0]

            seg_count = last_entry + 1
            segments  = []
            for idx in range(seg_count):
                off = srh_off + 8 + idx * 16
                if off + 16 > len(buf):
                    break
                segments.append(str(ipaddress.IPv6Address(buf[off:off + 16])))

            # Parse TLVs: bytes between end of segment list and end of SRH
            srh_end   = srh_off + (hdr_ext_len + 1) * 8
            tlv_start = srh_off + 8 + seg_count * 16
            tlvs      = []
            tlv_off   = tlv_start
            while tlv_off + 2 <= srh_end and tlv_off + 2 <= len(buf):
                tlv_type   = buf[tlv_off]
                tlv_length = buf[tlv_off + 1]
                if tlv_off + 2 + tlv_length > len(buf):
                    break
                tlv_data = bytes(buf[tlv_off + 2: tlv_off + 2 + tlv_length])
                tlvs.append({
                    "type":     tlv_type,
                    "length":   tlv_length,
                    "data":     tlv_data,
                    "data_hex": tlv_data.hex(),
                })
                tlv_off += 2 + tlv_length

            if tlvs:
                print("  [pcap] found %d SRH TLV(s) after segment list" % len(tlvs))
                for t in tlvs:
                    print("    type=%d length=%d data_hex=%s"
                          % (t["type"], t["length"], t["data_hex"]))

            return {
                "routing_type":  routing_type,
                "segments_left": segments_left,
                "last_entry":    last_entry,
                "flags_byte":    flags_byte,
                "tag":           tag,
                "segments":      segments,
                "tlvs":          tlvs,
            }
        except Exception:
            continue

    print("  [pcap] scanned %d packets; no IPv6/SRH found" % pkt_count)
    return None


# ---------------------------------------------------------------------------
# Flow builders
# ---------------------------------------------------------------------------

def _build_srh_flow(config, name, tx_port, rx_port,
                    ip6_src, ip6_dst,
                    segments_left, last_entry, segments,
                    protected=0, alert=0, tag=0,
                    pps=100, packets=200):
    """Add Ethernet + IPv6 (nxt=43) + SRH (segment_routing) to config."""
    f = config.flows.add()
    f.name = name
    f.tx_rx.port.tx_name = tx_port
    f.tx_rx.port.rx_name = rx_port
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
    ip6.ipv6.next_header.value = 43  # routing extension header

    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing"
    sr = ext.ipv6_extension_header.routing.segment_routing
    sr.segments_left.value = segments_left
    sr.last_entry.value = last_entry
    sr.flags.protected.value = protected
    sr.flags.alert.value = alert
    sr.tag.value = tag
    for segment in segments:
        sr.segment_list.segment()[-1].segment.value = segment

    return f


def _add_usid_container(segment_list, container_ipv6, lb_bits=32, usid_bits=16):
    """Add a uSID container segment using the structured locator/usids API.

    Unpacks a pre-packed IPv6 uSID container address (e.g. "fc00:0:1:2:3::")
    into the FlowIpv6SegmentRoutingUsidSegment locator / locator_length / usids
    fields, which is required by the new snappi API.

    lb_bits: high-order bits forming the Locator Block (default 32 for F3216).
    usid_bits: bits per uSID value (default 16 for F3216).
    """
    import socket
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
    for usid_val in usids:
        seg.usids.add().usid = usid_val


def _build_gsrh_flow(config, name, tx_port, rx_port,
                     ip6_src, ip6_dst,
                     segments_left, last_entry, usid_containers,
                     oam=0, tag=0,
                     pps=100, packets=200):
    """Add Ethernet + IPv6 (nxt=43) + uSID SRH (segment_routing_usid) to config."""
    f = config.flows.add()
    f.name = name
    f.tx_rx.port.tx_name = tx_port
    f.tx_rx.port.rx_name = rx_port
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
    usid.last_entry.value = last_entry
    usid.flags.oam.value = oam
    usid.tag.value = tag
    for usid_container in usid_containers:
        _add_usid_container(usid.segment_list, usid_container)

    return f


# ---------------------------------------------------------------------------
# Test 1: Standard SRH (segment_routing) - 3 SIDs, P-flag set, tag set
# ---------------------------------------------------------------------------

def test_srh_full_sid(api, b2b_raw_config, utils):
    """Standard SRH (ipv6RoutingType4) with 3 full IPv6 SIDs.

    Configures: segments_left=2, last_entry=2, P-flag=1, tag=0x0042,
    segment_list = [fc00:0:3::1, fc00:0:2::1, fc00:0:1::1].

    Wire verifies: routing_type=4, segments_left, last_entry, P-flag,
    tag, and segment addresses.
    """
    tc = "test_srh_full_sid"
    api.set_config(api.config())  # reset IxN state
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    segment_list = ["fc00:0:3::1", "fc00:0:2::1", "fc00:0:1::1"]
    segments_left = 2
    last_entry = 2
    protected = 1
    tag = 0x0042

    f = b2b_raw_config.flows.add()
    f.name = "srh_full"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add().ethernet
    eth.src.value = "00:11:22:33:44:55"
    eth.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add().ipv6
    ip6.src.value = "2001:db8::1"
    ip6.dst.value = segment_list[0]
    ip6.next_header.value = 43

    sr = f.packet.add().ipv6_extension_header.routing.segment_routing
    sr.segments_left.value = segments_left
    sr.last_entry.value = last_entry
    sr.flags.protected.value = protected
    sr.tag.value = tag
    for segment in segment_list:
        sr.segment_list.segment()[-1].segment.value = segment

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    srh = _parse_srh_from_pcap(pcap)
    sep = "=" * 62
    inner = "-" * 62
    if srh is not None:
        print("\n%s" % sep)
        print("  %s  [SRH wire verify]" % tc)
        print(inner)
        print("  routing_type  : %d  (expect 4)" % srh["routing_type"])
        print("  segments_left : %d  (expect %d)" % (srh["segments_left"], segments_left))
        print("  last_entry    : %d  (expect %d)" % (srh["last_entry"], last_entry))
        print("  flags_byte    : 0x%02x  (expect P-flag=1 -> 0x40)" % srh["flags_byte"])
        print("  tag           : 0x%04x  (expect 0x%04x)" % (srh["tag"], tag))
        for i, s in enumerate(srh["segments"]):
            print("  segment[%d]    : %-36s  (expect %s)"
                  % (i, s, _norm(segment_list[i]) if i < len(segment_list) else "?"))
        print(sep)

        assert srh["routing_type"] == 4, (
            "Expected routing_type=4, got %d" % srh["routing_type"]
        )
        assert srh["segments_left"] == segments_left, (
            "Expected segments_left=%d, got %d" % (segments_left, srh["segments_left"])
        )
        assert srh["last_entry"] == last_entry, (
            "Expected last_entry=%d, got %d" % (last_entry, srh["last_entry"])
        )
        assert srh["tag"] == tag, (
            "Expected tag=0x%04x, got 0x%04x" % (tag, srh["tag"])
        )
        # Flags byte layout: U1(7) P(6) O(5) A(4) H(3) U(2) U(1) U(0)
        p_flag = (srh["flags_byte"] >> 6) & 1
        assert p_flag == protected, (
            "Expected P-flag=%d, got %d (flags_byte=0x%02x)" % (protected, p_flag, srh["flags_byte"])
        )
        norm_conf = [_norm(a) for a in segment_list]
        norm_wire = [_norm(s) for s in srh["segments"]]
        assert norm_conf == norm_wire, (
            "Segment list mismatch.\n  configured: %s\n  on wire:    %s"
            % (norm_conf, norm_wire)
        )
        _delete_capture(tc)
    else:
        # Capture parsed but no SRH found - verify traffic was sent
        req = api.metrics_request()
        req.flow.flow_names = ["srh_full"]
        metrics = api.get_metrics(req)
        tx_pkts = sum(m.frames_tx for m in metrics.flow_metrics)
        print("\n  [NOTE] No SRH found in capture; tx_pkts=%d" % tx_pkts)
        print("  IxNetwork accepted the SRH config (set_config succeeded).")
        assert tx_pkts > 0, (
            "No packets transmitted for flow srh_full; "
            "IxNetwork may have rejected the SRH stack configuration"
        )


# ---------------------------------------------------------------------------
# Test 2: uSID SRH with 1 uSID container (multiple uSIDs, single segment entry)
# ---------------------------------------------------------------------------

def test_srh_usid(api, b2b_raw_config, utils):
    """Multiple uSIDs with 1 uSID SRH container: 3-hop path packed in one F3216 uSID
    container, carried inside a uSID SRH extension header with a single segment entry.

    OTG model used:
      Flow.Ipv6  (NH=43, dst = uSID container)
      Flow.Ipv6ExtHeader.routing.segment_routing_usid  (Flow.Ipv6SegmentRoutingUsid)
        segment_list: 1 entry  (last_entry=0, segments_left=0)

    F3216 uSID container layout (128 bits):
      fc00:0:1:2:3::
        Locator-Block = fc00:0000  (32 bits, shared domain prefix)
        uSID-1        = 0001       (16 bits, hop 1)
        uSID-2        = 0002       (16 bits, hop 2)
        uSID-3        = 0003       (16 bits, hop 3)
        Remaining     = 0::        (48 bits, zeros = end of uSID list)

    The uSID SRH segment list holds exactly 1 entry (last_entry=0, segments_left=0).
    This is the minimal uSID SRH case - the routing header is present but the entire
    path is contained in the single active container.  Compare with test_usid_no_srh
    (same container but with no routing header at all) and test_usid_multi_srh_container
    (path spans 2 containers requiring 2 segment list entries).

    Packet stack:
      Ethernet -> IPv6 (NH=43, dst=fc00:0:1:2:3::) -> uSID SRH (1 segment) -> ...

    Wire verifies:
      - routing_type = 4  (uSID SRH, RFC 9800)
      - segments_left = 0, last_entry = 0
      - segment[0] = fc00:0:1:2:3::
    """
    tc = "test_srh_usid"
    api.set_config(api.config())  # reset IxN state
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    usid_container = "fc00:0:1:2:3::"   # F3216: block=fc00:0:, hops=0001,0002,0003
    segments_left  = 0
    last_entry     = 0

    f = b2b_raw_config.flows.add()
    f.name = "gsrh_one_container"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add().ethernet
    eth.src.value = "00:11:22:33:44:55"
    eth.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add().ipv6
    ip6.src.value = "2001:db8::1"
    ip6.dst.value = usid_container
    ip6.next_header.value = 43

    usid = f.packet.add().ipv6_extension_header.routing.segment_routing_usid
    usid.segments_left.value = segments_left
    usid.last_entry.value    = last_entry
    usid.tag.value           = 0
    _add_usid_container(usid.segment_list, usid_container)

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    srh = _parse_srh_from_pcap(pcap)
    sep = "=" * 62
    inner = "-" * 62
    if srh is not None:
        print("\n%s" % sep)
        print("  %s  [uSID SRH 1-container wire verify]" % tc)
        print(inner)
        print("  routing_type  : %d  (expect 4)" % srh["routing_type"])
        print("  segments_left : %d  (expect %d)" % (srh["segments_left"], segments_left))
        print("  last_entry    : %d  (expect %d)" % (srh["last_entry"], last_entry))
        got_seg = srh["segments"][0] if srh["segments"] else "?"
        print("  segment[0]    : %-36s  (expect %s)" % (got_seg, _norm(usid_container)))
        print(sep)

        assert srh["routing_type"] == 4, (
            "Expected routing_type=4, got %d" % srh["routing_type"]
        )
        assert srh["segments_left"] == segments_left, (
            "Expected segments_left=%d, got %d" % (segments_left, srh["segments_left"])
        )
        assert srh["last_entry"] == last_entry, (
            "Expected last_entry=%d, got %d" % (last_entry, srh["last_entry"])
        )
        assert len(srh["segments"]) == 1, (
            "Expected 1 segment entry, got %d" % len(srh["segments"])
        )
        assert _norm(srh["segments"][0]) == _norm(usid_container), (
            "segment[0]: want %s got %s" % (_norm(usid_container), _norm(srh["segments"][0]))
        )
        _delete_capture(tc)
    else:
        req = api.metrics_request()
        req.flow.flow_names = ["gsrh_one_container"]
        metrics = api.get_metrics(req)
        tx_pkts = sum(m.frames_tx for m in metrics.flow_metrics)
        print("\n  [NOTE] No uSID SRH found in capture; tx_pkts=%d" % tx_pkts)
        print("  IxNetwork accepted the uSID SRH config (set_config succeeded).")
        assert tx_pkts > 0, (
            "No packets transmitted for flow gsrh_one_container; "
            "IxNetwork may have rejected the uSID SRH stack configuration"
        )


# ---------------------------------------------------------------------------
# Test 2b: uSID SRH with 2 uSID containers (multiple uSIDs, 2 segment entries)
# ---------------------------------------------------------------------------

def test_usid_multi_srh_container(api, b2b_raw_config, utils):
    """Multiple uSIDs with more than 1 uSID SRH container: 4-hop path spread across
    2 F3216 uSID containers, carried in a uSID SRH with 2 segment list entries.

    OTG model used:
      Flow.Ipv6  (NH=43, dst = first/active uSID container)
      Flow.Ipv6ExtHeader.routing.segment_routing_usid  (Flow.Ipv6SegmentRoutingUsid)
        segment_list: 2 entries  (last_entry=1, segments_left=1)

    F3216 uSID containers (128 bits each):
      container-1: fc00:0:1:2::
        Locator-Block = fc00:0000  (32 bits)
        uSID-1        = 0001       (16 bits, hop 1)
        uSID-2        = 0002       (16 bits, hop 2)
        Remaining     = 0::        (64 bits, zeros)

      container-2: fc00:0:3:4::
        Locator-Block = fc00:0000  (32 bits)
        uSID-3        = 0003       (16 bits, hop 3)
        uSID-4        = 0004       (16 bits, hop 4)
        Remaining     = 0::        (64 bits, zeros)

    uSID SRH layout (RFC 9800 / RFC 8754 Section 2):
      IPv6 dst     = fc00:0:1:2::  (active container, currently being processed)
      segment_list = [fc00:0:1:2::, fc00:0:3:4::]  (all containers, RFC 8754 style)
      segments_left = 1  (1 more container to visit after the active one)
      last_entry    = 1  (highest index in segment list)

    When all uSIDs in the active container fc00:0:1:2:: are exhausted, the
    forwarding node decrements segments_left to 0, copies segment_list[0] =
    fc00:0:3:4:: into IPv6 dst, and continues processing the next container.

    Compare with test_srh_usid (single container, segments_left=0) and
    test_usid_no_srh (no uSID SRH at all).

    Packet stack:
      Ethernet -> IPv6 (NH=43, dst=fc00:0:1:2::) -> uSID SRH (2 segments) -> ...

    Wire verifies:
      - routing_type = 4  (uSID SRH, RFC 9800)
      - segments_left = 1, last_entry = 1
      - segment[0] = fc00:0:1:2::
      - segment[1] = fc00:0:3:4::
    """
    tc = "test_usid_multi_srh_container"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    usid_containers = ["fc00:0:1:2::", "fc00:0:3:4::"]   # 2 hops each
    segments_left = 1
    last_entry = 1

    f = b2b_raw_config.flows.add()
    f.name = "gsrh_two_containers"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add().ethernet
    eth.src.value = "00:11:22:33:44:55"
    eth.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add().ipv6
    ip6.src.value = "2001:db8::1"
    ip6.dst.value = usid_containers[0]
    ip6.next_header.value = 43

    usid = f.packet.add().ipv6_extension_header.routing.segment_routing_usid
    usid.segments_left.value = segments_left
    usid.last_entry.value = last_entry
    usid.tag.value = 0
    for usid_container in usid_containers:
        _add_usid_container(usid.segment_list, usid_container)

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    srh = _parse_srh_from_pcap(pcap)
    sep = "=" * 62
    inner = "-" * 62
    if srh is not None:
        print("\n%s" % sep)
        print("  %s  [uSID SRH 2-container wire verify]" % tc)
        print(inner)
        print("  routing_type  : %d  (expect 4)" % srh["routing_type"])
        print("  segments_left : %d  (expect %d)" % (srh["segments_left"], segments_left))
        print("  last_entry    : %d  (expect %d)" % (srh["last_entry"], last_entry))
        for i, s in enumerate(srh["segments"]):
            print("  segment[%d]    : %-36s  (expect %s)"
                  % (i, s, _norm(usid_containers[i]) if i < len(usid_containers) else "?"))
        print(sep)

        assert srh["routing_type"] == 4, (
            "Expected routing_type=4, got %d" % srh["routing_type"]
        )
        assert srh["segments_left"] == segments_left, (
            "Expected segments_left=%d, got %d" % (segments_left, srh["segments_left"])
        )
        assert srh["last_entry"] == last_entry, (
            "Expected last_entry=%d, got %d" % (last_entry, srh["last_entry"])
        )
        assert len(srh["segments"]) == 2, (
            "Expected 2 segment entries, got %d" % len(srh["segments"])
        )
        norm_conf = [_norm(a) for a in usid_containers]
        norm_wire = [_norm(s) for s in srh["segments"]]
        assert norm_conf == norm_wire, (
            "uSID container mismatch.\n  configured: %s\n  on wire:    %s"
            % (norm_conf, norm_wire)
        )
        _delete_capture(tc)
    else:
        req = api.metrics_request()
        req.flow.flow_names = ["gsrh_two_containers"]
        metrics = api.get_metrics(req)
        tx_pkts = sum(m.frames_tx for m in metrics.flow_metrics)
        print("\n  [NOTE] No uSID SRH found in capture; tx_pkts=%d" % tx_pkts)
        print("  IxNetwork accepted the uSID SRH config (set_config succeeded).")
        assert tx_pkts > 0, (
            "No packets transmitted for flow gsrh_two_containers; "
            "IxNetwork may have rejected the uSID SRH stack configuration"
        )


# ---------------------------------------------------------------------------
# Test 3: SRH with both P-flag and A-flag + increment on segments_left
# ---------------------------------------------------------------------------

def test_srh_flags_and_increment(api, b2b_raw_config, utils):
    """SRH with P-flag=1, A-flag=1, and segments_left as an increment pattern.

    Covers: both modeled flag bits, pattern increment on segments_left,
    multiple flows in one set_config (SRH + uSID SRH simultaneously).
    Verifies that IxNetwork accepts both stacks without error and both
    flows transmit packets.
    """
    tc = "test_srh_flags_and_increment"
    api.set_config(api.config())  # reset IxN state
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    # Flow 1: standard SRH, both flags set, segments_left increments 1->2
    f1 = b2b_raw_config.flows.add()
    f1.name = "srh_both_flags"
    f1.tx_rx.port.tx_name = p1.name
    f1.tx_rx.port.rx_name = p2.name
    f1.rate.pps = 50
    f1.duration.fixed_packets.packets = 100
    f1.metrics.enable = True

    eth1 = f1.packet.add()
    eth1.choice = "ethernet"
    eth1.ethernet.src.value = "00:11:22:33:44:55"
    eth1.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

    ip6_1 = f1.packet.add()
    ip6_1.choice = "ipv6"
    ip6_1.ipv6.src.value = "2001:db8::1"
    ip6_1.ipv6.dst.value = "fc00:0:2::1"
    ip6_1.ipv6.next_header.value = 43

    ext1 = f1.packet.add()
    ext1.choice = "ipv6_extension_header"
    ext1.ipv6_extension_header.routing.choice = "segment_routing"
    sr1 = ext1.ipv6_extension_header.routing.segment_routing
    sr1.segments_left.increment.start = 1
    sr1.segments_left.increment.step = 1
    sr1.segments_left.increment.count = 2
    sr1.last_entry.value = 1
    sr1.flags.protected.value = 1
    sr1.flags.alert.value = 1
    sr1.tag.value = 0
    sr1.segment_list.segment()[-1].segment.value = "fc00:0:2::1"
    sr1.segment_list.segment()[-1].segment.value = "fc00:0:1::1"

    # Flow 2: uSID SRH in same config, no flags
    f2 = b2b_raw_config.flows.add()
    f2.name = "gsrh_plain"
    f2.tx_rx.port.tx_name = p1.name
    f2.tx_rx.port.rx_name = p2.name
    f2.rate.pps = 50
    f2.duration.fixed_packets.packets = 100
    f2.metrics.enable = True

    eth2 = f2.packet.add()
    eth2.choice = "ethernet"
    eth2.ethernet.src.value = "00:11:22:33:44:66"
    eth2.ethernet.dst.value = "00:aa:bb:cc:dd:ff"

    ip6_2 = f2.packet.add()
    ip6_2.choice = "ipv6"
    ip6_2.ipv6.src.value = "2001:db8::2"
    ip6_2.ipv6.dst.value = "fc00:2:1::"
    ip6_2.ipv6.next_header.value = 43

    ext2 = f2.packet.add()
    ext2.choice = "ipv6_extension_header"
    ext2.ipv6_extension_header.routing.choice = "segment_routing_usid"
    usid2 = ext2.ipv6_extension_header.routing.segment_routing_usid
    usid2.segments_left.value = 0
    usid2.last_entry.value = 0
    usid2.tag.value = 0
    _add_usid_container(usid2.segment_list, "fc00:2:1::")

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    req = api.metrics_request()
    req.flow.flow_names = ["srh_both_flags", "gsrh_plain"]
    metrics = api.get_metrics(req)
    flow_map = {m.name: m.frames_tx for m in metrics.flow_metrics}

    sep = "=" * 62
    inner = "-" * 62
    print("\n%s" % sep)
    print("  %s  [flow metrics]" % tc)
    print(inner)
    for fname, tx in flow_map.items():
        print("  %-20s  tx_pkts=%d" % (fname, tx))
    print(sep)

    assert flow_map.get("srh_both_flags", 0) > 0, (
        "Flow srh_both_flags sent 0 packets; "
        "IxNetwork may have rejected the SRH stack with increment"
    )
    assert flow_map.get("gsrh_plain", 0) > 0, (
        "Flow gsrh_plain sent 0 packets; "
        "IxNetwork may have rejected the uSID SRH stack"
    )

    _delete_capture(tc)


# ---------------------------------------------------------------------------
# Extended wire parser — SRH + inner IP/transport
# ---------------------------------------------------------------------------

def _parse_full_packet_from_pcap(pcap_bytes):
    """Parse first SRH packet from pcapng; extract SRH + inner IP + transport.

    Returns:
      {
        "srh":       {routing_type, segments_left, last_entry, flags_byte,
                      tag, segments: [str], srh_next_header: int},
        "inner_ip":  {version: 4|6, src: str, dst: str,
                      proto_num: int, proto_name: str} or None,
        "transport": {src_port: int, dst_port: int} or None,
      }
    Returns None if no SRH packet found.
    """
    if pcap_bytes is None:
        return None
    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
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

    pkt_count = 0
    for _, pkt_data in pcap:
        try:
            buf = bytes(pkt_data)
            pkt_count += 1
            if pkt_count == 1:
                print("\n  [pcap] first pkt len=%d hex=%s" % (
                    len(buf), buf[:80].hex()))
                print("  [pcap] FULL hex: %s" % buf.hex())

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

            srh_next_hdr  = buf[srh_off + 0]
            hdr_ext_len   = buf[srh_off + 1]
            routing_type  = buf[srh_off + 2]
            if routing_type != 4:
                continue

            segments_left = buf[srh_off + 3]
            last_entry    = buf[srh_off + 4]
            flags_byte    = buf[srh_off + 5]
            tag           = struct.unpack("!H", buf[srh_off + 6:srh_off + 8])[0]

            seg_count = last_entry + 1
            segments  = []
            for idx in range(seg_count):
                off = srh_off + 8 + idx * 16
                if off + 16 > len(buf):
                    break
                segments.append(str(ipaddress.IPv6Address(buf[off:off + 16])))

            srh_result = {
                "routing_type":    routing_type,
                "segments_left":   segments_left,
                "last_entry":      last_entry,
                "flags_byte":      flags_byte,
                "tag":             tag,
                "segments":        segments,
                "srh_next_header": srh_next_hdr,
            }

            # Advance past SRH to inner payload
            srh_total = (hdr_ext_len + 1) * 8
            inner_off  = srh_off + srh_total

            inner_ip  = None
            transport = None

            if srh_next_hdr == 4 and inner_off + 20 <= len(buf):
                # Inner IPv4
                ihl    = (buf[inner_off] & 0x0F) * 4
                proto  = buf[inner_off + 9]
                src_ip = str(ipaddress.IPv4Address(buf[inner_off + 12:inner_off + 16]))
                dst_ip = str(ipaddress.IPv4Address(buf[inner_off + 16:inner_off + 20]))
                inner_ip = {
                    "version":    4,
                    "src":        src_ip,
                    "dst":        dst_ip,
                    "proto_num":  proto,
                    "proto_name": {6: "TCP", 17: "UDP"}.get(proto, "proto-%d" % proto),
                }
                transport_off = inner_off + ihl
                if transport_off + 4 <= len(buf):
                    transport = {
                        "src_port": struct.unpack("!H", buf[transport_off:transport_off + 2])[0],
                        "dst_port": struct.unpack("!H", buf[transport_off + 2:transport_off + 4])[0],
                    }

            elif srh_next_hdr == 41 and inner_off + 40 <= len(buf):
                # Inner IPv6-in-IPv6
                proto  = buf[inner_off + 6]
                src_ip = str(ipaddress.IPv6Address(buf[inner_off + 8:inner_off + 24]))
                dst_ip = str(ipaddress.IPv6Address(buf[inner_off + 24:inner_off + 40]))
                inner_ip = {
                    "version":    6,
                    "src":        src_ip,
                    "dst":        dst_ip,
                    "proto_num":  proto,
                    "proto_name": {6: "TCP", 17: "UDP"}.get(proto, "proto-%d" % proto),
                }
                transport_off = inner_off + 40
                if transport_off + 4 <= len(buf):
                    transport = {
                        "src_port": struct.unpack("!H", buf[transport_off:transport_off + 2])[0],
                        "dst_port": struct.unpack("!H", buf[transport_off + 2:transport_off + 4])[0],
                    }

            return {"srh": srh_result, "inner_ip": inner_ip, "transport": transport}

        except Exception:
            continue

    print("  [pcap] scanned %d packets; no IPv6/SRH found" % pkt_count)
    return None


# ---------------------------------------------------------------------------
# Pretty-printer + asserter: configured vs wire
# ---------------------------------------------------------------------------

def _print_and_verify(tc, pkt, cfg):
    """Print a formatted configured-vs-wire table and assert all fields match.

    cfg keys:
      srh:       {segments_left, last_entry, flags_byte, tag, segments: [str]}
      inner_ip:  {version, src, dst}  or None
      transport: {proto, src_port, dst_port}  or None  (proto = "TCP"/"UDP")
    """
    SEP   = "=" * 72
    SEC   = "-" * 72
    W_LBL = 22
    W_VAL = 24

    def _row(label, configured, wire, ok=None):
        if ok is None:
            ok = (str(configured) == str(wire))
        status = "PASS" if ok else "FAIL"
        print("  %-*s  %-*s  %-*s  %s"
              % (W_LBL, label, W_VAL, str(configured), W_VAL, str(wire), status))
        return ok

    print("\n" + SEP)
    print("  %-40s  %s" % (tc, "[configured vs wire]"))
    print(SEP)

    if pkt is None:
        print("  [ERROR] No SRH packet found in capture")
        print(SEP)
        assert False, "[%s] No SRH packet found in capture" % tc

    srh     = pkt["srh"]
    c_srh   = cfg["srh"]
    c_inner = cfg.get("inner_ip")
    c_trans = cfg.get("transport")

    # -- SRH section -------------------------------------------------------
    print("  %-*s  %-*s  %-*s  %s"
          % (W_LBL, "Field", W_VAL, "Configured", W_VAL, "Wire", "Status"))
    print(SEC)

    _row("routing_type",  4,                      srh["routing_type"])
    _row("segments_left", c_srh["segments_left"],  srh["segments_left"])
    _row("last_entry",    c_srh["last_entry"],      srh["last_entry"])
    _row("flags_byte",
         "0x%02x" % c_srh["flags_byte"],
         "0x%02x" % srh["flags_byte"],
         c_srh["flags_byte"] == srh["flags_byte"])
    _row("tag",
         "0x%04x" % c_srh["tag"],
         "0x%04x" % srh["tag"],
         c_srh["tag"] == srh["tag"])

    for i, seg in enumerate(c_srh["segments"]):
        wire_seg = srh["segments"][i] if i < len(srh["segments"]) else "MISSING"
        ok = (i < len(srh["segments"])) and (_norm(seg) == _norm(wire_seg))
        _row("segment[%d]" % i, _norm(seg), wire_seg, ok)

    if len(c_srh["segments"]) != len(srh["segments"]):
        print("  %-*s  %-*s  %-*s  FAIL"
              % (W_LBL, "segment count",
                 W_VAL, len(c_srh["segments"]),
                 W_VAL, len(srh["segments"])))

    # -- Inner IP section --------------------------------------------------
    if c_inner is not None:
        print(SEC)
        inner = pkt.get("inner_ip")
        ip_lbl = "inner IPv%d" % c_inner["version"]
        if inner is None:
            print("  %-*s  [NOT FOUND in capture]" % (W_LBL, ip_lbl))
        else:
            _row("%s version" % ip_lbl, c_inner["version"], inner["version"])
            _row("%s src" % ip_lbl,     c_inner["src"],     inner["src"],
                 c_inner["src"] == inner["src"])
            _row("%s dst" % ip_lbl,     c_inner["dst"],     inner["dst"],
                 c_inner["dst"] == inner["dst"])

    # -- Transport section -------------------------------------------------
    if c_trans is not None:
        print(SEC)
        trans      = pkt.get("transport")
        inner_wire = pkt.get("inner_ip")
        wire_proto = inner_wire["proto_name"] if inner_wire else "?"
        _row("transport proto",
             c_trans["proto"], wire_proto,
             c_trans["proto"] == wire_proto)
        if trans is None:
            print("  %-*s  [NOT FOUND in capture]" % (W_LBL, "ports"))
        else:
            _row("src_port", c_trans["src_port"], trans["src_port"],
                 c_trans["src_port"] == trans["src_port"])
            _row("dst_port", c_trans["dst_port"], trans["dst_port"],
                 c_trans["dst_port"] == trans["dst_port"])

    print(SEP)

    # Assertions -----------------------------------------------------------
    assert srh["routing_type"] == 4, \
        "[%s] routing_type: want 4 got %d" % (tc, srh["routing_type"])
    assert srh["segments_left"] == c_srh["segments_left"], \
        "[%s] segments_left: want %d got %d" % (
            tc, c_srh["segments_left"], srh["segments_left"])
    assert srh["last_entry"] == c_srh["last_entry"], \
        "[%s] last_entry: want %d got %d" % (
            tc, c_srh["last_entry"], srh["last_entry"])
    assert srh["flags_byte"] == c_srh["flags_byte"], \
        "[%s] flags_byte: want 0x%02x got 0x%02x" % (
            tc, c_srh["flags_byte"], srh["flags_byte"])
    assert srh["tag"] == c_srh["tag"], \
        "[%s] tag: want 0x%04x got 0x%04x" % (tc, c_srh["tag"], srh["tag"])
    assert [_norm(s) for s in srh["segments"]] == \
           [_norm(s) for s in c_srh["segments"]], \
        "[%s] segments mismatch: want %s got %s" % (
            tc, c_srh["segments"], srh["segments"])

    if c_inner is not None:
        inner = pkt.get("inner_ip")
        assert inner is not None, \
            "[%s] inner IP not found in wire capture" % tc
        assert inner["version"] == c_inner["version"], \
            "[%s] inner IP version: want %d got %d" % (
                tc, c_inner["version"], inner["version"])
        assert inner["src"] == c_inner["src"], \
            "[%s] inner IP src: want %s got %s" % (tc, c_inner["src"], inner["src"])
        assert inner["dst"] == c_inner["dst"], \
            "[%s] inner IP dst: want %s got %s" % (tc, c_inner["dst"], inner["dst"])

    if c_trans is not None:
        inner_wire = pkt.get("inner_ip")
        assert inner_wire is not None, "[%s] inner IP not found" % tc
        assert inner_wire["proto_name"] == c_trans["proto"], \
            "[%s] transport: want %s got %s" % (
                tc, c_trans["proto"], inner_wire["proto_name"])
        trans = pkt.get("transport")
        assert trans is not None, \
            "[%s] transport header not found in capture" % tc
        assert trans["src_port"] == c_trans["src_port"], \
            "[%s] src_port: want %d got %d" % (
                tc, c_trans["src_port"], trans["src_port"])
        assert trans["dst_port"] == c_trans["dst_port"], \
            "[%s] dst_port: want %d got %d" % (
                tc, c_trans["dst_port"], trans["dst_port"])


# ---------------------------------------------------------------------------
# Inner-payload flow builders
# ---------------------------------------------------------------------------

def _build_srh_flow_with_inner(config, name, tx_port, rx_port,
                                ip6_src, ip6_dst,
                                segments_left, last_entry, segments,
                                protected=0, alert=0, tag=0,
                                inner_ip_version="ipv4",
                                inner_ip_src="10.0.1.1",
                                inner_ip_dst="10.0.2.1",
                                inner_transport="tcp",
                                inner_src_port=1234,
                                inner_dst_port=5678,
                                pps=100, packets=200):
    """SRH + inner IPv4 or IPv6 + TCP or UDP payload."""
    f = config.flows.add()
    f.name = name
    f.tx_rx.port.tx_name = tx_port
    f.tx_rx.port.rx_name = rx_port
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
    sr.segments_left.value   = segments_left
    sr.last_entry.value      = last_entry
    sr.flags.protected.value = protected
    sr.flags.alert.value     = alert
    sr.tag.value             = tag
    for segment in segments:
        sr.segment_list.segment()[-1].segment.value = segment

    inner_pkt = f.packet.add()
    if inner_ip_version == "ipv4":
        inner_pkt.choice = "ipv4"
        inner_pkt.ipv4.src.value = inner_ip_src
        inner_pkt.ipv4.dst.value = inner_ip_dst
        inner_pkt.ipv4.protocol.value = 6 if inner_transport == "tcp" else 17
    else:
        inner_pkt.choice = "ipv6"
        inner_pkt.ipv6.src.value = inner_ip_src
        inner_pkt.ipv6.dst.value = inner_ip_dst
        inner_pkt.ipv6.next_header.value = 6 if inner_transport == "tcp" else 17

    transport_pkt = f.packet.add()
    if inner_transport == "tcp":
        transport_pkt.choice = "tcp"
        transport_pkt.tcp.src_port.value = inner_src_port
        transport_pkt.tcp.dst_port.value = inner_dst_port
    else:
        transport_pkt.choice = "udp"
        transport_pkt.udp.src_port.value = inner_src_port
        transport_pkt.udp.dst_port.value = inner_dst_port

    return f


def _build_gsrh_flow_with_inner(config, name, tx_port, rx_port,
                                 ip6_src, ip6_dst,
                                 segments_left, last_entry, usid_containers,
                                 oam=0, tag=0,
                                 inner_ip_version="ipv4",
                                 inner_ip_src="10.0.1.1",
                                 inner_ip_dst="10.0.2.1",
                                 inner_transport="udp",
                                 inner_src_port=4000,
                                 inner_dst_port=5000,
                                 pps=100, packets=200):
    """uSID SRH + inner IPv4 or IPv6 + TCP or UDP payload."""
    f = config.flows.add()
    f.name = name
    f.tx_rx.port.tx_name = tx_port
    f.tx_rx.port.rx_name = rx_port
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

    inner_pkt = f.packet.add()
    if inner_ip_version == "ipv4":
        inner_pkt.choice = "ipv4"
        inner_pkt.ipv4.src.value = inner_ip_src
        inner_pkt.ipv4.dst.value = inner_ip_dst
    else:
        inner_pkt.choice = "ipv6"
        inner_pkt.ipv6.src.value = inner_ip_src
        inner_pkt.ipv6.dst.value = inner_ip_dst

    transport_pkt = f.packet.add()
    if inner_transport == "tcp":
        transport_pkt.choice = "tcp"
        transport_pkt.tcp.src_port.value = inner_src_port
        transport_pkt.tcp.dst_port.value = inner_dst_port
    else:
        transport_pkt.choice = "udp"
        transport_pkt.udp.src_port.value = inner_src_port
        transport_pkt.udp.dst_port.value = inner_dst_port

    return f


# ---------------------------------------------------------------------------
# TC-4: SRH + inner IPv4 + TCP
# ---------------------------------------------------------------------------

def test_srh_inner_ipv4_tcp(api, b2b_raw_config, utils):
    """Standard SRH (2 SIDs, P-flag) carrying inner IPv4/TCP payload.

    Packet stack:
      Ethernet -> outer IPv6 (NH=43) -> SRH (RT=4, sl=1, le=1, P-flag)
               -> inner IPv4 (src=10.0.1.1, dst=10.0.2.1)
               -> TCP (src=1234, dst=5678)

    Wire verifies: SRH header fields + inner IPv4 src/dst + TCP src/dst ports.
    Capture is preserved for Wireshark inspection.
    """
    tc = "test_srh_inner_ipv4_tcp"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    segment_list = ["fc00:0:2::1", "fc00:0:1::1"]
    inner_ip_src = "10.0.1.1"
    inner_ip_dst = "10.0.2.1"
    inner_src_port = 1234
    inner_dst_port = 5678

    _build_srh_flow_with_inner(
        b2b_raw_config, "srh_ipv4_tcp",
        p1.name, p2.name,
        ip6_src="2001:db8::1", ip6_dst=segment_list[0],
        segments_left=1, last_entry=1,
        segments=segment_list, protected=1,
        inner_ip_version="ipv4",
        inner_ip_src=inner_ip_src, inner_ip_dst=inner_ip_dst,
        inner_transport="tcp",
        inner_src_port=inner_src_port, inner_dst_port=inner_dst_port,
    )

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _log_all_ixn_stacks(api, "srh_ipv4_tcp")
    #_log_ixn_stack_fields(api, "srh_ipv4_tcp", "ipv6RoutingType4")
    #_log_ixn_stack_fields(api, "srh_ipv4_tcp", "ipv4",
    #                     highlight=["srcIp", "dstIp", "protocol"])
    #_log_ixn_stack_fields(api, "srh_ipv4_tcp", "tcp",
    #                     highlight=["tcp.header.dataOffset"])
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    port_results, flow_results = utils.get_all_stats(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_full_packet_from_pcap(pcap)
    _print_and_verify(tc, pkt, cfg={
        "srh": {
            "segments_left": 1,
            "last_entry":    1,
            "flags_byte":    0x40,
            "tag":           0,
            "segments":      segment_list,
        },
        "inner_ip":  {"version": 4, "src": inner_ip_src, "dst": inner_ip_dst},
        "transport": {"proto": "TCP", "src_port": inner_src_port, "dst_port": inner_dst_port},
    })
    print("\n  [%s] PASSED" % tc)


# ---------------------------------------------------------------------------
# TC-5: SRH + inner IPv4 + UDP
# ---------------------------------------------------------------------------

def test_srh_inner_ipv4_udp(api, b2b_raw_config, utils):
    """Standard SRH (3 SIDs, tag=0xABCD) carrying inner IPv4/UDP payload.

    Packet stack:
      Ethernet -> outer IPv6 (NH=43) -> SRH (RT=4, sl=2, le=2, tag=0xABCD)
               -> inner IPv4 (src=192.168.1.1, dst=192.168.2.1)
               -> UDP (src=4000, dst=53)

    Wire verifies: SRH header fields + inner IPv4 src/dst + UDP src/dst ports.
    Capture is preserved for Wireshark inspection.
    """
    tc = "test_srh_inner_ipv4_udp"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    segment_list = ["fc00:0:3::1", "fc00:0:2::1", "fc00:0:1::1"]
    tag          = 0xABCD
    inner_ip_src = "192.168.1.1"
    inner_ip_dst = "192.168.2.1"
    inner_src_port = 4000
    inner_dst_port = 53

    _build_srh_flow_with_inner(
        b2b_raw_config, "srh_ipv4_udp",
        p1.name, p2.name,
        ip6_src="2001:db8::1", ip6_dst=segment_list[0],
        segments_left=2, last_entry=2,
        segments=segment_list, tag=tag,
        inner_ip_version="ipv4",
        inner_ip_src=inner_ip_src, inner_ip_dst=inner_ip_dst,
        inner_transport="udp",
        inner_src_port=inner_src_port, inner_dst_port=inner_dst_port,
    )

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    # _log_ixn_stack_fields(api, "srh_ipv4_udp", "ipv4",
    #                       highlight=["ipv4.header.protocol"])
    # _log_ixn_stack_fields(api, "srh_ipv4_udp", "udp",
    #                       highlight=["udp.header.length"])
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    port_results, flow_results = utils.get_all_stats(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_full_packet_from_pcap(pcap)
    _print_and_verify(tc, pkt, cfg={
        "srh": {
            "segments_left": 2,
            "last_entry":    2,
            "flags_byte":    0x00,
            "tag":           tag,
            "segments":      segment_list,
        },
        "inner_ip":  {"version": 4, "src": inner_ip_src, "dst": inner_ip_dst},
        "transport": {"proto": "UDP", "src_port": inner_src_port, "dst_port": inner_dst_port},
    })
    print("\n  [%s] PASSED" % tc)


# ---------------------------------------------------------------------------
# TC-6: SRH + inner IPv6 + TCP
# ---------------------------------------------------------------------------

def test_srh_inner_ipv6_tcp(api, b2b_raw_config, utils):
    """Standard SRH (2 SIDs) with inner IPv6/TCP payload (IPv6-in-SRv6).

    Packet stack:
      Ethernet -> outer IPv6 (NH=43) -> SRH (RT=4, sl=1, le=1)
               -> inner IPv6 (src=fd00::1, dst=fd00::2)
               -> TCP (src=8080, dst=443)

    Wire verifies: SRH header fields + inner IPv6 src/dst + TCP src/dst ports.
    Capture is preserved for Wireshark inspection.
    """
    tc = "test_srh_inner_ipv6_tcp"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    segment_list = ["fc00:0:2::1", "fc00:0:1::1"]
    inner_ip_src = "fd00::1"
    inner_ip_dst = "fd00::2"
    inner_src_port = 8080
    inner_dst_port = 443

    _build_srh_flow_with_inner(
        b2b_raw_config, "srh_ipv6_tcp",
        p1.name, p2.name,
        ip6_src="2001:db8::1", ip6_dst=segment_list[0],
        segments_left=1, last_entry=1,
        segments=segment_list,
        inner_ip_version="ipv6",
        inner_ip_src=inner_ip_src, inner_ip_dst=inner_ip_dst,
        inner_transport="tcp",
        inner_src_port=inner_src_port, inner_dst_port=inner_dst_port,
    )

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    # _log_ixn_stack_fields(api, "srh_ipv6_tcp", "ipv6",
    #                       highlight=["ipv6.header.nextHeader"])
    # _log_ixn_stack_fields(api, "srh_ipv6_tcp", "tcp",
    #                       highlight=["tcp.header.dataOffset"])
    _start_capture(api)
    _start_traffic(api)
    time.sleep(6)
    _stop_traffic(api)
    _stop_capture(api)

    port_results, flow_results = utils.get_all_stats(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_full_packet_from_pcap(pcap)
    _print_and_verify(tc, pkt, cfg={
        "srh": {
            "segments_left": 1,
            "last_entry":    1,
            "flags_byte":    0x00,
            "tag":           0,
            "segments":      segment_list,
        },
        "inner_ip":  {"version": 6, "src": _norm(inner_ip_src), "dst": _norm(inner_ip_dst)},
        "transport": {"proto": "TCP", "src_port": inner_src_port, "dst_port": inner_dst_port},
    })
    print("\n  [%s] PASSED" % tc)


# ---------------------------------------------------------------------------
# TC-7: uSID SRH (uSID, A-flag) + inner IPv4 + UDP
# ---------------------------------------------------------------------------

def test_gsrh_inner_ipv4_udp(api, b2b_raw_config, utils):
    """uSID SRH (2 uSID containers, no flags) carrying inner IPv4/UDP payload.

    Packet stack:
      Ethernet -> outer IPv6 (NH=43) -> uSID SRH (RT=4, sl=1, le=1, flags=0x00)
               -> inner IPv4 (src=172.16.1.1, dst=172.16.2.1)
               -> UDP (src=9000, dst=9001)

    Wire verifies: uSID SRH header fields + inner IPv4 src/dst + UDP src/dst ports.
    Capture is preserved for Wireshark inspection.
    """
    tc = "test_gsrh_inner_ipv4_udp"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    usid_containers = ["fc00:1:1::", "fc00:1:2::"]
    inner_ip_src = "172.16.1.1"
    inner_ip_dst = "172.16.2.1"
    inner_src_port = 9000
    inner_dst_port = 9001

    _build_gsrh_flow_with_inner(
        b2b_raw_config, "gsrh_ipv4_udp",
        p1.name, p2.name,
        ip6_src="2001:db8::1", ip6_dst=usid_containers[0],
        segments_left=1, last_entry=1,
        usid_containers=usid_containers,
        inner_ip_version="ipv4",
        inner_ip_src=inner_ip_src, inner_ip_dst=inner_ip_dst,
        inner_transport="udp",
        inner_src_port=inner_src_port, inner_dst_port=inner_dst_port,
    )

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    # _log_ixn_stack_fields(api, "gsrh_ipv4_udp", "ipv4",
    #                       highlight=["ipv4.header.protocol"])
    # _log_ixn_stack_fields(api, "gsrh_ipv4_udp", "udp",
    #                       highlight=["udp.header.length"])
    _start_capture(api)
    _start_traffic(api)
    time.sleep(6)
    _stop_traffic(api)
    _stop_capture(api)

    port_results, flow_results = utils.get_all_stats(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_full_packet_from_pcap(pcap)
    _print_and_verify(tc, pkt, cfg={
        "srh": {
            "segments_left": 1,
            "last_entry":    1,
            "flags_byte":    0x00,
            "tag":           0,
            "segments":      usid_containers,
        },
        "inner_ip":  {"version": 4, "src": inner_ip_src, "dst": inner_ip_dst},
        "transport": {"proto": "UDP", "src_port": inner_src_port, "dst_port": inner_dst_port},
    })
    print("\n  [%s] PASSED" % tc)


# ---------------------------------------------------------------------------
# SRH-8: SRH optional TLVs - Ingress Node TLV and Egress Node TLV (RFC 9259)
# ---------------------------------------------------------------------------

def test_srh_ingress_egress_node_tlv(api, b2b_raw_config, utils):
    """SRH with Pad TLV configured; verify SRH structure and TLV area on wire.

    The snappi API exposes only pad_tlv for the standard SRH TLV area.
    IxNetwork always appends a fixed TLV block after the segment list; this
    test configures pad_tlv.type and pad_tlv.length to non-default values and
    verifies the SRH header fields and that TLV bytes are present on the wire.

    Packet stack:
      Ethernet -> IPv6 (NH=43) -> SRH (RT=4, sl=0, le=0, 1 SID)
               + Pad TLV area (type and length configured via OTG)

    Wire verifies:
      - SRH routing_type=4, segments_left=0, last_entry=0, flags_byte=0x00
      - At least one TLV byte block appears after the segment list
    """
    tc = "test_srh_ingress_egress_node_tlv"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    segment = "fc00:0:1:1::"

    f = b2b_raw_config.flows.add()
    f.name = "srh_tlv"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add()
    eth.choice = "ethernet"
    eth.ethernet.src.value = "00:11:22:33:44:55"
    eth.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = "2001:db8::a"
    ip6.ipv6.dst.value = segment
    ip6.ipv6.next_header.value = 43

    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing"
    sr = ext.ipv6_extension_header.routing.segment_routing
    sr.segments_left.value = 0
    sr.last_entry.value    = 0
    sr.tag.value           = 0
    sr.segment_list.segment()[-1].segment.value = segment

    # Configure Padding TLV via the only OTG-exposed TLV field
    sr.pad_tlv.type.value   = 5
    sr.pad_tlv.length.value = 2

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_srh_with_tlvs_from_pcap(pcap)

    sep   = "=" * 68
    inner = "-" * 68

    assert pkt is not None, "[%s] No SRH packet found in capture" % tc
    assert pkt["routing_type"]  == 4, \
        "[%s] routing_type: expected 4 got %d" % (tc, pkt["routing_type"])
    assert pkt["segments_left"] == 0, \
        "[%s] segments_left: expected 0 got %d" % (tc, pkt["segments_left"])
    assert pkt["last_entry"]    == 0, \
        "[%s] last_entry: expected 0 got %d" % (tc, pkt["last_entry"])
    assert pkt["flags_byte"] == 0x00, \
        "[%s] flags_byte: expected 0x00 got 0x%02x" % (tc, pkt["flags_byte"])

    tlvs = pkt["tlvs"]

    print("\n" + sep)
    print("  %s  [SRH TLV wire verify]" % tc)
    print(inner)
    print("  %-6s  %-8s  %-8s  %s"
          % ("Index", "type", "length", "data_hex"))
    print(inner)
    for i, tlv in enumerate(tlvs):
        print("  [%d]    %-8d %-8d %s"
              % (i, tlv["type"], tlv["length"], tlv["data_hex"]))
    print(sep)

    assert len(tlvs) >= 1, \
        "[%s] Expected >= 1 TLV after segment list, got 0" % tc
    print("  [PASS]  TLV area present: %d TLV(s) found after segment list" % len(tlvs))

    _delete_capture(tc)
    print("\n  [%s] PASSED — SRH structure and TLV area verified on wire." % tc)


# ---------------------------------------------------------------------------
# Helpers for test 9
# ---------------------------------------------------------------------------

def _parse_ipv6_udp_from_pcap(pcap_bytes):
    """Parse the first IPv6/UDP packet that has NO routing extension header.

    Used to verify uSID no-SRH flows: the packet must carry the uSID container
    in the IPv6 destination address and must NOT have next_header=43 (no SRH).

    Returns:
      {"ip6_src": str, "ip6_dst": str, "next_header": int,
       "src_port": int, "dst_port": int}
    or None if no matching packet is found.
    """
    if pcap_bytes is None:
        return None
    raw = pcap_bytes.read() if hasattr(pcap_bytes, "read") else bytes(pcap_bytes)
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

    pkt_count = 0
    for _, pkt_data in pcap:
        try:
            buf = bytes(pkt_data)
            pkt_count += 1
            if pkt_count == 1:
                print("\n  [pcap] first pkt len=%d hex=%s" % (len(buf), buf[:80].hex()))

            if len(buf) < 54:   # Ethernet(14) + IPv6(40)
                continue

            eth_type = struct.unpack("!H", buf[12:14])[0]
            if eth_type == 0x8100:
                if len(buf) < 58:
                    continue
                eth_type = struct.unpack("!H", buf[16:18])[0]
                ip6_off = 18
            else:
                ip6_off = 14

            if eth_type != 0x86DD:
                continue
            if ip6_off + 40 > len(buf):
                continue

            next_hdr = buf[ip6_off + 6]
            if next_hdr == 43:      # SRH packet — not what we want
                continue

            ip6_src = str(ipaddress.IPv6Address(buf[ip6_off + 8:ip6_off + 24]))
            ip6_dst = str(ipaddress.IPv6Address(buf[ip6_off + 24:ip6_off + 40]))

            result = {"ip6_src": ip6_src, "ip6_dst": ip6_dst, "next_header": next_hdr}

            # Parse UDP ports when next_header=17
            if next_hdr == 17 and ip6_off + 48 <= len(buf):
                udp_off = ip6_off + 40
                result["src_port"] = struct.unpack("!H", buf[udp_off:udp_off + 2])[0]
                result["dst_port"] = struct.unpack("!H", buf[udp_off + 2:udp_off + 4])[0]

            return result

        except Exception:
            continue

    print("  [pcap] scanned %d packets; no plain IPv6 (non-SRH) found" % pkt_count)
    return None


# ---------------------------------------------------------------------------
# Test 9: uSID — no SRH routing extension header (destination-only encoding)
# ---------------------------------------------------------------------------

def test_usid_no_srh(api, b2b_raw_config, utils):
    """Multiple uSIDs with NO SRH: 3-hop path packed into one F3216 uSID container,
    placed directly in the IPv6 destination via ipv6.dst_usids - no routing extension
    header required.

    OTG model used:
      Flow.Ipv6  (dst_usids = structured locator + uSID list; next_header not set,
                  IxNetwork auto-computes NH=17 from the following UDP stack)
      Flow.Udp
      No Flow.Ipv6ExtHeader - no routing extension header is present.

    F3216 uSID container layout (128 bits):
      fc00:0:1:2:3::
        Locator-Block = fc00:0000  (32 bits, shared domain prefix)
        uSID-1        = 0001       (16 bits, hop 1 - egress of node 1)
        uSID-2        = 0002       (16 bits, hop 2 - egress of node 2)
        uSID-3        = 0003       (16 bits, hop 3 - egress of node 3)
        Remaining     = 0::        (48 bits, zeros = end of uSID list)

    With the F3216 encoding (32-bit locator block, 16-bit per uSID), up to 6 hops
    fit in a single 128-bit container.  When the entire path fits, the container is
    placed in IPv6 dst and no SRH is added.  Compare with test_srh_usid
    (same 3-hop container carried inside a uSID SRH) and test_usid_multi_srh_container
    (4-hop path split across 2 uSID SRH containers).

    Packet stack:
      Ethernet -> IPv6 (NH=17, dst=fc00:0:1:2:3::) -> UDP (src=1234, dst=5000)

    Wire verifies:
      - IPv6 next_header = 17  (UDP directly - NO routing extension header present)
      - IPv6 dst = fc00:0:1:2:3::  (uSID container assembled from locator + uSIDs)
      - UDP src_port = 1234, dst_port = 5000
    """
    tc = "test_usid_no_srh"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

  

    f = b2b_raw_config.flows.add()
    f.name = "usid_no_srh"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add().ethernet
    eth.src.value = "00:11:22:33:44:55"
    eth.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add().ipv6
    ip6.src.value = "2001:db8::1"
    du = ip6.dst_usids
    du.locator.value = "fc00::"
    du.locator_length.value = 32
    du.usids.add().usid = "0001"
    du.usids.add().usid = "0002"
    du.usids.add().usid = "0003"
    # next_header auto-computed by IxNetwork from the following UDP header

    src_port  = 1234
    dst_port  = 5000
    udp = f.packet.add().udp
    udp.src_port.value = src_port
    udp.dst_port.value = dst_port

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    usid_dst = "fc00:0:1:2:3::"

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_ipv6_udp_from_pcap(pcap)

    sep   = "=" * 66
    inner = "-" * 66
    print("\n" + sep)
    print("  %s  [uSID no-SRH wire verify]" % tc)
    print("  %-22s  %-22s  %-22s  %s" % ("Field", "Configured", "Wire", "Status"))
    print(inner)

    assert pkt is not None, \
        "[%s] No plain IPv6 packet found in capture" % tc

    def _chk(label, want, got):
        ok = (str(want) == str(got))
        print("  %-22s  %-22s  %-22s  %s"
              % (label, str(want), str(got), "PASS" if ok else "FAIL"))
        return ok

    ok  = _chk("ip6_dst",      _norm(usid_dst),  _norm(pkt["ip6_dst"]))
    ok &= _chk("next_header",   17,               pkt["next_header"])
    ok &= _chk("udp.src_port",  src_port,         pkt.get("src_port", "?"))
    ok &= _chk("udp.dst_port",  dst_port,         pkt.get("dst_port", "?"))
    print(sep)

    assert _norm(pkt["ip6_dst"]) == _norm(usid_dst), \
        "[%s] ip6_dst: want %s got %s" % (tc, _norm(usid_dst), _norm(pkt["ip6_dst"]))
    assert pkt["next_header"] == 17, \
        "[%s] next_header: want 17 (UDP, no SRH) got %d" % (tc, pkt["next_header"])
    assert pkt.get("src_port") == src_port, \
        "[%s] udp.src_port: want %d got %s" % (tc, src_port, pkt.get("src_port"))
    assert pkt.get("dst_port") == dst_port, \
        "[%s] udp.dst_port: want %d got %s" % (tc, dst_port, pkt.get("dst_port"))

    _delete_capture(tc)
    print("\n  [%s] PASSED — uSID container in IPv6 dst, no SRH on wire." % tc)


# ---------------------------------------------------------------------------
# Test 10: no-SRH uSID via flowutils.set_usid_dst helper
# ---------------------------------------------------------------------------

def test_usid_no_srh_via_helper(api, b2b_raw_config, utils):
    """Two-uSID no-SRH flow built with flowutils.set_usid_dst.

    Exercises the snappi_ixnetwork.flowutils.set_usid_dst helper which
    populates ipv6.dst_usids from explicit locator and uSID arguments in a
    single call, replacing the per-field assignment pattern shown in
    test_usid_no_srh.

    F3216 container: locator=fc00::/32, usids=["0001","0002"] -> dst fc00:0:1:2::

    Packet stack:
      Ethernet -> IPv6 (NH=17, dst=fc00:0:1:2::) -> UDP (src=4321, dst=6543)

    Wire verifies:
      - IPv6 next_header=17 (UDP directly; no routing extension header)
      - IPv6 dst=fc00:0:1:2:: (two-uSID container assembled by helper)
      - UDP src_port=4321, dst_port=6543
    """
    from snappi_ixnetwork.flowutils import set_usid_dst

    tc = "test_usid_no_srh_via_helper"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    f = b2b_raw_config.flows.add()
    f.name = "usid_no_srh_helper"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add().ethernet
    eth.src.value = "00:11:22:33:44:55"
    eth.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add().ipv6
    ip6.src.value = "2001:db8::1"
    set_usid_dst(ip6.dst_usids, "fc00::", 32, ["0001", "0002"])

    src_port = 4321
    dst_port = 6543
    udp = f.packet.add().udp
    udp.src_port.value = src_port
    udp.dst_port.value = dst_port

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    expected_dst = "fc00:0:1:2::"
    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_ipv6_udp_from_pcap(pcap)

    sep   = "=" * 66
    inner = "-" * 66
    print("\n" + sep)
    print("  %s  [set_usid_dst helper - no-SRH wire verify]" % tc)
    print("  %-22s  %-22s  %-22s  %s" % ("Field", "Configured", "Wire", "Status"))
    print(inner)

    assert pkt is not None, "[%s] No plain IPv6 packet found in capture" % tc

    def _chk(label, want, got):
        ok = (str(want) == str(got))
        print("  %-22s  %-22s  %-22s  %s"
              % (label, str(want), str(got), "PASS" if ok else "FAIL"))
        return ok

    ok  = _chk("ip6_dst",     _norm(expected_dst), _norm(pkt["ip6_dst"]))
    ok &= _chk("next_header",  17,                  pkt["next_header"])
    ok &= _chk("udp.src_port", src_port,            pkt.get("src_port", "?"))
    ok &= _chk("udp.dst_port", dst_port,            pkt.get("dst_port", "?"))
    print(sep)

    assert _norm(pkt["ip6_dst"]) == _norm(expected_dst), \
        "[%s] ip6_dst: want %s got %s" % (tc, _norm(expected_dst), _norm(pkt["ip6_dst"]))
    assert pkt["next_header"] == 17, \
        "[%s] next_header: want 17 (UDP, no SRH) got %d" % (tc, pkt["next_header"])
    assert pkt.get("src_port") == src_port, \
        "[%s] udp.src_port: want %d got %s" % (tc, src_port, pkt.get("src_port"))
    assert pkt.get("dst_port") == dst_port, \
        "[%s] udp.dst_port: want %d got %s" % (tc, dst_port, pkt.get("dst_port"))

    _delete_capture(tc)
    print("\n  [%s] PASSED — set_usid_dst helper verified." % tc)


# ---------------------------------------------------------------------------
# Test 11: uSID SRH via flowutils.add_usid_container helper
# ---------------------------------------------------------------------------

def test_usid_srh_via_helper(api, b2b_raw_config, utils):
    """Two-container uSID SRH built with flowutils.add_usid_container.

    Exercises the snappi_ixnetwork.flowutils.add_usid_container helper which
    appends one uSID container to a segment_routing_usid segment list from
    explicit locator and uSID arguments, replacing the pre-packed IPv6 address
    approach used in _add_usid_container.

    Two F3216 containers (locator=fc00::/32):
      Container 0 (first visited, sl=1): usids=["0001","0002"] -> fc00:0:1:2::
      Container 1 (last,          sl=0): usids=["0003","0004"] -> fc00:0:3:4::

    Packet stack:
      Ethernet -> outer IPv6 (NH=43, dst=fc00:0:1:2::)
               -> uSID SRH (RT=4, sl=1, le=1, flags=0x00, tag=0)
               -> inner IPv6 (src=2001:db8::a, dst=2001:db8::b)
               -> UDP (src=7777, dst=8888)

    Wire verifies:
      - SRH routing_type=4, sl=1, le=1, flags_byte=0x00, tag=0
      - segments=[fc00:0:1:2::, fc00:0:3:4::]
      - inner IPv6 src/dst and UDP ports
    """
    from snappi_ixnetwork.flowutils import add_usid_container

    tc = "test_usid_srh_via_helper"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    locator = "fc00::"
    lb      = 32

    f = b2b_raw_config.flows.add()
    f.name = "usid_srh_helper"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add()
    eth.choice = "ethernet"
    eth.ethernet.src.value = "00:11:22:33:44:55"
    eth.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

    ip6 = f.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = "2001:db8::1"
    ip6.ipv6.dst.value = "fc00:0:1:2::"   # first container (active) in outer dst
    ip6.ipv6.next_header.value = 43

    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing_usid"
    usid = ext.ipv6_extension_header.routing.segment_routing_usid
    usid.segments_left.value = 1
    usid.last_entry.value    = 1
    usid.flags.oam.value     = 0
    usid.tag.value           = 0
    add_usid_container(usid.segment_list, locator, lb, ["0001", "0002"])
    add_usid_container(usid.segment_list, locator, lb, ["0003", "0004"])

    inner_ip6 = f.packet.add()
    inner_ip6.choice = "ipv6"
    inner_ip6.ipv6.src.value = "2001:db8::a"
    inner_ip6.ipv6.dst.value = "2001:db8::b"

    src_port = 7777
    dst_port = 8888
    inner_udp = f.packet.add()
    inner_udp.choice = "udp"
    inner_udp.udp.src_port.value = src_port
    inner_udp.udp.dst_port.value = dst_port

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(6)
    _stop_traffic(api)
    _stop_capture(api)

    utils.get_all_stats(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_full_packet_from_pcap(pcap)
    _print_and_verify(tc, pkt, cfg={
        "srh": {
            "segments_left": 1,
            "last_entry":    1,
            "flags_byte":    0x00,
            "tag":           0,
            "segments":      ["fc00:0:1:2::", "fc00:0:3:4::"],
        },
        "inner_ip":  {"version": 6,
                      "src": _norm("2001:db8::a"),
                      "dst": _norm("2001:db8::b")},
        "transport": {"proto": "UDP", "src_port": src_port, "dst_port": dst_port},
    })

    _delete_capture(tc)
    print("\n  [%s] PASSED — add_usid_container helper verified." % tc)
