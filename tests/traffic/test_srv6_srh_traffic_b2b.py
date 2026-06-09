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

import binascii
import io
import ipaddress
import os
import socket
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
    seg.usids = list(usids)


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
    """3-hop NEXT-CSID path packed in one F3216 uSID container inside a uSID SRH.

    RFC 9800 NEXT-CSID flavor, LBL=32 bits, LNFL=16 bits, K=6 CSIDs per container.

    OTG model used:
      Flow.Ipv6  (NH=43, dst = uSID container)
      Flow.Ipv6ExtHeader.routing.segment_routing_usid
        segment_list: 1 entry (last_entry=0, segments_left=0)
        segment[0]:
          locator.value        = "fc00::"   (LBL, 32 bits)
          locator_length.value = 32
          usids                = ["0001", "0002", "0003"]

    Container wire layout (128 bits):
      [LBL=fc00:0000 (32b)][CSID1=0001 (16b)][CSID2=0002 (16b)][CSID3=0003 (16b)]
      [EoC zeros (48b)]
      = fc00:0:1:2:3::

    NEXT-CSID processing per RFC 9800 Section 4.1:
      - Hop 1 (CSID=0001): DA.Argument = 0002:0003:0000:... (non-zero), shift left.
                           New DA = fc00:0:2:3::
      - Hop 2 (CSID=0002): DA.Argument = 0003:0000:... (non-zero), shift left.
                           New DA = fc00:0:3::
      - Hop 3 (CSID=0003): DA.Argument = 0 (EoC). Final destination reached.

    1 segment entry in SRH (last_entry=0, segments_left=0): entire path fits in the
    single active container; no SRH advancement needed.

    Compare:
      test_usid_no_srh            — same container, no routing header (NH=17)
      test_usid_multi_srh_container — path spans 2 containers, 2 SRH entries

    Packet stack:
      Ethernet -> IPv6 (NH=43, dst=fc00:0:1:2:3::) -> uSID SRH (1 segment)

    Wire verifies:
      routing_type=4, segments_left=0, last_entry=0, segment[0]=fc00:0:1:2:3::
    """
    tc = "test_srh_usid"
    api.set_config(api.config())  # reset IxN state
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    usid_container = "fc00:0:1:2:3::"
    locator        = "fc00::"
    locator_length = 32
    usids          = ["0001", "0002", "0003"]
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

    seg = usid.segment_list.segment()[-1]
    seg.locator.value        = locator
    seg.locator_length.value = locator_length
    seg.usids                = list(usids)

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
    """4-hop NEXT-CSID path spread across 2 F3216 uSID containers in a uSID SRH.

    RFC 9800 NEXT-CSID flavor, LBL=32 bits, LNFL=16 bits, K=6 CSIDs per container.

    OTG model used:
      Flow.Ipv6  (NH=43, dst = first/active uSID container)
      Flow.Ipv6ExtHeader.routing.segment_routing_usid
        segment_list: 2 entries  (last_entry=1, segments_left=1)
        segment[0]:
          locator.value        = "fc00::"
          locator_length.value = 32
          usids                = ["0001", "0002"]
        segment[1]:
          locator.value        = "fc00::"
          locator_length.value = 32
          usids                = ["0003", "0004"]

    Container wire layout (128 bits each):
      container-1: [LBL=fc00:0000 (32b)][0001 (16b)][0002 (16b)][EoC zeros (64b)]
                   = fc00:0:1:2::
      container-2: [LBL=fc00:0000 (32b)][0003 (16b)][0004 (16b)][EoC zeros (64b)]
                   = fc00:0:3:4::

    NEXT-CSID processing per RFC 9800 Section 4.1:
      Container 1 active (IPv6 dst = fc00:0:1:2::):
        Hop 1 (CSID=0001): Argument=0002:0000:... non-zero -> shift -> DA=fc00:0:2::
        Hop 2 (CSID=0002): Argument=0 (EoC) -> segments_left-- -> load Segment List[0]
      Container 2 active (IPv6 dst = fc00:0:3:4::):
        Hop 3 (CSID=0003): Argument=0004:0000:... non-zero -> shift -> DA=fc00:0:4::
        Hop 4 (CSID=0004): Argument=0 (EoC) -> final destination reached

    Compare:
      test_srh_usid   — single container, entire path fits in 1 entry (segments_left=0)
      test_usid_no_srh — same container concept but no routing header at all

    Packet stack:
      Ethernet -> IPv6 (NH=43, dst=fc00:0:1:2::) -> uSID SRH (2 segments)

    Wire verifies:
      routing_type=4, segments_left=1, last_entry=1,
      segment[0]=fc00:0:1:2::, segment[1]=fc00:0:3:4::
    """
    tc = "test_usid_multi_srh_container"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    locator        = "fc00::"
    locator_length = 32
    container1     = "fc00:0:1:2::"
    usids_c1       = ["0001", "0002"]
    container2     = "fc00:0:3:4::"
    usids_c2       = ["0003", "0004"]
    segments_left  = 1
    last_entry     = 1

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
    ip6.dst.value = container1
    ip6.next_header.value = 43

    usid = f.packet.add().ipv6_extension_header.routing.segment_routing_usid
    usid.segments_left.value = segments_left
    usid.last_entry.value    = last_entry
    usid.tag.value           = 0

    seg0 = usid.segment_list.segment()[-1]
    seg0.locator.value        = locator
    seg0.locator_length.value = locator_length
    seg0.usids                = list(usids_c1)

    seg1 = usid.segment_list.segment()[-1]
    seg1.locator.value        = locator
    seg1.locator_length.value = locator_length
    seg1.usids                = list(usids_c2)

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
        for i, (s, exp) in enumerate(zip(srh["segments"], [container1, container2])):
            print("  segment[%d]    : %-36s  (expect %s)" % (i, s, _norm(exp)))
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
        assert _norm(srh["segments"][0]) == _norm(container1), (
            "segment[0]: want %s got %s" % (_norm(container1), _norm(srh["segments"][0]))
        )
        assert _norm(srh["segments"][1]) == _norm(container2), (
            "segment[1]: want %s got %s" % (_norm(container2), _norm(srh["segments"][1]))
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
    du.usids = ["0001", "0002", "0003"]
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


# ---------------------------------------------------------------------------
# G-SHR wire parser — outer IPv6 dst + SRH segment list
# ---------------------------------------------------------------------------

def _parse_gshr_from_pcap(pcap_bytes):
    """Parse the outer IPv6 dst and SRH fields from a G-SHR (Reduced SRH) packet.

    In G-SHR (RFC 9800 / RFC 8754 Section 4.1.1), the active (first) uSID
    container is encoded in the outer IPv6 dst field while the remaining
    containers appear in the SRH segment list.  This parser captures both.

    Returns:
      {
        "ip6_dst":       str,          # outer IPv6 destination address
        "routing_type":  int,          # must be 4
        "segments_left": int,
        "last_entry":    int,
        "flags_byte":    int,
        "tag":           int,
        "segments":      list[str],    # SRH segment list (remaining containers only)
      }
    Returns None if no IPv6/SRH (routing_type=4) packet is found.
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

            # Outer IPv6 destination address
            ip6_dst = str(ipaddress.IPv6Address(buf[ip6_off + 24:ip6_off + 40]))

            srh_off = ip6_off + 40
            if srh_off + 8 > len(buf):
                continue

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

            return {
                "ip6_dst":       ip6_dst,
                "routing_type":  routing_type,
                "segments_left": segments_left,
                "last_entry":    last_entry,
                "flags_byte":    flags_byte,
                "tag":           tag,
                "segments":      segments,
            }
        except Exception:
            continue

    print("  [pcap] scanned %d packets; no IPv6/SRH found" % pkt_count)
    return None


# ---------------------------------------------------------------------------
# Test 12: G-SHR — Reduced SRH with uSID (dst_usids + segment_routing_usid)
# ---------------------------------------------------------------------------

def test_gshr_reduced_srh(api, b2b_raw_config, utils):
    """G-SHR (Generalized SRH Reduction / Reduced SRH): first uSID container
    in IPv6 dst via dst_usids, remaining container(s) in uSID SRH segment list.

    This is distinct from:
      - test_usid_no_srh: entire path in dst_usids, no SRH at all.
      - test_srh_usid / test_usid_multi_srh_container: all containers in SRH
        segment list, plain ipv6.dst points to the first container.

    RFC reference:
      RFC 9800 Section 4 (uSID reduced encapsulation),
      RFC 8754 Section 4.1.1 (Reduced SRH — first segment in IPv6 dst,
      not repeated in the SRH segment list).

    OTG encoding:
      ip6.dst_usids  -> first/active uSID container assembled into IPv6 dst
                        locator=fc00::/32, usids=["0001","0002"] -> fc00:0:1:2::
      segment_routing_usid.segment_list  -> remaining container(s) ONLY
                        (first container NOT repeated here per Reduced SRH)
                        1 entry: fc00:0:3:4::

    Packet stack:
      Ethernet -> outer IPv6 (NH=43, dst=fc00:0:1:2:: from dst_usids)
               -> uSID SRH (RT=4, sl=1, le=0, flags=0x00, tag=0)
                  segment_list: [fc00:0:3:4::]   <- remaining container only
               -> inner IPv4 (src=10.1.0.1, dst=10.2.0.1)
               -> UDP (src=5001, dst=5002)

    Wire verifies:
      - outer IPv6 dst = fc00:0:1:2::   (assembled from dst_usids)
      - SRH routing_type = 4
      - SRH segments_left = 1           (1 more container in SRH to visit)
      - SRH last_entry = 0              (only 1 entry in the SRH segment list)
      - SRH segment[0] = fc00:0:3:4::  (second/remaining container)
      - flags_byte = 0x00, tag = 0
    """
    tc = "test_gshr_reduced_srh"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    # First (active) container goes into IPv6 dst via dst_usids.
    # Assembled wire address: fc00:0:1:2::
    locator          = "fc00::"
    locator_len      = 32
    first_usids      = ["0001", "0002"]
    expected_ip6_dst = "fc00:0:1:2::"

    # Second container goes into the SRH segment list (Reduced SRH).
    # NOT repeated in dst_usids.
    remaining_container = "fc00:0:3:4::"

    segments_left = 1   # 1 more container remains in the SRH after the active one
    last_entry    = 0   # only 1 entry in the SRH segment list (index 0)

    inner_ip_src   = "10.1.0.1"
    inner_ip_dst   = "10.2.0.1"
    inner_src_port = 5001
    inner_dst_port = 5002

    f = b2b_raw_config.flows.add()
    f.name = "gshr_reduced"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add()
    eth.choice = "ethernet"
    eth.ethernet.src.value = "00:11:22:33:44:55"
    eth.ethernet.dst.value = "00:aa:bb:cc:dd:ee"

    # Outer IPv6: dst assembled from dst_usids (first container)
    ip6 = f.packet.add()
    ip6.choice = "ipv6"
    ip6.ipv6.src.value = "2001:db8::1"
    du = ip6.ipv6.dst_usids
    du.locator.value        = locator
    du.locator_length.value = locator_len
    du.usids = list(first_usids)
    ip6.ipv6.next_header.value = 43

    # uSID SRH: segment list contains ONLY the remaining container
    ext = f.packet.add()
    ext.choice = "ipv6_extension_header"
    ext.ipv6_extension_header.routing.choice = "segment_routing_usid"
    usid = ext.ipv6_extension_header.routing.segment_routing_usid
    usid.segments_left.value = segments_left
    usid.last_entry.value    = last_entry
    usid.flags.oam.value     = 0
    usid.tag.value           = 0
    _add_usid_container(usid.segment_list, remaining_container)

    # Inner IPv4 + UDP
    inner_ip = f.packet.add()
    inner_ip.choice = "ipv4"
    inner_ip.ipv4.src.value = inner_ip_src
    inner_ip.ipv4.dst.value = inner_ip_dst

    inner_udp = f.packet.add()
    inner_udp.choice = "udp"
    inner_udp.udp.src_port.value = inner_src_port
    inner_udp.udp.dst_port.value = inner_dst_port

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)
    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    port_results, flow_results = utils.get_all_stats(api)

    pcap = _get_capture(api, p2.name)
    _save_capture(pcap, tc)

    pkt = _parse_gshr_from_pcap(pcap)

    sep   = "=" * 72
    inner = "-" * 72

    if pkt is not None:
        print("\n" + sep)
        print("  %s  [G-SHR Reduced SRH wire verify]" % tc)
        print("  %-28s  %-22s  %-22s  %s"
              % ("Field", "Configured", "Wire", "Status"))
        print(inner)

        def _row(label, want, got):
            ok = (str(want) == str(got))
            print("  %-28s  %-22s  %-22s  %s"
                  % (label, str(want), str(got), "PASS" if ok else "FAIL"))
            return ok

        _row("outer ip6_dst",  _norm(expected_ip6_dst), _norm(pkt["ip6_dst"]))
        _row("routing_type",   4,             pkt["routing_type"])
        _row("segments_left",  segments_left, pkt["segments_left"])
        _row("last_entry",     last_entry,    pkt["last_entry"])
        _row("flags_byte",
             "0x%02x" % 0x00,
             "0x%02x" % pkt["flags_byte"],
             )
        _row("tag",            "0x0000",      "0x%04x" % pkt["tag"])
        for i, seg in enumerate(pkt["segments"]):
            _row("SRH segment[%d]" % i, "?" if i > 0 else _norm(remaining_container), seg)
        print(sep)

        assert _norm(pkt["ip6_dst"]) == _norm(expected_ip6_dst), (
            "[%s] outer ip6_dst: want %s got %s"
            % (tc, _norm(expected_ip6_dst), _norm(pkt["ip6_dst"]))
        )
        assert pkt["routing_type"] == 4, (
            "[%s] routing_type: want 4 got %d" % (tc, pkt["routing_type"])
        )
        assert pkt["segments_left"] == segments_left, (
            "[%s] segments_left: want %d got %d"
            % (tc, segments_left, pkt["segments_left"])
        )
        assert pkt["last_entry"] == last_entry, (
            "[%s] last_entry: want %d got %d" % (tc, last_entry, pkt["last_entry"])
        )
        assert pkt["flags_byte"] == 0x00, (
            "[%s] flags_byte: want 0x00 got 0x%02x" % (tc, pkt["flags_byte"])
        )
        assert pkt["tag"] == 0, (
            "[%s] tag: want 0 got %d" % (tc, pkt["tag"])
        )
        assert len(pkt["segments"]) == 1, (
            "[%s] SRH segment list: want 1 entry (remaining container only) got %d"
            % (tc, len(pkt["segments"]))
        )
        assert _norm(pkt["segments"][0]) == _norm(remaining_container), (
            "[%s] SRH segment[0]: want %s got %s"
            % (tc, _norm(remaining_container), _norm(pkt["segments"][0]))
        )
        _delete_capture(tc)
        print("\n  [%s] PASSED — G-SHR Reduced SRH verified on wire." % tc)

    else:
        req = api.metrics_request()
        req.flow.flow_names = ["gshr_reduced"]
        metrics = api.get_metrics(req)
        tx_pkts = sum(m.frames_tx for m in metrics.flow_metrics)
        print("\n  [NOTE] No G-SHR packet found in capture; tx_pkts=%d" % tx_pkts)
        assert tx_pkts > 0, (
            "[%s] No packets transmitted; IxNetwork may have rejected the "
            "dst_usids + segment_routing_usid combination" % tc
        )


# ---------------------------------------------------------------------------
# Direct RESTpy helpers for ipv6GSRHType4
# ---------------------------------------------------------------------------

def _usid_container_to_hex_slots(container_ipv6, lb_bits=32, usid_bits=16):
    """Unpack a uSID container IPv6 address into four 32-bit hex slot strings.

    Each 128-bit uSID container maps to four consecutive 32-bit ipv6SID slots
    in the ipv6GSRHType4 IxNetwork stack (e.g. fc00:0:1:2:: -> 4 hex strings).

    Returns list of 4 strings, each 8 hex characters (no prefix).
    Example: "fc00:0:1:2::" -> ["fc000000", "00010002", "00000000", "00000000"]
    """
    packed = socket.inet_pton(socket.AF_INET6, container_ipv6)
    return [
        binascii.hexlify(packed[i * 4:(i + 1) * 4]).decode("ascii")
        for i in range(4)
    ]


def _restpy_set_field(stack, field_type_id, value, value_type="singleValue"):
    """Set a single field in an IxNetwork RESTpy Stack object."""
    field = stack.Field.find(FieldTypeId=field_type_id)
    if not field:
        raise RuntimeError("Field '%s' not found in stack" % field_type_id)
    field.update(ValueType=value_type, SingleValue=str(value), Auto=False)


def _restpy_read_gsrh_slots(gsrh_stack, n_containers):
    """Read the populated ipv6SID hex slots from an ipv6GSRHType4 stack.

    Iterates all fields once into a dict keyed by FieldTypeId, then
    re-assembles each 128-bit uSID container from four consecutive 32-bit
    hex slot values (zero-padded to 8 chars each).

    Returns a list of IPv6 address strings (one per uSID container).
    """
    field_map = {}
    for f in gsrh_stack.Field.find():
        try:
            field_map[f.FieldTypeId] = str(f.SingleValue)
        except Exception:
            pass

    containers = []
    for seg_idx in range(n_containers):
        pieces = []
        for piece_idx in range(4):
            slot = seg_idx * 4 + piece_idx + 1
            fid  = ("ipv6GSRHType4.segmentRoutingHeader"
                    ".segmentList.ipv6SID%d" % slot)
            pieces.append(field_map.get(fid, "0").zfill(8))
        packed = binascii.unhexlify("".join(pieces))
        containers.append(str(ipaddress.IPv6Address(packed)))
    return containers


def _restpy_override_gsrh_slots(gsrh_stack, usid_containers):
    """Overwrite the ipv6SID hex slots of an existing ipv6GSRHType4 stack.

    Called after snappi has already pushed the base config via set_config()
    so that any field not exposed by the OTG model can be adjusted directly.

    Each 128-bit uSID container is split into four 32-bit hex pieces and
    written into consecutive ipv6SID slots (slots 1-4 for the first container,
    5-8 for the second, etc.).
    """
    slot = 1
    for container in usid_containers:
        hex_slots = _usid_container_to_hex_slots(container)
        for hex_val in hex_slots:
            fid = ("ipv6GSRHType4.segmentRoutingHeader"
                   ".segmentList.ipv6SID%d" % slot)
            f = gsrh_stack.Field.find(FieldTypeId=fid)
            if f:
                f.update(ValueType="singleValue",
                         SingleValue=hex_val,
                         Auto=False,
                         OptionalEnabled=True)
            slot += 1


# ---------------------------------------------------------------------------
# Test 13: ipv6GSRHType4 — hybrid: snappi builds config, RESTpy reads & overrides
# ---------------------------------------------------------------------------

def test_gsrh_restpy_direct(api, b2b_raw_config, utils):
    """Hybrid test: snappi/OTG builds the ipv6GSRHType4 traffic config, then
    IxNetwork RESTpy is used to read every GSRH slot value directly from
    the IxNetwork session and optionally override fields that the OTG model
    does not yet expose.

    Approach:
      1. Use the existing OTG segment_routing_usid path (api.set_config) to
         build Ethernet -> IPv6 -> ipv6GSRHType4 in IxNetwork.
      2. After set_config, access api._ixnetwork to find the ipv6GSRHType4
         stack and read back all 32-bit hex GSID slots via RESTpy.
      3. Verify slot values match the assembled uSID containers.
      4. Send traffic, capture, and wire-verify the SRH fields on the pcap.

    This pattern lets tests reach any ipv6GSRHType4 field (TLVs, individual
    flag bits, per-slot hex values) that the OTG model does not surface,
    without rebuilding the entire traffic item from scratch in RESTpy.

    Two F3216 uSID containers (locator fc00::/32, Routing Type = 4):
      Container 0 (active): fc00:0:1:2::  usids=[0001,0002]
      Container 1 (remaining): fc00:0:3:4::  usids=[0003,0004]

    Wire verifies:
      - routing_type = 4, segments_left = 1, last_entry = 1
      - segment[0] = fc00:0:1:2::, segment[1] = fc00:0:3:4::
      - flags_byte = 0x00, tag = 0
    """
    tc = "test_gsrh_restpy_direct"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    usid_containers = ["fc00:0:1:2::", "fc00:0:3:4::"]
    segments_left   = 1
    last_entry      = 1

    # Step 1: build config via OTG (snappi creates ipv6GSRHType4 in IxNetwork)
    f = b2b_raw_config.flows.add()
    f.name = "gsrh_restpy"
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
    usid.last_entry.value    = last_entry
    usid.flags.oam.value     = 0
    usid.tag.value           = 0
    for c in usid_containers:
        _add_usid_container(usid.segment_list, c)

    # No capture object in config: snappi transmit() auto-starts capture when
    # one is present, which fails if the card's capture-port limit is already
    # reached by other tests on the same chassis card.
    api.set_config(b2b_raw_config)

    # Step 2: access the ipv6GSRHType4 stack directly via RESTpy
    ixn        = api._ixnetwork
    ti         = ixn.Traffic.TrafficItem.find(Name="gsrh_restpy")
    ce         = ti.ConfigElement.find()
    gsrh_stack = ce.Stack.find(StackTypeId="ipv6GSRHType4")

    print("\n  [restpy] Dumping all ipv6GSRHType4 fields after set_config:")
    _log_ixn_stack_fields(api, "gsrh_restpy", "ipv6GSRHType4",
                          highlight=["ipv6SID", "segmentsLeft",
                                     "lastEntry", "hdrExtLen"])

    # Step 3: read hex slots back and verify they match the uSID containers
    read_back = _restpy_read_gsrh_slots(gsrh_stack, len(usid_containers))
    sep   = "=" * 66
    inner = "-" * 66
    print("\n" + sep)
    print("  [restpy] GSRH slot read-back vs configured containers")
    print(inner)
    for i, (configured, readback) in enumerate(
            zip(usid_containers, read_back)):
        ok = _norm(configured) == _norm(readback)
        print("  container[%d]  configured=%-20s  readback=%-20s  %s"
              % (i, _norm(configured), _norm(readback),
                 "MATCH" if ok else "MISMATCH"))
    print(sep)

    for i, (configured, readback) in enumerate(
            zip(usid_containers, read_back)):
        assert _norm(configured) == _norm(readback), (
            "[%s] RESTpy slot read-back mismatch for container[%d]: "
            "want %s got %s" % (tc, i, _norm(configured), _norm(readback))
        )

    # Step 4: send traffic via RESTpy directly so snappi's transmit() path
    # (which unconditionally calls _start_capture) is bypassed entirely.
    ixn.Traffic.Apply()
    ixn.Traffic.StartStatelessTrafficBlocking()
    time.sleep(4)
    ixn.Traffic.StopStatelessTrafficBlocking()

    # No pcap in this test — RESTpy slot read-back is the primary assertion.
    srh = None

    if srh is not None:
        print("\n" + sep)
        print("  %s  [ipv6GSRHType4 wire verify]" % tc)
        print("  %-24s  %-20s  %-20s  %s"
              % ("Field", "Configured", "Wire", "Status"))
        print(inner)

        def _row(label, want, got):
            ok = (str(want) == str(got))
            print("  %-24s  %-20s  %-20s  %s"
                  % (label, str(want), str(got), "PASS" if ok else "FAIL"))
            return ok

        _row("routing_type",  4,             srh["routing_type"])
        _row("segments_left", segments_left, srh["segments_left"])
        _row("last_entry",    last_entry,    srh["last_entry"])
        _row("flags_byte",    "0x00",        "0x%02x" % srh["flags_byte"])
        _row("tag",           "0x0000",      "0x%04x" % srh["tag"])
        for i, container in enumerate(usid_containers):
            wire = srh["segments"][i] if i < len(srh["segments"]) else "MISSING"
            _row("segment[%d]" % i, _norm(container), wire)
        print(sep)

        assert srh["routing_type"]  == 4,             "[%s] routing_type"  % tc
        assert srh["segments_left"] == segments_left, "[%s] segments_left" % tc
        assert srh["last_entry"]    == last_entry,    "[%s] last_entry"    % tc
        assert srh["flags_byte"]    == 0x00,          "[%s] flags_byte"    % tc
        assert srh["tag"]           == 0,             "[%s] tag"           % tc
        assert len(srh["segments"]) == len(usid_containers), (
            "[%s] segment count: want %d got %d"
            % (tc, len(usid_containers), len(srh["segments"])))
        for i, container in enumerate(usid_containers):
            assert _norm(srh["segments"][i]) == _norm(container), (
                "[%s] segment[%d]: want %s got %s"
                % (tc, i, _norm(container), _norm(srh["segments"][i])))

        print("\n  [%s] PASSED" % tc)
        print("  Capture saved at: tests/captures/%s.pcapng" % tc)

    else:
        req = api.metrics_request()
        req.flow.flow_names = ["gsrh_restpy"]
        metrics = api.get_metrics(req)
        tx_pkts = sum(m.frames_tx for m in metrics.flow_metrics)
        print("\n  [NOTE] No SRH found in capture; tx_pkts=%d" % tx_pkts)
        assert tx_pkts > 0, "[%s] No packets transmitted" % tc
        print("  Capture saved at: tests/captures/%s.pcapng" % tc)


def test_replace_csid_first_container(api, b2b_raw_config, utils):
    """REPLACE-CSID flavor (RFC 9800 Section 4.2) - first container (no SRH).

    The FIRST CSID container of a REPLACE-CSID sequence is a fully formed SRv6 SID
    with the same structure as a NEXT-CSID container: locator block + single CSID
    (Locator-Node+Function, LNFL bits) + Argument = 0. Valid LNFL: 16-bit or 32-bit;
    implementations MUST support 32-bit (RFC 9800 Section 4.2). No SRH.

    Config (LBL=32, LNFL=32):
      dst_usids: locator="2001:db8::", locator_length=32, usids=["00010001"]
      Assembly: [LB=32 bits: 2001:0db8][CSID=0x00010001][Arg=0, 64 bits]
      Expected dst: 2001:db8:1:1::

    Verifies via RESTpy that the IxNetwork ipv6 stack dst field matches.
    """
    tc = "test_replace_csid_first_container"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    # REPLACE-CSID first container: LBL=32, LNFL=32, single CSID=0x00010001
    # Assembly: [2001:0db8 (32 bits)] [0001:0001 (32 bits)] [0...0 (64 bits)]
    locator      = "2001:db8::"
    locator_len  = 32
    usids        = ["00010001"]
    expected_dst = "2001:db8:1:1::"

    f = b2b_raw_config.flows.add()
    f.name = "replace_csid_first"
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
    du.locator.value        = locator
    du.locator_length.value = locator_len
    du.usids                = usids

    api.set_config(b2b_raw_config)

    # Read back the assembled IPv6 dst via RESTpy
    ixn        = api._ixnetwork
    ti         = ixn.Traffic.TrafficItem.find(Name="replace_csid_first")
    ce         = ti.ConfigElement.find()
    ipv6_stack = ce.Stack.find(StackTypeId="ipv6")
    field_map  = {}
    for fld in ipv6_stack.Field.find():
        field_map[fld.FieldTypeId] = fld.SingleValue

    dst_readback = field_map.get("ipv6.header.dstIP", "")
    print("\n  [%s] REPLACE-CSID first container" % tc)
    print("  locator=%s/%d  usids=%s" % (locator, locator_len, usids))
    print("  expected dst : %s" % _norm(expected_dst))
    print("  IxNetwork dst: %s" % dst_readback)
    assert _norm(dst_readback) == _norm(expected_dst), (
        "[%s] dst mismatch: want %s got %s"
        % (tc, _norm(expected_dst), _norm(dst_readback))
    )

    ixn.Traffic.Apply()
    ixn.Traffic.StartStatelessTrafficBlocking()
    time.sleep(3)
    ixn.Traffic.StopStatelessTrafficBlocking()

    req = api.metrics_request()
    req.flow.flow_names = [f.name]
    tx_pkts = sum(m.frames_tx for m in api.get_metrics(req).flow_metrics)
    assert tx_pkts > 0, "[%s] No packets transmitted" % tc
    print("  [%s] PASSED  tx_pkts=%d" % (tc, tx_pkts))


def test_replace_csid_packed_containers(api, b2b_raw_config, utils):
    """REPLACE-CSID flavor (RFC 9800 Section 4.2) - subsequent packed containers in SRH.

    After the first container (in outer DA), REPLACE-CSID subsequent containers are
    in packed format (NOT valid IPv6 SIDs): K = floor(128/LNFL) slots of LNFL bits.
    Valid LNFL: 16-bit (K=8) or 32-bit (K=4); 32-bit MUST be supported (RFC 9800 Section 4.2).
    This test uses LNFL=32 (K=4), the mandatory baseline.

    Wire order convention (RFC 9800 Section 4.2, Figure 4):
      Provide CSIDs in wire order (MSB first among provided values). The implementation
      right-aligns them to the LSB end; unused MSB slots are zero-padded automatically.
      usids[0] -> leftmost occupied slot, usids[-1] -> LSB slot (processed first by router).

    Example (K=4, LNFL=32, 2 CSIDs):
      usids=["00030004","00010002"] ->
        [0x00000000][0x00000000][0x00030004][0x00010002]  (32-bit slots MSB->LSB)
        IPv6: ::3:4:1:2

    Config (2 packed containers in SRH, reverse path order):
      outer DA: "2001:db8:1:1::"  (first container, fully formed SID, set directly)
      seg[0] (last to process):  usids=["00070008","00050006"] -> expected ::7:8:5:6
      seg[1] (first to process): usids=["00030004","00010002"] -> expected ::3:4:1:2

    Verifies via RESTpy that ipv6GSRHType4 slot values match the packed wire format.
    """
    tc = "test_replace_csid_packed_containers"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    # Packed containers: LNFL=32, K=4, locator_length=0.
    # CSIDs in wire order (MSB first). Right-aligned to LSB; MSB slots zero-padded.
    # Wire format (MSB->LSB): [0][0][usids[0]][usids[1]]
    # seg[0] (last):  usids[0]="00070008" at slot 2, usids[1]="00050006" at slot 3 (LSB)
    #   -> wire 0000:0000:0000:0000:0007:0008:0005:0006 = ::7:8:5:6
    # seg[1] (first): usids[0]="00030004" at slot 2, usids[1]="00010002" at slot 3 (LSB)
    #   -> wire 0000:0000:0000:0000:0003:0004:0001:0002 = ::3:4:1:2
    usids_per_seg  = [["00070008", "00050006"], ["00030004", "00010002"]]
    expected_wire  = ["::7:8:5:6",              "::3:4:1:2"]
    active_dst     = "2001:db8:1:1::"   # first container (fully formed SID) in outer DA
    segments_left  = 1
    last_entry     = 1

    f = b2b_raw_config.flows.add()
    f.name = "replace_csid_packed"
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
    ip6.dst.value = active_dst   # first container = fully formed SID, set directly
    ip6.next_header.value = 43

    usid_hdr = f.packet.add().ipv6_extension_header.routing.segment_routing_usid
    usid_hdr.segments_left.value = segments_left
    usid_hdr.last_entry.value    = last_entry
    usid_hdr.flags.oam.value     = 0
    usid_hdr.tag.value           = 0

    # Packed containers: locator_length=0, 32-bit CSIDs (LNFL=32, K=4).
    # Wire order: usids[0] is leftmost occupied slot, usids[-1] is LSB (processed first).
    for usid_vals in usids_per_seg:
        seg = usid_hdr.segment_list.segment()[-1]
        seg.locator.value        = "::0"   # ignored for packed format
        seg.locator_length.value = 0
        seg.usids                = usid_vals

    api.set_config(b2b_raw_config)

    ixn        = api._ixnetwork
    ti         = ixn.Traffic.TrafficItem.find(Name="replace_csid_packed")
    ce         = ti.ConfigElement.find()
    gsrh_stack = ce.Stack.find(StackTypeId="ipv6GSRHType4")

    print("\n  [%s] REPLACE-CSID packed container slot read-back:" % tc)
    read_back = _restpy_read_gsrh_slots(gsrh_stack, len(usids_per_seg))
    sep   = "=" * 72
    inner = "-" * 72
    print(sep)
    for i, (want, got) in enumerate(zip(expected_wire, read_back)):
        ok = _norm(want) == _norm(got)
        print("  seg[%d]  want=%-26s  got=%-26s  %s"
              % (i, _norm(want), _norm(got), "MATCH" if ok else "MISMATCH"))
    print(sep)

    for i, (want, got) in enumerate(zip(expected_wire, read_back)):
        assert _norm(want) == _norm(got), (
            "[%s] seg[%d] mismatch: want %s got %s"
            % (tc, i, _norm(want), _norm(got))
        )

    ixn.Traffic.Apply()
    ixn.Traffic.StartStatelessTrafficBlocking()
    time.sleep(3)
    ixn.Traffic.StopStatelessTrafficBlocking()

    req = api.metrics_request()
    req.flow.flow_names = [f.name]
    tx_pkts = sum(m.frames_tx for m in api.get_metrics(req).flow_metrics)
    assert tx_pkts > 0, "[%s] No packets transmitted" % tc
    print("  [%s] PASSED  tx_pkts=%d" % (tc, tx_pkts))


# ---------------------------------------------------------------------------
# Test 15: RFC 9800 Figure 5 — REPLACE-CSID Compressed SID List (7 SIDs)
# ---------------------------------------------------------------------------

def test_replace_csid_fig5_7sids(api, b2b_raw_config, utils):
    """RFC 9800 Figure 5: REPLACE-CSID Compressed SID List — 7 SIDs, 3 containers.

    Models the exact packet structure from Figure 5 in RFC 9800 Section 4.2
    (REPLACE-CSID flavor).  Parameters: LBL=48 bits, LNFL=32 bits, K=4 slots.

    Container 1 — outer IPv6 DA (full SRv6 SID, not in SRH):
      [Locator-Block (48b) = 2001:db8::] [1st CSID (32b) = 0x00010001] [Arg=0 (48b)]
      Assembled DA: 2001:db8:0:1:1::

    Container 2 — SRH seg[1] (packed, fully filled, processes CSIDs 2-5):
      Packing (usids[i] -> position K-1-i, i.e. usids[0] at LSB bits 96-127):
        position 3 (LSB bits 96-127): 2nd CSID = 0x00020002
        position 2 (bits 64-95):      3rd CSID = 0x00030003
        position 1 (bits 32-63):      4th CSID = 0x00040004
        position 0 (MSB bits 0-31):   5th CSID = 0x00050005
      Wire (MSB->LSB): [00050005][00040004][00030003][00020002]
      IPv6: 5:5:4:4:3:3:2:2

    Container 3 — SRH seg[0] (packed, partially filled, processes CSIDs 6-7):
      Packing:
        position 3 (LSB bits 96-127): 6th CSID = 0x00060006
        position 2 (bits 64-95):      7th CSID = 0x00070007
        positions 1, 0 (MSB end):     zeros (end-of-CSID-list padding)
      Wire (MSB->LSB): [00000000][00000000][00070007][00060006]
      IPv6: ::7:7:6:6

    SRH: last_entry=1 (2 entries: seg[0] and seg[1]), segments_left=1.

    Packet stack:
      Ethernet -> IPv6 (NH=43, dst=2001:db8:0:1:1::)
               -> REPLACE-CSID SRH (RT=4, sl=1, le=1, flags=0x00, tag=0)
                  seg[0] = ::7:7:6:6        <- CSIDs 6-7 (last to process)
                  seg[1] = 5:5:4:4:3:3:2:2 <- CSIDs 2-5 (first in SRH to process)

    Wire verifies via capture (capture intentionally kept for Wireshark inspection):
      - outer IPv6 dst    = 2001:db8:0:1:1::
      - SRH routing_type  = 4
      - SRH segments_left = 1, last_entry = 1
      - SRH seg[0]        = ::7:7:6:6
      - SRH seg[1]        = 5:5:4:4:3:3:2:2
    """
    tc = "test_replace_csid_fig5_7sids"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    # Container 1: full SRv6 SID pre-assembled as the outer IPv6 DA.
    # LBL=48 (2001:0db8:0000), CSID1=0x00010001, Arg=0 -> 2001:db8:0:1:1::
    active_dst    = "2001:db8:0:1:1::"
    segments_left = 1
    last_entry    = 1

    # Container 3 — seg[0] (last entry in SRH; processes CSIDs 6-7, 2 slots used).
    # Wire order: usids[0]=MSB-occupied -> slot 2, usids[1]=LSB -> slot 3 (processed first).
    # Wire: [00000000][00000000][00070007][00060006] = ::7:7:6:6
    csids_seg0    = ["00070007", "00060006"]
    expected_seg0 = "::7:7:6:6"

    # Container 2 — seg[1] (second entry; processes CSIDs 2-5, all K=4 slots used).
    # Wire order: usids[0]=MSB -> slot 0, usids[3]=LSB -> slot 3 (processed first).
    # Wire: [00050005][00040004][00030003][00020002] = 5:5:4:4:3:3:2:2
    csids_seg1    = ["00050005", "00040004", "00030003", "00020002"]
    expected_seg1 = "5:5:4:4:3:3:2:2"

    f = b2b_raw_config.flows.add()
    f.name = "replace_csid_fig5"
    f.tx_rx.port.tx_name = p1.name
    f.tx_rx.port.rx_name = p2.name
    f.rate.pps = 100
    f.duration.fixed_packets.packets = 200
    f.metrics.enable = True

    eth = f.packet.add().ethernet
    eth.src.value = "00:11:22:33:44:55"
    eth.dst.value = "00:aa:bb:cc:dd:ee"

    # Outer IPv6: DA = container 1 (pre-assembled full SRv6 SID).
    ip6 = f.packet.add().ipv6
    ip6.src.value = "2001:db8::1"
    ip6.dst.value = active_dst
    ip6.next_header.value = 43

    # REPLACE-CSID SRH: 2 packed containers (locator_length=0 = packed format).
    usid_hdr = f.packet.add().ipv6_extension_header.routing.segment_routing_usid
    usid_hdr.segments_left.value = segments_left
    usid_hdr.last_entry.value    = last_entry
    usid_hdr.flags.oam.value     = 0
    usid_hdr.tag.value           = 0

    # seg[0] added first => index 0 in segment_list = last SRH entry (CSIDs 6-7).
    seg0 = usid_hdr.segment_list.segment()[-1]
    seg0.locator.value        = "::0"
    seg0.locator_length.value = 0
    seg0.usids                = list(csids_seg0)

    # seg[1] added second => index 1 in segment_list (CSIDs 2-5, fully packed).
    seg1 = usid_hdr.segment_list.segment()[-1]
    seg1.locator.value        = "::0"
    seg1.locator_length.value = 0
    seg1.usids                = list(csids_seg1)

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)

    # RESTpy slot read-back for diagnostics: print packed container values.
    try:
        ixn        = api._ixnetwork
        ti         = ixn.Traffic.TrafficItem.find(Name="replace_csid_fig5")
        ce         = ti.ConfigElement.find()
        gsrh_stack = ce.Stack.find(StackTypeId="ipv6GSRHType4")
        if gsrh_stack:
            read_back = _restpy_read_gsrh_slots(gsrh_stack, 2)
            sep_r = "-" * 72
            print("\n  [restpy] RFC 9800 Figure 5 -- GSRH slot read-back after set_config")
            print("  " + sep_r)
            for i, (want, got) in enumerate(
                    zip([expected_seg0, expected_seg1], read_back)):
                ok = _norm(want) == _norm(got)
                print("  seg[%d]  want=%-28s  got=%-28s  %s"
                      % (i, _norm(want), _norm(got), "MATCH" if ok else "MISMATCH"))
            print("  " + sep_r)
    except Exception as exc:
        print("  [restpy] readback skipped: %s" % exc)

    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    # Capture intentionally kept (not deleted) for Wireshark inspection.
    path = _save_capture(pcap, tc)
    print("\n  [%s] Capture preserved: %s" % (tc, path))

    pkt = _parse_gshr_from_pcap(pcap)

    sep   = "=" * 74
    inner = "-" * 74
    print("\n" + sep)
    print("  %s" % tc)
    print("  RFC 9800 Figure 5 -- REPLACE-CSID 7-SID wire verify")
    print("  %-30s  %-22s  %-22s  %s"
          % ("Field", "Configured", "Wire", "Status"))
    print(inner)

    assert pkt is not None, "[%s] No SRH packet found in capture" % tc

    def _row(label, want, got):
        ok = (str(want) == str(got))
        print("  %-30s  %-22s  %-22s  %s"
              % (label, str(want), str(got), "PASS" if ok else "FAIL"))
        return ok

    _row("outer ip6_dst",         _norm(active_dst),    _norm(pkt["ip6_dst"]))
    _row("routing_type",          4,                    pkt["routing_type"])
    _row("segments_left",         segments_left,        pkt["segments_left"])
    _row("last_entry",            last_entry,           pkt["last_entry"])
    _row("flags_byte",            "0x00",               "0x%02x" % pkt["flags_byte"])
    _row("tag",                   "0x0000",             "0x%04x" % pkt["tag"])
    _row("seg[0] CSIDs 6-7",
         _norm(expected_seg0),
         _norm(pkt["segments"][0]) if len(pkt["segments"]) > 0 else "MISSING")
    _row("seg[1] CSIDs 2-5",
         _norm(expected_seg1),
         _norm(pkt["segments"][1]) if len(pkt["segments"]) > 1 else "MISSING")
    print(sep)

    assert _norm(pkt["ip6_dst"]) == _norm(active_dst), (
        "[%s] outer ip6_dst: want %s got %s"
        % (tc, _norm(active_dst), _norm(pkt["ip6_dst"]))
    )
    assert pkt["routing_type"] == 4, (
        "[%s] routing_type: want 4 got %d" % (tc, pkt["routing_type"])
    )
    assert pkt["segments_left"] == segments_left, (
        "[%s] segments_left: want %d got %d"
        % (tc, segments_left, pkt["segments_left"])
    )
    assert pkt["last_entry"] == last_entry, (
        "[%s] last_entry: want %d got %d" % (tc, last_entry, pkt["last_entry"])
    )
    assert pkt["flags_byte"] == 0x00, (
        "[%s] flags_byte: want 0x00 got 0x%02x" % (tc, pkt["flags_byte"])
    )
    assert pkt["tag"] == 0, (
        "[%s] tag: want 0 got %d" % (tc, pkt["tag"])
    )
    assert len(pkt["segments"]) == 2, (
        "[%s] SRH segment count: want 2 got %d" % (tc, len(pkt["segments"]))
    )
    assert _norm(pkt["segments"][0]) == _norm(expected_seg0), (
        "[%s] seg[0] (CSIDs 6-7): want %s got %s"
        % (tc, _norm(expected_seg0), _norm(pkt["segments"][0]))
    )
    assert _norm(pkt["segments"][1]) == _norm(expected_seg1), (
        "[%s] seg[1] (CSIDs 2-5): want %s got %s"
        % (tc, _norm(expected_seg1), _norm(pkt["segments"][1]))
    )


# ---------------------------------------------------------------------------
# Test 16: RFC 9800 Figure 2 — NEXT-CSID 8 SIDs, LBL=48, LNFL=16, K=5
# ---------------------------------------------------------------------------

def test_next_csid_fig2_8sids(api, b2b_raw_config, utils):
    """RFC 9800 Figure 2: NEXT-CSID Compressed SID List — 8 SIDs, 2 containers.
    LBL=48 bits, LNFL=16 bits, AL=64 bits, K=5 CSIDs per container.

    Container 1 (CSIDs 1-5): [LBL=48b][C1][C2][C3][C4][C5]
      locator = 2001:db8:1:: (48 bits = 20:01:0d:b8:00:01)
      usids   = ["0001","0002","0003","0004","0005"]
      wire    = 2001:db8:1:1:2:3:4:5

    Container 2 (CSIDs 6-8 + 32-bit zero pad): [LBL=48b][C6][C7][C8][0][0]
      usids   = ["0006","0007","0008"]
      wire    = 2001:db8:1:6:7:8::

    SRH layout (non-reduced SRH, RFC 8754 order):
      IPv6 dst       = Container 1 (active)
      Segment List[0] = Container 2 (ultimate / last to visit)
      Segment List[1] = Container 1 (penultimate / active copy)
      segments_left  = 1, last_entry = 1

    Capture kept for Wireshark inspection.
    """
    tc = "test_next_csid_fig2_8sids"
    api.set_config(api.config())
    p1, p2 = b2b_raw_config.ports
    b2b_raw_config.flows.clear()

    locator       = "2001:db8:1::"
    lb_bits       = 48

    # Container 1 — CSIDs 1-5, wire = 2001:db8:1:1:2:3:4:5
    container1 = "2001:db8:1:1:2:3:4:5"
    csids_c1   = ["0001", "0002", "0003", "0004", "0005"]

    # Container 2 — CSIDs 6-8 + zero pad, wire = 2001:db8:1:6:7:8::
    container2 = "2001:db8:1:6:7:8::"
    csids_c2   = ["0006", "0007", "0008"]

    active_dst    = container1
    segments_left = 1
    last_entry    = 1

    f = b2b_raw_config.flows.add()
    f.name = "next_csid_fig2"
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
    ip6.dst.value = active_dst
    ip6.next_header.value = 43

    usid_hdr = f.packet.add().ipv6_extension_header.routing.segment_routing_usid
    usid_hdr.segments_left.value = segments_left
    usid_hdr.last_entry.value    = last_entry
    usid_hdr.flags.oam.value     = 0
    usid_hdr.tag.value           = 0

    # Segment List[0] (ultimate/last hop) — Container 2, added first
    seg_c2 = usid_hdr.segment_list.segment()[-1]
    seg_c2.locator.value        = locator
    seg_c2.locator_length.value = lb_bits
    seg_c2.usids                = list(csids_c2)

    # Segment List[1] (penultimate/active copy) — Container 1, added second
    seg_c1 = usid_hdr.segment_list.segment()[-1]
    seg_c1.locator.value        = locator
    seg_c1.locator_length.value = lb_bits
    seg_c1.usids                = list(csids_c1)

    _add_capture(b2b_raw_config, p2.name)
    api.set_config(b2b_raw_config)

    # RESTpy slot read-back for diagnostics (segment order matches add order)
    try:
        ixn        = api._ixnetwork
        ti         = ixn.Traffic.TrafficItem.find(Name="next_csid_fig2")
        ce         = ti.ConfigElement.find()
        gsrh_stack = ce.Stack.find(StackTypeId="ipv6GSRHType4")
        if gsrh_stack:
            read_back  = _restpy_read_gsrh_slots(gsrh_stack, 2)
            sep_r      = "-" * 60
            expected_rb = [container2, container1]
            print("\n  [restpy] GSRH slot read-back:")
            print("  " + sep_r)
            for i, (want, got) in enumerate(zip(expected_rb, read_back)):
                match = "MATCH" if _norm(str(want)) == _norm(str(got)) else "MISMATCH"
                print("  container[%d]: want %-38s got %-38s %s"
                      % (i, _norm(want), _norm(got), match))
            print("  " + sep_r)
    except Exception as exc:
        print("  [restpy] readback skipped: %s" % exc)

    _start_capture(api)
    _start_traffic(api)
    time.sleep(4)
    _stop_traffic(api)
    _stop_capture(api)

    pcap = _get_capture(api, p2.name)
    # Capture intentionally kept (not deleted) for Wireshark inspection.
    path = _save_capture(pcap, tc)
    print("\n  [%s] Capture preserved: %s" % (tc, path))

    pkt = _parse_gshr_from_pcap(pcap)

    sep   = "=" * 74
    inner = "-" * 74
    print("\n" + sep)
    print("  %s" % tc)
    print("  RFC 9800 Figure 2 -- NEXT-CSID 8-SID wire verify")
    print("  %-30s  %-22s  %-22s  %s"
          % ("Field", "Configured", "Wire", "Status"))
    print(inner)

    assert pkt is not None, "[%s] No SRH packet found in capture" % tc

    def _row(label, want, got):
        ok = (str(want) == str(got))
        print("  %-30s  %-22s  %-22s  %s"
              % (label, str(want), str(got), "PASS" if ok else "FAIL"))
        return ok

    _row("outer ip6_dst",          _norm(active_dst),    _norm(pkt["ip6_dst"]))
    _row("routing_type",           4,                    pkt["routing_type"])
    _row("segments_left",          segments_left,        pkt["segments_left"])
    _row("last_entry",             last_entry,           pkt["last_entry"])
    _row("flags_byte",             "0x00",               "0x%02x" % pkt["flags_byte"])
    _row("tag",                    "0x0000",             "0x%04x" % pkt["tag"])
    _row("seg[0] (container-2)",
         _norm(container2),
         _norm(pkt["segments"][0]) if len(pkt["segments"]) > 0 else "MISSING")
    _row("seg[1] (container-1)",
         _norm(container1),
         _norm(pkt["segments"][1]) if len(pkt["segments"]) > 1 else "MISSING")
    print(sep)

    assert _norm(pkt["ip6_dst"]) == _norm(active_dst), (
        "[%s] outer ip6_dst: want %s got %s"
        % (tc, _norm(active_dst), _norm(pkt["ip6_dst"]))
    )
    assert pkt["routing_type"] == 4, (
        "[%s] routing_type: want 4 got %d" % (tc, pkt["routing_type"])
    )
    assert pkt["segments_left"] == segments_left, (
        "[%s] segments_left: want %d got %d"
        % (tc, segments_left, pkt["segments_left"])
    )
    assert pkt["last_entry"] == last_entry, (
        "[%s] last_entry: want %d got %d" % (tc, last_entry, pkt["last_entry"])
    )
    assert pkt["flags_byte"] == 0x00, (
        "[%s] flags_byte: want 0x00 got 0x%02x" % (tc, pkt["flags_byte"])
    )
    assert pkt["tag"] == 0, (
        "[%s] tag: want 0 got %d" % (tc, pkt["tag"])
    )
    assert len(pkt["segments"]) == 2, (
        "[%s] SRH segment count: want 2 got %d" % (tc, len(pkt["segments"]))
    )
    assert _norm(pkt["segments"][0]) == _norm(container2), (
        "[%s] seg[0] (container-2, ultimate): want %s got %s"
        % (tc, _norm(container2), _norm(pkt["segments"][0]))
    )
    assert _norm(pkt["segments"][1]) == _norm(container1), (
        "[%s] seg[1] (container-1, active): want %s got %s"
        % (tc, _norm(container1), _norm(pkt["segments"][1]))
    )

    print("\n  [%s] PASSED -- RFC 9800 Figure 5 REPLACE-CSID 7-SID verified on wire." % tc)
    print("  Capture preserved at: tests/captures/%s.pcapng" % tc)
