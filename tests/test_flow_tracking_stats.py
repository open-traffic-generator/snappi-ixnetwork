import time


def test_flow_tracking_stats(api, utils):
    config = api.config()
    api._enable_flow_tracking(True)
    # ports
    config.ports.port(name="p1", location=utils.settings.ports[0])
    config.ports.port(name="p2", location=utils.settings.ports[1])
    config.ports.port(name="p3", location=utils.settings.ports[2])
    config.ports.port(name="p4", location=utils.settings.ports[3])
    layer1 = config.layer1.layer1()[-1]
    layer1.port_names = [port.name for port in config.ports]
    layer1.speed = "speed_100_gbps"
    layer1.media = "copper"
    layer1.name = "test"
    d1, d2, d3, d4 = (
        config.devices.device(container_name="p1", name="Device1")
        .device(container_name="p2", name="Device2")
        .device(container_name="p3", name="Device3")
        .device(container_name="p4", name="Device4")
    )
    # device1
    d1.ethernet.name = "Eth1"
    d1.ethernet.mac = "00:02:00:00:00:11"
    d1.ethernet.ipv4.name = "IPv41"
    d1.ethernet.ipv4.address = "10.10.10.1"
    d1.ethernet.ipv4.prefix = 32
    d1.ethernet.ipv4.gateway = "10.10.10.2"
    # device2
    d2.ethernet.name = "Eth2"
    d2.ethernet.mac = "00:02:00:00:00:12"
    d2.ethernet.ipv4.name = "IPv42"
    d2.ethernet.ipv4.address = "10.10.10.2"
    d2.ethernet.ipv4.prefix = 32
    d2.ethernet.ipv4.gateway = "10.10.10.1"
    # device3
    d3.ethernet.name = "Eth3"
    d3.ethernet.mac = "00:02:00:00:00:13"
    d3.ethernet.ipv4.name = "IPv43"
    d3.ethernet.ipv4.address = "20.20.20.1"
    d3.ethernet.ipv4.prefix = 32
    d3.ethernet.ipv4.gateway = "20.20.20.2"
    # device4
    d4.ethernet.name = "Eth4"
    d4.ethernet.mac = "00:02:00:00:00:14"
    d4.ethernet.ipv4.name = "IPv44"
    d4.ethernet.ipv4.address = "20.20.20.2"
    d4.ethernet.ipv4.prefix = 32
    d4.ethernet.ipv4.gateway = "20.20.20.1"

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
