import time
import dpkt

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
    flow.payload.choice = "fixed"
    flow.payload.fixed.pattern = "4B6579736967687420546563686E6F6C6F67696573"
    flow.payload.fixed.repeat = True

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=True)
    time.sleep(10)
    utils.stop_traffic(api, b2b_raw_config, stop_capture=True)

    captures_ok(api, b2b_raw_config, packets)

def captures_ok(api, cfg, packets):
    pkt_count = 0

    request = api.capture_request()
    request.port_name = "rx"
    pcap_bytes = api.get_capture(request)

    for _, pkt in dpkt.pcapng.Reader(pcap_bytes):
        eth = dpkt.ethernet.Ethernet(pkt)
        pkt_count += 1
                
    assert pkt_count == packets