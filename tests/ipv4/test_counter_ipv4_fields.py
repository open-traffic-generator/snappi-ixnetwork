def test_counter_ip_fields(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - counter pattern for the fields
      header len, total len, identification,
      reserved, don't fragment, more fragment,
      fragment offset, time to live, protocol,
      header checksum

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    fields = [
        "header_length", "total_length", "identification",
        "reserved", "dont_fragment", "more_fragments", "fragment_offset",
        "time_to_live", "protocol", "header_checksum"
    ]
    start = [
        5, 0, 0, 0, 0, 0, 0, 0, 0, 0
    ]
    step = [
        1, 2, 1000, 1, 1, 1, 100, 10, 1, 10
    ]
    count = [
        11, 10000, 65, 10, 10, 10, 1000, 10000, 1000, 1000
    ]
    # import snappi
    # f = snappi.Api().config().flows.flow()[-1]

    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[-1]
    eth.src.value = "ab:ab:ab:ab:bc:bc"
    eth.dst.value = "bc:bc:bc:bc:ab:ab"
    ipv4.src.value = "10.1.1.1"
    ipv4.dst.value = "10.1.1.2"
    for i, field in enumerate(fields):
        f_obj = getattr(ipv4, field)
        f_obj.increment.start = start[i]
        f_obj.increment.step = step[i]
        f_obj.increment.count = count[i]

    api.set_config(b2b_raw_config)
    keys = [
        'Header Length',
        'Total Length (octets)',
        'Identification',
        'Reserved',
        'Fragment',
        'Last Fragment',
        'Fragment offset',
        'TTL (Time to live)',
        'Protocol',
        'Header checksum',
    ]
    attrs = dict()
    for i, k in enumerate(keys):
        attrs[k] = (
            str(start[i]), str(step[i]), str(count[i])
        )

    utils.validate_config(api, 'ipv4', **attrs)
