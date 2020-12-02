from abstract_open_traffic_generator import flow
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
    source = '00:0C:29:E3:53:EA'
    destination = '00:0C:29:E3:53:F4'

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(source),
                dst=flow.Pattern(destination)
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

    source = utils.generate_value_list_with_packet_count([source], packets)
    destination = utils.generate_value_list_with_packet_count(
        [destination], packets
    )
    size = utils.generate_value_list_with_packet_count([size], packets)
    eth.captures_ok(api, b2b_raw_config, size, source, destination)
