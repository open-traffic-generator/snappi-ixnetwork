from abstract_open_traffic_generator import flow
import utils


def test_counter_ip_addr(api, settings, b2b_raw_config):
    """
    Configure a raw IPv4 flow with,
    - Counter Pattern src and dst IPv4 address

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    count = 10
    step = '05:00:00:02:01:00'
    src = utils.mac_or_ip_addr_from_counter_pattern(
        '00:0C:29:E3:53:EA', step, count, True
    )
    dst = utils.mac_or_ip_addr_from_counter_pattern(
        '00:0C:29:E3:53:F4', step, count, True
    )

    step = '0.0.1.0'
    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    src_ip_list = flow.Counter(
        start=src_ip,
        step=step,
        count=count
    )

    dst_ip_list = flow.Counter(
        start=dst_ip,
        step=step,
        count=count,
        up=False
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
        'Destination Address': (dst_ip, step, str(count)),
        'Source Address': (src_ip, step, str(count)),
    }
    utils.validate_config(api, 'ipv4', **attrs)
