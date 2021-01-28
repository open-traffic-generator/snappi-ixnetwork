import pytest


@pytest.mark.skip("skip until migrated to snappi")
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

    pat = flow.Pattern

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
                header_length=pat('5'),
                total_length=pat('100'),
                identification=pat('1234'),
                reserved=pat('1'),
                dont_fragment=pat('1'),
                more_fragments=pat('1'),
                fragment_offset=pat('0'),
                time_to_live=pat('50'),
                protocol=pat('200'),
                header_checksum=pat('1234')
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)
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
