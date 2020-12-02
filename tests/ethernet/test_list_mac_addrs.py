from abstract_open_traffic_generator import flow
import utils
import eth


def test_fixed_mac_addrs(api, settings, b2b_raw_config):
    """
    Configure a raw ethernet flow with,
    - fixed src and dst MAC address
    - 100 frames of 1518B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst MAC address
    """
    f = b2b_raw_config.flows[0]
    size = 100
    packets = 10
    step = '05:00:00:02:01:00'
    src = utils.generate_mac_counter_list('00:0C:29:E3:53:EA', step, 5, True)
    dst = utils.generate_mac_counter_list('00:0C:29:E3:53:F4', step, 5, True)

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(src),
                dst=flow.Pattern(dst)
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

    src = utils.generate_value_list_with_packet_count(src, packets)
    dst = utils.generate_value_list_with_packet_count(dst, packets)
    size = utils.generate_value_list_with_packet_count([size], packets)
    eth.captures_ok(api, b2b_raw_config, size, src, dst)
