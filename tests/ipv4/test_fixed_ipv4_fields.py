def test_fixed_ip_fields(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - fixed pattern for the fields
      header len, total len, identification,
      reserved, don't fragment, more fragment,
      fragment offset, time to live, protocol,
      header checksum

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    src = '00:0C:29:E3:53:EA'
    dst = '00:0C:29:E3:53:F4'

    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    f.packet.ethernet().ipv4()
    eth = f.packet[0]
    ipv4 = f.packet[1]
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
    ipv4.header_checksum.value = 1234

    api.set_config(b2b_raw_config)
    attrs = {
        'Header Length': '5',
        'Total Length (octets)': '100',
        'Identification': '1234',
        'Reserved': '1',
        'Fragment': '1',
        'Last Fragment': '1',
        'Fragment offset': '0',
        'TTL (Time to live)': '50',
        'Protocol': '200',
        'Header checksum': '1234'
    }
    utils.validate_config(api, 'ipv4', **attrs)
