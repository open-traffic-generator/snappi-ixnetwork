def test_list_ip_fields(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - list pattern for the fields
      header len, total len, identification,
      reserved, don't fragment, more fragment,
      fragment offset, time to live, protocol,
      header checksum

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"

    from random import Random

    r = Random()

    header_length = [str(r.randint(5, 15)) for i in range(10)]
    total_length = [str(r.randint(0, 65535)) for i in range(10)]
    identification = [str(r.randint(0, 65535)) for i in range(10)]
    reserved = [str(r.randint(0, 1)) for i in range(10)]
    dont_fragment = [str(r.randint(0, 1)) for i in range(10)]
    more_fragments = [str(r.randint(0, 1)) for i in range(10)]
    fragment_offset = [str(r.randint(0, 8191)) for i in range(10)]
    time_to_live = [str(r.randint(0, 255)) for i in range(10)]
    protocol = [str(r.randint(0, 255)) for i in range(10)]
    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[1]
    eth.src.value = src
    eth.dst.value = dst
    ipv4.src.value = src_ip
    ipv4.dst.value = dst_ip
    ipv4.header_length.values = header_length
    ipv4.total_length.values = total_length
    ipv4.identification.values = identification
    ipv4.reserved.values = reserved
    ipv4.dont_fragment.values = dont_fragment
    ipv4.more_fragments.values = more_fragments
    ipv4.fragment_offset.values = fragment_offset
    ipv4.time_to_live.values = time_to_live
    ipv4.protocol.values = protocol

    api.set_config(b2b_raw_config)
    attrs = {
        "Header Length": header_length,
        "Total Length (octets)": total_length,
        "Identification": identification,
        "Reserved": reserved,
        "Fragment": dont_fragment,
        "Last Fragment": more_fragments,
        "Fragment offset": fragment_offset,
        "TTL (Time to live)": time_to_live,
        "Protocol": protocol,
    }
    utils.validate_config(api, "ipv4", **attrs)
