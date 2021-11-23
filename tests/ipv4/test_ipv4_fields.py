def test_ipv4_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw raw IPv4 flows with ,
    - fixed pattern for the fields
      header len, total len, identification, reserved, don't fragment,
      more fragment, fragment offset, time to live, protocol, header checksum
    - list pattern for the fields
      header len, total len, identification, reserved, don't fragment,
      more fragment, fragment offset, time to live, protocol, header checksum
    - counter pattern for the fields
      header len, total len, identification, reserved, don't fragment,
      more fragment, fragment offset, time to live, protocol, header checksum

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"

    flow1.packet.ethernet().ipv4()
    eth = flow1.packet[0]
    ipv4 = flow1.packet[1]
    eth.src.value = src
    eth.dst.value = dst
    ipv4.src.value = src_ip
    ipv4.dst.value = dst_ip
    ipv4.header_length.value = 5
    ipv4.total_length.value = 100
    ipv4.identification.value = 1234
    ipv4.reserved.value = 1
    ipv4.dont_fragment.value = 1
    ipv4.more_fragments.value = 1
    ipv4.fragment_offset.value = 0
    ipv4.time_to_live.value = 50
    ipv4.protocol.value = 200

    # list
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    src_ip = "10.1.1.1"
    dst_ip = "20.1.1.1"

    from random import Random

    r = Random()

    header_length = [r.randint(5, 15) for i in range(10)]
    total_length = [r.randint(0, 65535) for i in range(10)]
    identification = [r.randint(0, 65535) for i in range(10)]
    reserved = [r.randint(0, 1) for i in range(10)]
    dont_fragment = [r.randint(0, 1) for i in range(10)]
    more_fragments = [r.randint(0, 1) for i in range(10)]
    fragment_offset = [r.randint(0, 31) for i in range(10)]
    time_to_live = [r.randint(0, 255) for i in range(10)]
    protocol = [r.randint(0, 255) for i in range(10)]
    flow2.packet.ethernet().ipv4()
    eth = flow2.packet[0]
    ipv4 = flow2.packet[1]
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

    # counter
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    fields = [
        "header_length",
        "total_length",
        "identification",
        "reserved",
        "dont_fragment",
        "more_fragments",
        "fragment_offset",
        "time_to_live",
        "protocol",
    ]
    start = [5, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    step = [1, 2, 1000, 1, 1, 1, 10, 10, 1, 10]
    count = [11, 10000, 65, 10, 10, 10, 1000, 10000, 1000, 1000]

    flow3.packet.ethernet().ipv4()
    eth = flow3.packet[0]
    ipv4 = flow3.packet[-1]
    eth.src.value = "ab:ab:ab:ab:bc:bc"
    eth.dst.value = "bc:bc:bc:bc:ab:ab"
    ipv4.src.value = "10.1.1.1"
    ipv4.dst.value = "10.1.1.2"
    for i, field in enumerate(fields):
        f_obj = getattr(ipv4, field)
        f_obj.increment.start = start[i]
        f_obj.increment.step = step[i]
        f_obj.increment.count = count[i]

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "Header Length": "5",
        "Total Length (octets)": "100",
        "Identification": "1234",
        "Reserved": "1",
        "Fragment": "1",
        "Last Fragment": "1",
        "Fragment offset": "0",
        "TTL (Time to live)": "50",
        # TODO: Revert the comment for snappi 6.x
        # "Protocol": "200",
    }
    utils.validate_config(api, "f1", "ipv4", **f1_attrs)

    # list validation
    f2_attrs = {
        "Header Length": [str(h) for h in header_length],
        "Total Length (octets)": [str(t) for t in total_length],
        "Identification": [str(i) for i in identification],
        "Reserved": [str(r) for r in reserved],
        "Fragment": [str(df) for df in dont_fragment],
        "Last Fragment": [str(mf) for mf in more_fragments],
        "Fragment offset": [str(fo) for fo in fragment_offset],
        "TTL (Time to live)": [str(ttl) for ttl in time_to_live],
        # TODO: Revert the comment for snappi 6.x
        # "Protocol": [str(pro) for pro in protocol],
    }
    utils.validate_config(api, "f2", "ipv4", **f2_attrs)

    # counter validation
    keys = [
        "Header Length",
        "Total Length (octets)",
        "Identification",
        "Reserved",
        "Fragment",
        "Last Fragment",
        "Fragment offset",
        "TTL (Time to live)",
        # TODO: Revert the comment for snappi 6.x
        # "Protocol",
    ]
    f3_attrs = dict()
    for i, k in enumerate(keys):
        f3_attrs[k] = (str(start[i]), str(step[i]), str(count[i]))

    utils.validate_config(api, "f3", "ipv4", **f3_attrs)
