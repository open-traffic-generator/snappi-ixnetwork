from abstract_open_traffic_generator import flow


def test_fixed_ip_addr(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - fixed src and dst IPv4 address

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    src = '00:0C:29:E3:53:EA'
    dst = '00:0C:29:E3:53:F4'

    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(src),
                dst=flow.Pattern(dst)
            )
        ),
        flow.Header(
            flow.Ipv4(
                src=flow.Pattern(src_ip),
                dst=flow.Pattern(dst_ip)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'Destination Address': dst_ip,
        'Source Address': src_ip,
    }
    utils.validate_config(api, 'ipv4', **attrs)
