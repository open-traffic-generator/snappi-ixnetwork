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
    p1, p2, p3, p4 = (
        config.ports.port(name="txp1", location=utils.settings.ports[0])
        .port(name="txp2", location=utils.settings.ports[1])
        .port(name="rxp1", location=utils.settings.ports[2])
        .port(name="rxp2", location=utils.settings.ports[3])
    )

    config.layer1.layer1(
        name="layer1",
        port_names=[p.name for p in config.ports],
        speed=utils.settings.speed,
        media=utils.settings.media,
    )

    lag1, lag2 = config.lags.lag(name="lag1").lag(name="lag2")
    lp1, lp2 = lag1.ports.port(port_name=p1.name).port(port_name=p2.name)
    lp3, lp4 = lag2.ports.port(port_name=p3.name).port(port_name=p4.name)

    lag1.protocol.static.lag_id = 1
    lag2.protocol.static.lag_id = 2

    lp1.ethernet.name, lp2.ethernet.name = "eth1", "eth2"
    lp3.ethernet.name, lp4.ethernet.name = "eth3", "eth4"

    lp1.ethernet.mac = "00:11:02:00:00:01"
    lp2.ethernet.mac = "00:22:02:00:00:01"
    lp3.ethernet.mac = "00:33:02:00:00:01"
    lp4.ethernet.mac = "00:44:02:00:00:01"

    lp1.ethernet.vlans.vlan(priority=1, name="vlan1", id=1)[-1]
    lp2.ethernet.vlans.vlan(priority=1, name="vlan2", id=1)[-1]
    lp3.ethernet.vlans.vlan(priority=1, name="vlan3", id=1)[-1]
    lp4.ethernet.vlans.vlan(priority=1, name="vlan4", id=1)[-1]

    packets = 2000
    f1_size = 74
    f2_size = 1500
    d1, d2 = config.devices.device(name="device1").device(name="device2")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = lag1.name, lag2.name
    eth1.name, eth2.name = "d_eth1", "d_eth2"
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"
    f1, f2 = config.flows.flow(name="f1").flow(name="f2")
    f1.tx_rx.port.tx_name, f1.tx_rx.port.rx_name = p1.name, p2.name
    f2.tx_rx.port.tx_name, f2.tx_rx.port.rx_name = p3.name, p4.name
    config.options.port_options.location_preemption = True
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
        lambda: utils.is_stats_accumulated(api, packets * 2),
        "stats to be accumulated",
    )

    utils.wait_for(
        lambda: results_ok(api, utils, f1_size, f2_size, packets),
        "stats to be as expected",
        timeout_seconds=30,
    )


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
    LAG1_ATTR = {
        "ActorSystemId": ["00 11 03 00 00 03", "00 11 03 00 00 03"],
        "ActorSystemPriority": ["1", "1"],
        "ActorKey": ["10", "10"],
        "ActorPortNumber": ["30", "40"],
        "ActorPortPriority": ["100", "101"],
        "LacpActivity": ["active", "active"],
        "LacpduPeriodicTimeInterval": ["5", "6"],
        "LacpduTimeout": ["12", "13"],
    }

    LAG2_ATTR = {
        "ActorSystemId": ["00 22 03 00 00 03", "00 22 03 00 00 03"],
        "ActorSystemPriority": ["2", "2"],
        "ActorKey": ["20", "20"],
        "ActorPortNumber": ["50", "60"],
        "ActorPortPriority": ["200", "201"],
        "LacpActivity": ["active", "active"],
        "LacpduPeriodicTimeInterval": ["7", "8"],
        "LacpduTimeout": ["14", "15"],
    }
    config = api.config()
    p1, p2, p3, p4 = (
        config.ports.port(name="txp1", location=utils.settings.ports[0])
        .port(name="txp2", location=utils.settings.ports[2])
        .port(name="rxp1", location=utils.settings.ports[1])
        .port(name="rxp2", location=utils.settings.ports[3])
    )

    config.layer1.layer1(
        name="layer1",
        port_names=[p.name for p in config.ports],
        speed=utils.settings.speed,
        media=utils.settings.media,
    )

    lag1, lag2 = config.lags.lag(name="lag1").lag(name="lag2")
    l1_p1, l1_p2 = lag1.ports.port(port_name=p1.name).port(port_name=p2.name)
    l2_p1, l2_p2 = lag2.ports.port(port_name=p3.name).port(port_name=p4.name)
    config.options.port_options.location_preemption = True

    lag1.protocol.lacp.actor_system_id = "00:11:03:00:00:03"
    lag1.protocol.lacp.actor_system_priority = int(
        LAG1_ATTR["ActorSystemPriority"][0]
    )
    lag1.protocol.lacp.actor_key = int(LAG1_ATTR["ActorKey"][0])

    lag2.protocol.lacp.actor_system_id = "00:22:03:00:00:03"
    lag2.protocol.lacp.actor_system_priority = int(
        LAG2_ATTR["ActorSystemPriority"][0]
    )
    lag2.protocol.lacp.actor_key = int(LAG2_ATTR["ActorKey"][0])

    l1_p1.lacp.actor_port_number = int(LAG1_ATTR["ActorPortNumber"][0])
    l1_p2.lacp.actor_port_number = int(LAG1_ATTR["ActorPortNumber"][1])
    l2_p1.lacp.actor_port_number = int(LAG2_ATTR["ActorPortNumber"][0])
    l2_p2.lacp.actor_port_number = int(LAG2_ATTR["ActorPortNumber"][1])

    l1_p1.lacp.actor_port_priority = int(LAG1_ATTR["ActorPortPriority"][0])
    l1_p2.lacp.actor_port_priority = int(LAG1_ATTR["ActorPortPriority"][1])
    l2_p1.lacp.actor_port_priority = int(LAG2_ATTR["ActorPortPriority"][0])
    l2_p2.lacp.actor_port_priority = int(LAG2_ATTR["ActorPortPriority"][1])

    l1_p1.lacp.actor_activity = LAG1_ATTR["LacpActivity"][0]
    l1_p2.lacp.actor_activity = LAG1_ATTR["LacpActivity"][1]
    l2_p1.lacp.actor_activity = LAG2_ATTR["LacpActivity"][0]
    l2_p2.lacp.actor_activity = LAG2_ATTR["LacpActivity"][1]

    l1_p1.lacp.lacpdu_periodic_time_interval = int(
        LAG1_ATTR["LacpduPeriodicTimeInterval"][0]
    )
    l1_p2.lacp.lacpdu_periodic_time_interval = int(
        LAG1_ATTR["LacpduPeriodicTimeInterval"][1]
    )
    l2_p1.lacp.lacpdu_periodic_time_interval = int(
        LAG2_ATTR["LacpduPeriodicTimeInterval"][0]
    )
    l2_p2.lacp.lacpdu_periodic_time_interval = int(
        LAG2_ATTR["LacpduPeriodicTimeInterval"][1]
    )

    l1_p1.lacp.lacpdu_timeout = int(LAG1_ATTR["LacpduTimeout"][0])
    l1_p2.lacp.lacpdu_timeout = int(LAG1_ATTR["LacpduTimeout"][1])
    l2_p1.lacp.lacpdu_timeout = int(LAG2_ATTR["LacpduTimeout"][0])
    l2_p2.lacp.lacpdu_timeout = int(LAG2_ATTR["LacpduTimeout"][1])

    l1_p1.ethernet.name, l1_p2.ethernet.name = "eth1", "eth2"
    l2_p1.ethernet.name, l2_p2.ethernet.name = "eth3", "eth4"

    l1_p1.ethernet.mac = "00:11:02:00:00:01"
    l1_p2.ethernet.mac = "00:22:02:00:00:01"
    l2_p1.ethernet.mac = "00:33:02:00:00:01"
    l2_p2.ethernet.mac = "00:44:02:00:00:01"

    l1_p1.ethernet.vlans.vlan(priority=1, name="vlan1", id=1)[-1]
    l1_p2.ethernet.vlans.vlan(priority=1, name="vlan2", id=1)[-1]
    l2_p1.ethernet.vlans.vlan(priority=1, name="vlan3", id=1)[-1]
    l2_p2.ethernet.vlans.vlan(priority=1, name="vlan4", id=1)[-1]

    d1, d2 = config.devices.device(name="device1").device(name="device2")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = lag1.name, lag2.name
    eth1.name, eth2.name = "d_eth1", "d_eth2"
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    api.set_config(config)

    utils.wait_for(
        lambda: lacp_pdu_status_ok(api, "up"), "port state as expected"
    )

    cs = api.control_state()
    cs.protocol.lacp.member_ports.lag_member_names = ["rxp2"]
    cs.protocol.lacp.member_ports.state = cs.protocol.lacp.member_ports.DOWN
    api.set_control_state(cs)

    utils.wait_for(
        lambda: lacp_pdu_status_ok(api, "down"), "port state as expected"
    )

    cs = api.control_state()
    cs.protocol.lacp.member_ports.lag_member_names = ["rxp2"]
    cs.protocol.lacp.member_ports.state = cs.protocol.lacp.member_ports.UP
    api.set_control_state(cs)

    utils.wait_for(
        lambda: lacp_pdu_status_ok(api, "up"), "port state as expected"
    )

    validate_lacp_config(api, LAG1_ATTR, LAG2_ATTR)


