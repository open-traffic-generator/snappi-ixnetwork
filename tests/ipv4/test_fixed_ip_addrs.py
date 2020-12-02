from abstract_open_traffic_generator import flow
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
    f.duration = flow.Duration(flow.FixedPackets(packets=packets))
    f.size = flow.Size(size)
    f.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: utils.stats_ok(api, size, packets), 'stats to be as expected'
    )

    src_ip = utils.generate_value_list_with_packet_count([src_ip], packets)
    dst_ip = utils.generate_value_list_with_packet_count([dst_ip], packets)
    size = utils.generate_value_list_with_packet_count([size], packets)
    ipv4.captures_ok(api, b2b_raw_config, size, src_ip, dst_ip)
