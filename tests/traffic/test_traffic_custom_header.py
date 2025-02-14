def test_traffic_custom_header(api, b2b_raw_config, utils):
    """
    Configure the devices on Tx and Rx Port.
    Configure the flow with devices as end points.
    run the traffic
    Validation,
    - validate the port and flow statistics.
    """

    size = 1518
    packets = 100

    flow = b2b_raw_config.flows[0]
    custom = flow.packet.custom()[-1]

    custom.bytes="64"

    metric_tag = custom.metric_tags.add()
    metric_tag.name = "custom metric tag"
    metric_tag.offset = 32
    metric_tag.length = 32


    flow.duration.fixed_packets.packets = packets
    flow.size.fixed = size
    flow.rate.percentage = 10
    flow.metrics.enable = True

    utils.start_traffic(api, b2b_raw_config)