def lacp_pdu_status_ok(api, state):
    return (
        api._ixnetwork.Lag.find()
        .ProtocolStack.find()
        .Ethernet.find()
        .Lagportlacp.find()
        .SessionStatus
    )[1] == state


def validate_lacp_config(api, LAG1_ATTR, LAG2_ATTR):
    lags = api._ixnetwork.Lag.find()

    for lag in lags:
        assert lag.LagMode.LagProtocol == "lacp"

    lag1 = lags[0].ProtocolStack.find().Ethernet.find().Lagportlacp.find()
    for attr in LAG1_ATTR:
        assert getattr(lag1, attr).Values == LAG1_ATTR[attr]

    lag2 = lags[1].ProtocolStack.find().Ethernet.find().Lagportlacp.find()
    for attr in LAG2_ATTR:
        assert getattr(lag2, attr).Values == LAG2_ATTR[attr]


def test_static_and_lacp_lag(api, utils):
    LACP_ATTR = {
        "ActorSystemId": ["00 22 03 00 00 03", "00 22 03 00 00 03"],
        "ActorSystemPriority": ["1", "1"],
        "ActorKey": ["10", "10"],
        "ActorPortNumber": ["30", "40"],
        "ActorPortPriority": ["100", "101"],
        "LacpActivity": ["active", "passive"],
        "LacpduPeriodicTimeInterval": ["5", "6"],
        "LacpduTimeout": ["12", "13"],
    }

    config = api.config()
    p1, p2, p3, p4 = (
        config.ports.port(name="txp1", location=utils.settings.ports[0])
        .port(name="txp2", location=utils.settings.ports[2])
        .port(name="rxp1", location=utils.settings.ports[1])
        .port(name="rxp2", location=utils.settings.ports[3])
    )

    config.layer1.layer1(
        name="layer1",
        port_names=[p.name for p in config.ports],
        speed=utils.settings.speed,
        media=utils.settings.media,
    )

    lag1, lag2 = config.lags.lag(name="lag1").lag(name="lag2")
    l1_p1, l1_p2 = lag1.ports.port(port_name=p1.name).port(port_name=p2.name)
    l2_p1, l2_p2 = lag2.ports.port(port_name=p3.name).port(port_name=p4.name)
    config.options.port_options.location_preemption = True

    lag1.protocol.static.lag_id = 5

    lag2.protocol.lacp.actor_system_id = "00:22:03:00:00:03"
    lag2.protocol.lacp.actor_system_priority = int(
        LACP_ATTR["ActorSystemPriority"][0]
    )
    lag2.protocol.lacp.actor_key = int(LACP_ATTR["ActorKey"][0])

    l2_p1.lacp.actor_port_number = int(LACP_ATTR["ActorPortNumber"][0])
    l2_p2.lacp.actor_port_number = int(LACP_ATTR["ActorPortNumber"][1])

    l2_p1.lacp.actor_port_priority = int(LACP_ATTR["ActorPortPriority"][0])
    l2_p2.lacp.actor_port_priority = int(LACP_ATTR["ActorPortPriority"][1])

    l2_p1.lacp.actor_activity = LACP_ATTR["LacpActivity"][0]
    l2_p2.lacp.actor_activity = LACP_ATTR["LacpActivity"][1]

    l2_p1.lacp.lacpdu_periodic_time_interval = int(
        LACP_ATTR["LacpduPeriodicTimeInterval"][0]
    )
    l2_p2.lacp.lacpdu_periodic_time_interval = int(
        LACP_ATTR["LacpduPeriodicTimeInterval"][1]
    )

    l2_p1.lacp.lacpdu_timeout = int(LACP_ATTR["LacpduTimeout"][0])
    l2_p2.lacp.lacpdu_timeout = int(LACP_ATTR["LacpduTimeout"][1])

    l1_p1.ethernet.name, l1_p2.ethernet.name = "eth1", "eth2"
    l2_p1.ethernet.name, l2_p2.ethernet.name = "eth3", "eth4"

    l1_p1.ethernet.mac = "00:11:02:00:00:01"
    l1_p2.ethernet.mac = "00:22:02:00:00:01"
    l2_p1.ethernet.mac = "00:33:02:00:00:01"
    l2_p2.ethernet.mac = "00:44:02:00:00:01"

    l1_p1.ethernet.vlans.vlan(priority=1, name="vlan1", id=1)[-1]
    l1_p2.ethernet.vlans.vlan(priority=1, name="vlan2", id=1)[-1]
    l2_p1.ethernet.vlans.vlan(priority=1, name="vlan3", id=1)[-1]
    l2_p2.ethernet.vlans.vlan(priority=1, name="vlan4", id=1)[-1]

    packets = 2000
    f1_size = 74
    f2_size = 1500
    d1, d2 = config.devices.device(name="device1").device(name="device2")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = lag1.name, lag2.name
    eth1.name, eth2.name = "d_eth1", "d_eth2"
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip1.name, ip2.name = "ip1", "ip2"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"
    f1, f2 = config.flows.flow(name="f1").flow(name="f2")
    f1.tx_rx.port.tx_name, f1.tx_rx.port.rx_name = p1.name, p2.name
    f2.tx_rx.port.tx_name, f2.tx_rx.port.rx_name = p3.name, p4.name
    f1.duration.fixed_packets.packets = packets
    f2.duration.fixed_packets.packets = packets
    f1.size.fixed = f1_size
    f2.size.fixed = f2_size
    f1.rate.percentage = 10
    f2.rate.percentage = 10

    api.set_config(config)
    validate_static_lacp_config(api, LACP_ATTR)


def validate_static_lacp_config(api, LACP_ATTR):
    lags = api._ixnetwork.Lag.find()

    assert (
        lags[0]
        .ProtocolStack.find()
        .Ethernet.find()
        .Lagportstaticlag.find()
        .LagId.Values
    )[0] == "5"
    assert lags[1].LagMode.LagProtocol == "lacp"

    lag_lacp = lags[1].ProtocolStack.find().Ethernet.find().Lagportlacp.find()
    for attr in LACP_ATTR:
        assert getattr(lag_lacp, attr).Values == LACP_ATTR[attr]


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


if __name__ == "__main__":
    pytest.main(["-s", __file__])
