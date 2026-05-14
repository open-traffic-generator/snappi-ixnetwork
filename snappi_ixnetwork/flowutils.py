"""SRv6 uSID flow-building helpers.

Two functions wrap the low-level snappi PatternFlow setter calls so callers
work with plain Python types (str, int, list[str]) rather than the internal
object hierarchy of FlowIpv6UsidDst and FlowIpv6SegmentRoutingUsidSegment.
"""


def set_usid_dst(dst_usids, locator, locator_length, usids):
    """Populate a FlowIpv6UsidDst object from a locator prefix and uSID list.

    Sets the three structured fields of ``ipv6.dst_usids`` in one call for
    the no-SRH reduced encapsulation case (RFC 9800 Section 4), where the
    entire SR path fits in a single 128-bit uSID container placed directly
    in the outer IPv6 destination field with no Segment Routing Header.

    The implementation packs the fields as:
        LB (locator_length high-order bits of locator) || uSID-1 || uSID-2 || ...
        || EoC (zero-pad to 128 bits)

    Args:
        dst_usids:            ``FlowIpv6UsidDst`` obtained from ``ipv6.dst_usids``.
        locator (str):        IPv6 locator block prefix, e.g. ``"fc00::"``.
        locator_length (int): Locator block length in bits, e.g. ``32`` for F3216.
        usids (list[str]):    Ordered uSID hex values to pack after the LB,
                              e.g. ``["0001", "0002", "0003"]``.

    Example::

        ip6 = flow.packet.add().ipv6
        ip6.src.value = "2001:db8::1"
        set_usid_dst(ip6.dst_usids, "fc00::", 32, ["0001", "0002", "0003"])
        # assembles IPv6 dst = fc00:0:1:2:3::
    """
    dst_usids.locator.value = locator
    dst_usids.locator_length.value = locator_length
    for usid_val in usids:
        dst_usids.usids.add().usid = usid_val


def add_usid_container(segment_list, locator, locator_length, usids):
    """Append one uSID container to a ``segment_routing_usid`` segment list.

    Adds a ``FlowIpv6SegmentRoutingUsidSegment`` entry built from an explicit
    locator block prefix and ordered uSID values.  Intended for G-SRH flows
    (``segment_routing_usid`` choice) that carry multiple uSID containers in
    the SRH segment list (RFC 9800 Section 4).

    Call once per container in path order (first hop first); the
    implementation appends segments to the iter and sets locator,
    locator_length, and each uSID on the new segment entry.

    Args:
        segment_list:         ``FlowIpv6SegmentRoutingUsidSegmentIter``
                              from ``segment_routing_usid.segment_list``.
        locator (str):        IPv6 locator block prefix, e.g. ``"fc00::"``.
        locator_length (int): Locator block length in bits, e.g. ``32`` for F3216.
        usids (list[str]):    Ordered uSID hex values within this container,
                              e.g. ``["0001", "0002"]``.

    Example::

        usid_hdr = ext.ipv6_extension_header.routing.segment_routing_usid
        add_usid_container(usid_hdr.segment_list, "fc00::", 32, ["0001", "0002"])
        add_usid_container(usid_hdr.segment_list, "fc00::", 32, ["0003", "0004"])
    """
    seg = segment_list.segment()[-1]
    seg.locator.value = locator
    seg.locator_length.value = locator_length
    for usid_val in usids:
        seg.usids.add().usid = usid_val
