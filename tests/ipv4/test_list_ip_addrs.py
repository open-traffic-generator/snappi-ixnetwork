from abstract_open_traffic_generator import flow
import utils


def test_list_ip_addr(api, settings, b2b_raw_config):
    """
    Configure a raw IPv4 flow with,
    - list pattern src and dst IPv4 address

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    step = '05:00:00:02:01:00'
    src = utils.mac_or_ip_addr_from_counter_pattern(
        '00:0C:29:E3:53:EA', step, 5, True
    )
    dst = utils.mac_or_ip_addr_from_counter_pattern(
        '00:0C:29:E3:53:F4', step, 5, True
    )

    step = '0.0.1.0'
    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    src_ip_list = utils.mac_or_ip_addr_from_counter_pattern(
        src_ip, step, 5, True, False
    )
    dst_ip_list = utils.mac_or_ip_addr_from_counter_pattern(
        dst_ip, step, 5, True, False
    )

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(src),
                dst=flow.Pattern(dst)
            )
        ),
        flow.Header(
            flow.Ipv4(
                src=flow.Pattern(src_ip_list),
                dst=flow.Pattern(dst_ip_list)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'Destination Address': dst_ip_list,
        'Source Address': src_ip_list,
    }
    utils.validate_config(api, 'ipv4', **attrs)
