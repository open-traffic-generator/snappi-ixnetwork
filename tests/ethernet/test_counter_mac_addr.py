from abstract_open_traffic_generator import flow
from abstract_open_traffic_generator.flow import Counter
import utils
import eth


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
    step = '00:00:00:00:01:00'

    src_mac_list = Counter(
        start=src,
        step=step,
        count=packets
    )

    dst_mac_list = Counter(
        start=dst,
        step=step,
        count=packets,
        up=False
    )

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(src_mac_list),
                dst=flow.Pattern(dst_mac_list)
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

    src = utils.generate_mac_counter_list(src, step, packets, True)
    dst = utils.generate_mac_counter_list(dst, step, packets, False)
    size = utils.generate_value_list_with_packet_count([size], packets)
    eth.captures_ok(api, b2b_raw_config, size, src, dst)
