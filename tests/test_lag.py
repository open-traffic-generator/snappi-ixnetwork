import pytest


def test_static_lag(api, utils):
    """Demonstrates the following:
    1) Creating a lag comprised of multiple ports
    2) Creating emulated devices over the lag
    3) Creating traffic over the emulated devices that will transmit
    traffic to a single rx port.

        TX LAG              DUT             RX
        ------+         +---------+
        port 1|         |
        ..    | ------> |
        port n|         |
        ------+
    """
    config = api.config()
    api.set_config(config)
    p1, p2, p3, p4 = (
        config.ports
        .port(name='txp1', location=utils.settings.ports[0])
        .port(name='txp2', location=utils.settings.ports[1])
        .port(name='rxp1', location=utils.settings.ports[2])
        .port(name='rxp2', location=utils.settings.ports[3])
    )

    config.layer1.layer1(
        name='layer1', port_names=[p.name for p in config.ports],
        speed=utils.settings.speed, media=utils.settings.media
    )

    lag1, lag2 = config.lags.lag(name='lag1').lag(name='lag2')
    lp1, lp2 = lag1.ports.port(port_name=p1.name).port(port_name=p2.name)
    lp3, lp4 = lag2.ports.port(port_name=p3.name).port(port_name=p4.name)
    lp1.protocol.static.lag_id = 1
    lp2.protocol.static.lag_id = 1
    lp3.protocol.static.lag_id = 2
    lp4.protocol.static.lag_id = 2

    lp1.ethernet.name, lp2.ethernet.name = 'eth1', 'eth2'
    lp3.ethernet.name, lp4.ethernet.name = 'eth3', 'eth4'

    lp1.ethernet.mac = '00:11:02:00:00:01'
    lp2.ethernet.mac = '00:22:02:00:00:01'
    lp3.ethernet.mac = '00:33:02:00:00:01'
    lp4.ethernet.mac = '00:44:02:00:00:01'

    lp1.ethernet.vlans.vlan(priority=1, name='vlan1', id=1)[-1]
    lp2.ethernet.vlans.vlan(priority=1, name='vlan2', id=1)[-1]
    lp3.ethernet.vlans.vlan(priority=1, name='vlan3', id=1)[-1]
    lp4.ethernet.vlans.vlan(priority=1, name='vlan4', id=1)[-1]

    packets = 2000
    f1_size = 74
    f2_size = 1500
    d1, d2 = config.devices.device(name='device1').device(name='device2')
    d1.container_name = lag1.name
    d2.container_name = lag2.name
    d1.ethernet.name, d2.ethernet.name = 'd_eth1', 'd_eth2'
    d1.ethernet.mac, d2.ethernet.mac = '00:00:00:00:00:11', '00:00:00:00:00:22'
    ip1, ip2 = d1.ethernet.ipv4, d2.ethernet.ipv4
    ip1.name, ip2.name = 'ip1', 'ip2'
    ip1.address = '10.1.1.1'
    ip1.gateway = '10.1.1.2'
    ip2.address = '10.1.1.2'
    ip2.gateway = '10.1.1.1'
    f1, f2 = config.flows.flow(name='f1').flow(name='f2')
    f1.tx_rx.port.tx_name, f1.tx_rx.port.rx_name = p1.name, p2.name
    f2.tx_rx.port.tx_name, f2.tx_rx.port.rx_name = p3.name, p4.name
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
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )

    utils.wait_for(
        lambda: utils.is_stats_accumulated(api, packets * 2),
        'stats to be accumulated'
    )

    utils.wait_for(
        lambda: results_ok(
            api, utils, f1_size, f2_size, packets
        ),
        'stats to be as expected', timeout_seconds=30
    )


@pytest.mark.skip(reason="revisit CI/CD fail")
def test_lacp_lag(api, utils):
    """Demonstrates the following:
    1) Creating a lag comprised of multiple ports
    2) Creating emulated devices over the lag
    3) Creating traffic over the emulated devices that will transmit
    traffic to a single rx port.

        TX LAG              DUT             RX
        ------+         +---------+
        port 1|         |
        ..    | ------> |
        port n|         |
        ------+
    """
    config = api.config()
    api.set_config(config)
    p1, p2, p3, p4 = (
        config.ports
        .port(name='txp1', location=utils.settings.ports[0])
        .port(name='txp2', location=utils.settings.ports[1])
        .port(name='rxp1', location=utils.settings.ports[2])
        .port(name='rxp2', location=utils.settings.ports[3])
    )

    config.layer1.layer1(
        name='layer1', port_names=[p.name for p in config.ports],
        speed=utils.settings.speed, media=utils.settings.media
    )

    lag1, lag2 = config.lags.lag(name='lag1').lag(name='lag2')
    lp1, lp2 = lag1.ports.port(port_name=p1.name).port(port_name=p2.name)
    lp3, lp4 = lag2.ports.port(port_name=p3.name).port(port_name=p4.name)
    lp1.protocol.lacp.actor_system_id = '00:11:03:00:00:03'
    lp2.protocol.lacp.actor_system_id = '00:11:03:00:00:03'
    lp3.protocol.lacp.actor_system_id = '00:22:03:00:00:03'
    lp4.protocol.lacp.actor_system_id = '00:22:03:00:00:03'

    lp1.ethernet.name, lp2.ethernet.name = 'eth1', 'eth2'
    lp3.ethernet.name, lp4.ethernet.name = 'eth3', 'eth4'

    lp1.ethernet.mac = '00:11:02:00:00:01'
    lp2.ethernet.mac = '00:22:02:00:00:01'
    lp3.ethernet.mac = '00:33:02:00:00:01'
    lp4.ethernet.mac = '00:44:02:00:00:01'

    lp1.ethernet.vlans.vlan(priority=1, name='vlan1', id=1)[-1]
    lp2.ethernet.vlans.vlan(priority=1, name='vlan2', id=1)[-1]
    lp3.ethernet.vlans.vlan(priority=1, name='vlan3', id=1)[-1]
    lp4.ethernet.vlans.vlan(priority=1, name='vlan4', id=1)[-1]

    packets = 2000
    f1_size = 74
    f2_size = 1500
    d1, d2 = config.devices.device(name='device1').device(name='device2')
    d1.container_name = lag1.name
    d2.container_name = lag2.name
    ip1, ip2 = d1.ethernet.ipv4, d2.ethernet.ipv4
    ip1.address = '10.1.1.1'
    ip1.gateway = '10.1.1.2'
    ip2.address = '10.1.1.2'
    ip2.gateway = '10.1.1.1'
    f1, f2 = config.flows.flow(name='f1').flow(name='f2')
    f1.tx_rx.port.tx_name, f1.tx_rx.port.rx_name = p1.name, p2.name
    f2.tx_rx.port.tx_name, f2.tx_rx.port.rx_name = p3.name, p4.name
    f1.duration.fixed_packets.packets = packets
    f2.duration.fixed_packets.packets = packets
    f1.size.fixed = f1_size
    f2.size.fixed = f2_size
    f1.rate.percentage = 10
    f2.rate.percentage = 10

    utils.start_traffic(api, config, start_capture=False)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )

    utils.wait_for(
        lambda: utils.is_stats_accumulated(api, packets * 2),
        'stats to be accumulated'
    )

    utils.wait_for(
        lambda: results_ok(
            api, utils, f1_size, f2_size, packets
        ),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, utils, size1, size2, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets * 2)
    bytes_ok = utils.total_bytes_ok(
        port_results, flow_results, packets * size1 + packets * size2
    )
    return frames_ok and bytes_ok
