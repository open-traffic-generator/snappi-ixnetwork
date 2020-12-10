from abstract_open_traffic_generator import flow


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
    src = '00:0C:29:E3:53:EA'
    dst = '00:0C:29:E3:53:F4'

    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    pat = flow.Pattern

    header_length = flow.Counter(
        start='5',
        step='1',
        count=11
    )
    total_length = flow.Counter(
        start='0',
        step='2',
        count=10000
    )
    identification = flow.Counter(
        start='0',
        step='1000',
        count=65
    )
    reserved = flow.Counter(
        start='0',
        step='1',
        count=10
    )
    dont_fragment = flow.Counter(
        start='0',
        step='1',
        count=10
    )
    more_fragments = flow.Counter(
        start='0',
        step='1',
        count=10
    )
    fragment_offset = flow.Counter(
        start='0',
        step='100',
        count=1000
    )
    time_to_live = flow.Counter(
        start='0',
        step='10',
        count=10000
    )
    protocol = flow.Counter(
        start='0',
        step='1',
        count=1000
    )
    header_checksum = flow.Counter(
        start='0',
        step='10',
        count=1000
    )

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=pat(src),
                dst=pat(dst)
            )
        ),
        flow.Header(
            flow.Ipv4(
                src=pat(src_ip),
                dst=pat(dst_ip),
                header_length=pat(header_length),
                total_length=pat(total_length),
                identification=pat(identification),
                reserved=pat(reserved),
                dont_fragment=pat(dont_fragment),
                more_fragments=pat(more_fragments),
                fragment_offset=pat(fragment_offset),
                time_to_live=pat(time_to_live),
                protocol=pat(protocol),
                header_checksum=pat(header_checksum)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'Header Length': (
            header_length.start,
            header_length.step,
            str(header_length.count),
        ),
        'Total Length (octets)': (
            total_length.start,
            total_length.step,
            str(total_length.count),
        ),
        'Identification': (
            identification.start,
            identification.step,
            str(identification.count),
        ),
        'Reserved': (
            reserved.start,
            reserved.step,
            str(reserved.count),
        ),
        'Fragment': (
            dont_fragment.start,
            dont_fragment.step,
            str(dont_fragment.count),
        ),
        'Last Fragment': (
            more_fragments.start,
            more_fragments.step,
            str(more_fragments.count),
        ),
        'Fragment offset': (
            fragment_offset.start,
            fragment_offset.step,
            str(fragment_offset.count),
        ),
        'TTL (Time to live)': (
            time_to_live.start,
            time_to_live.step,
            str(time_to_live.count),
        ),
        'Protocol': (
            protocol.start,
            protocol.step,
            str(protocol.count),
        ),
        'Header checksum': (
            header_checksum.start,
            header_checksum.step,
            str(header_checksum.count),
        )
    }
    utils.validate_config(api, 'ipv4', **attrs)
