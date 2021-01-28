import pytest


@pytest.mark.skip("skip until migrated to snappi")
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
    src = '00:0C:29:E3:53:EA'
    dst = '00:0C:29:E3:53:F4'

    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    pat = flow.Pattern

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
    header_checksum = [
        str('{:02x}'.format(r.randint(0, 65535))) for i in range(10)
    ]

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
        'Header Length': header_length,
        'Total Length (octets)': total_length,
        'Identification': identification,
        'Reserved': reserved,
        'Fragment': dont_fragment,
        'Last Fragment': more_fragments,
        'Fragment offset': fragment_offset,
        'TTL (Time to live)': time_to_live,
        'Protocol': protocol,
        'Header checksum': header_checksum
    }
    utils.validate_config(api, 'ipv4', **attrs)
