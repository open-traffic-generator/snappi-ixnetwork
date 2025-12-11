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

    b2b_raw_config.flows.clear()
    config = b2b_raw_config

    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    flow = b2b_raw_config.flows.flow(name="f1")[-1]
    flow.tx_rx.device.tx_names = [ip1.name]
    flow.tx_rx.device.rx_names = [ip2.name]
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

    captures_ok(api, b2b_raw_config, packets, config.ports[1].name)

def captures_ok(api, cfg, packets, name):
    pkt_count = 0

    request = api.capture_request()
    request.port_name = name
    pcap_bytes = api.get_capture(request)

    for _, pkt in dpkt.pcapng.Reader(pcap_bytes):
        eth = dpkt.ethernet.Ethernet(pkt)
        if isinstance(eth.data, dpkt.ip.IP):
            ip = eth.data
            pkt_count += 1
                
    assert pkt_count == packets