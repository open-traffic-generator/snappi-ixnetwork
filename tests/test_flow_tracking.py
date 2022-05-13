import time
import pytest


@pytest.mark.skip(reason="enable after debugging")
def test_flow_tracking_stats(api, utils):
    config = api.config()
    api._enable_flow_tracking(True)
    # ports
    p1, p2, p3, p4 = (
        config.ports.port(name="p1", location=utils.settings.ports[0])
        .port(name="p2", location=utils.settings.ports[1])
        .port(name="p3", location=utils.settings.ports[2])
        .port(name="p4", location=utils.settings.ports[3])
    )
    layer1 = config.layer1.layer1()[-1]
    layer1.port_names = [port.name for port in config.ports]
    layer1.speed = "speed_100_gbps"
    layer1.media = "copper"
    layer1.name = "test"
    d1, d2, d3, d4 = (
        config.devices.device(name="Device1")
        .device(name="Device2")
        .device(name="Device3")
        .device(name="Device4")
    )
    eth1, eth2 = (
        d1.ethernets.add(),
        d2.ethernets.add(),
    )

    eth3, eth4 = (
        d3.ethernets.add(),
        d4.ethernets.add(),
    )
    eth1.port_name, eth2.port_name = p1.name, p2.name
    eth3.port_name, eth4.port_name = p3.name, p4.name

    # device1
    eth1.name = "Eth1"
    eth1.mac = "00:02:00:00:00:11"
    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ip1"
    ip1.address = "10.10.10.1"
    ip1.prefix = 32
    ip1.gateway = "10.10.10.2"

    # device2
    eth2.name = "Eth2"
    eth2.mac = "00:02:00:00:00:12"
    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ip2"
    ip2.address = "10.10.10.2"
    ip2.prefix = 32
    ip2.gateway = "10.10.10.1"

    # device3
    eth3.name = "Eth3"
    eth3.mac = "00:02:00:00:00:13"
    ip3 = eth3.ipv4_addresses.add()
    ip3.name = "ip3"
    ip3.address = "20.20.20.1"
    ip3.prefix = 32
    ip3.gateway = "20.20.20.2"

    # device4
    eth4.name = "Eth4"
    eth4.mac = "00:02:00:00:00:14"
    ipv4 = eth4.ipv4_addresses.add()
    ipv4.name = "ip4"
    ipv4.address = "20.20.20.2"
    ipv4.prefix = 32
    ipv4.gateway = "20.20.20.1"

    # traffic
    config.flows.flow(name="Full Mesh Traffic")
    flow = config.flows[-1]
    flow.metrics.enable = True
    flow.metrics.loss = True
    endpoints = [device.name for device in config.devices]
    flow.tx_rx.device.tx_names = endpoints
    flow.tx_rx.device.rx_names = endpoints
    flow.packet.ethernet().ipv4().udp()
    flow.packet[1]
    flow.size.fixed = 128
    flow.duration.fixed_packets.packets = 10000
    flow.rate.percentage = 1
    api.set_config(config)

    print("Starting all protocols ...")
    ps = api.protocol_state()
    ps.state = ps.START
    api.set_protocol_state(ps)
    time.sleep(5)

    print("Start Traffic ...")
    # start traffic
    ts = api.transmit_state()
    ts.state = ts.START
    api.set_transmit_state(ts)
    # check stats
    time.sleep(5)
    config = api.get_config()
    request = api.metrics_request()
    request.choice = request.FLOW
    results = api.get_metrics(request).flow_metrics
    assert len(results) == 12

    print("Stop all protocols ...")
    ps = api.protocol_state()
    ps.state = ps.STOP
    api.set_protocol_state(ps)
    time.sleep(5)

    print("Stop Traffic ...")
    # start traffic
    ts = api.transmit_state()
    ts.state = ts.STOP
    api.set_transmit_state(ts)


@pytest.mark.skip(reason="run for 8 ports")
def test_flow_tracking_stats_8_ports(api):
    config = api.config()
    api._enable_flow_tracking(True)
    locations = [
        "localuhd/25",
        "localuhd/26",
        "localuhd/27",
        "localuhd/28",
        "localuhd/29",
        "localuhd/30",
        "localuhd/31",
        "localuhd/32",
    ]
    # ports
    for i in range(8):
        config.ports.port(name="p{}".format(i + 1), location=locations[i])
    layer1 = config.layer1.layer1()[-1]
    layer1.port_names = [port.name for port in config.ports]
    layer1.speed = "speed_100_gbps"
    layer1.media = "fiber"
    layer1.name = "test"

    config.options.port_options.location_preemption = True

    ports = [port for port in config.ports]

    for i in range(1, 9, 2):
        d = config.devices.device(name="Device{}".format(i))[-1]
        eth = d.ethernets.add()
        eth.port_name = ports[i - 1].name
        eth.name = "Eth{}".format(i)
        eth.mac = "00:02:00:00:00:1{}".format(i)
        ip = eth.ipv4_addresses.add()
        ip.name = "ip{}".format(i)
        ip.address = "10.10.10.{}".format(i)
        ip.prefix = 32
        ip.gateway = "10.10.10.{}".format(i + 1)

    for i in range(1, 9, 2):
        d = config.devices.device(name="Device{}".format(i + 1))[-1]
        eth = d.ethernets.add()
        eth.port_name = ports[i].name
        eth.name = "Eth{}".format(i + 1)
        eth.mac = "00:02:00:00:00:1{}".format(i + 1)
        ip = eth.ipv4_addresses.add()
        ip.name = "ip{}".format(i + 1)
        ip.address = "10.10.10.{}".format(i + 1)
        ip.prefix = 32
        ip.gateway = "10.10.10.{}".format(i)

    # traffic
    config.flows.flow(name="Full Mesh Traffic")
    flow = config.flows[-1]
    flow.metrics.enable = True
    flow.metrics.loss = True
    endpoints = [device.name for device in config.devices]
    flow.tx_rx.device.tx_names = endpoints
    flow.tx_rx.device.rx_names = endpoints
    flow.packet.ethernet().ipv4().udp()
    flow.packet[1]
    flow.size.fixed = 128
    flow.duration.fixed_packets.packets = 100000
    flow.rate.percentage = 1
    api.set_config(config)

    print("Starting all protocols ...")
    ps = api.protocol_state()
    ps.state = ps.START
    api.set_protocol_state(ps)
    time.sleep(5)

    # start traffic
    ts = api.transmit_state()
    ts.state = ts.START
    api.set_transmit_state(ts)
    while True:
        if check_status(api):
            break
    # check stats
    time.sleep(5)
    config = api.get_config()
    request = api.metrics_request()
    request.choice = request.FLOW
    results = api.get_metrics(request).flow_metrics
    assert len(results) == 56


def check_status(api):
    time.sleep(5)
    fq = api.metrics_request()
    fq.choice = fq.FLOW
    metrics = api.get_metrics(fq).flow_metrics
    print(metrics)
    frames_sent = all([f.frames_tx > 0 for f in metrics])
    all_stopped = all([m.transmit == "stopped" for m in metrics])
    print(frames_sent, all_stopped)
    return frames_sent and all_stopped
