def test_bidir_tagged_flows(api, utils):
    """Test bidirectional VLAN tagged flows

    1) Create 2 devices, each device has an interface and tag the traffic with VLAN 100
    2) Create 2 flows, each flow sends traffic from one device to the other
    3) Start the traffic and capture
    """
    config = api.config()
    p1, p2 = config.ports.port(name="tx", location=utils.settings.ports[0]).port(
        name="rx", location=utils.settings.ports[1]
    )

    config.layer1.layer1(
        name="layer1",
        port_names=[p.name for p in config.ports],
        speed=utils.settings.speed,
        media=utils.settings.media,
    )

    d1, d2 = config.devices.device(name="device1").device(name="device2")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.name, eth2.name = "eth1", "eth2"
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"

    eth1.vlans.vlan(priority=1, name="d1_vlan100", id=100)
    eth2.vlans.vlan(priority=1, name="d2_vlan100", id=100)

    packets = 2000
    f1_size = 74
    f2_size = 1500
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"
    f1, f2 = config.flows.flow(name="f1").flow(name="f2")
    f1.tx_rx.device.tx_names, f1.tx_rx.device.rx_names = [d1.name], [d2.name]
    f2.tx_rx.device.tx_names, f2.tx_rx.device.rx_names = [d2.name], [d1.name]
    f1.tx_rx.device.mode, f2.tx_rx.device.mode = "one_to_one", "one_to_one"
    f1.duration.fixed_packets.packets = packets
    f2.duration.fixed_packets.packets = packets
    f1.size.fixed = f1_size
    f2.size.fixed = f2_size
    f1.rate.percentage = 10
    f2.rate.percentage = 10

    f1.metrics.enable = True
    f1.metrics.loss = True

    f2.metrics.enable = True
    f2.metrics.loss = True

    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(lambda: utils.is_traffic_stopped(api), "traffic to stop")

    utils.wait_for(
        lambda: is_stats_accumulated(api, packets, utils),
        "stats to be accumulated",
    )

    utils.wait_for(
        lambda: results_ok(api, utils, f1_size, f2_size, packets),
        "stats to be as expected",
        timeout_seconds=30,
    )


def results_ok(api, utils, size1, size2, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = total_frames_ok(port_results, flow_results, packets * 2)
    bytes_ok = total_bytes_ok(
        port_results, flow_results, packets * size1 + packets * size2
    )
    return frames_ok and bytes_ok


def is_stats_accumulated(api, packets, utils):
    """
    Returns true if stats gets accumulated
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = total_frames_ok(port_results, flow_results, packets * 2)
    return frames_ok


def total_frames_ok(port_results, flow_results, expected):
    """Redefining utils.total_frames_ok() since port_rx could be greater than expected
    if the network sends extra frames (LLDP, STP...)"""
    port_tx = sum([p.frames_tx for p in port_results])
    port_rx = sum([p.frames_rx for p in port_results])
    flow_rx = sum([f.frames_rx for f in flow_results])

    return (port_tx == flow_rx == expected) and port_rx > expected

def total_bytes_ok(port_results, flow_results, expected):
    """Redefining utils.total_bytes_ok() since port_rx could be greater than expected
    if the network sends extra frames (LLDP, STP...)"""
    port_tx = sum([p.bytes_tx for p in port_results])
    port_rx = sum([p.bytes_rx for p in port_results])
    flow_rx = sum([f.bytes_rx for f in flow_results])

    return (port_tx == flow_rx == expected) and port_rx > expected