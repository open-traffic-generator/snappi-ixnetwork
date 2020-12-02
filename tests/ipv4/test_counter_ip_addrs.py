from abstract_open_traffic_generator import flow
from abstract_open_traffic_generator.flow import Counter
import utils
import ipv4


def test_fixed_mac_addrs(api, settings, b2b_raw_config):
    """
    Configure a raw ethernet flow with,
    - fixed src and dst MAC address
    - 10 frames of 1518B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst MAC address
    """
    f = b2b_raw_config.flows[0]
    size = 100
    packets = 10
    step = '05:00:00:02:01:00'
    src = utils.generate_mac_counter_list('00:0C:29:E3:53:EA', step, 10, True)
    dst = utils.generate_mac_counter_list('00:0C:29:E3:53:F4', step, 10, True)

    step = '0.0.1.0'
    src_ip = '10.1.1.1'
    dst_ip = '20.1.1.1'

    src_ip_list = Counter(
        start=src_ip,
        step=step,
        count=packets
    )

    dst_ip_list = Counter(
        start=dst_ip,
        step=step,
        count=packets,
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
    f.duration = flow.Duration(flow.FixedPackets(packets=packets))
    f.size = flow.Size(size)
    f.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: utils.stats_ok(api, size, packets), 'stats to be as expected'
    )

    src_ip = utils.generate_ip_counter_list(src_ip, step, packets, True)
    dst_ip = utils.generate_ip_counter_list(dst_ip, step, packets, False)
    size = utils.generate_value_list_with_packet_count([size], packets)
    ipv4.captures_ok(api, b2b_raw_config, size, src_ip, dst_ip)
