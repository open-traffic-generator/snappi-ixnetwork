import time
import pytest


def wait_for_arp(snappi_api, max_attempts=10, poll_interval_sec=1):
    """
    Args:
    snappi_api: snappi api
    max_attempts: maximum attempts for timeout
    poll_interval_sec: interval poll second
    Return:
    returns number of attempts if arp is resolved within max attempts else fail
    """
    attempts = 0
    v4_gateway_macs_resolved = False
    v6_gateway_macs_resolved = False

    get_config = snappi_api.get_config()
    v4_addresses = []
    v6_addresses = []

    for device in get_config.devices:
        for ethernet in device.ethernets:
            for v4_address in ethernet.ipv4_addresses:
                v4_addresses.append(v4_address.address)
            for v6_address in ethernet.ipv6_addresses:
                v6_addresses.append(v6_address.address)

    while attempts < max_attempts:
        request = snappi_api.states_request()
        request.choice = request.IPV4_NEIGHBORS
        states = snappi_api.get_states(request)

        if len(v4_addresses) > 0:
            v4_link_layer_address = [
                state.link_layer_address
                for state in states.ipv4_neighbors
                if state.link_layer_address is not None
            ]
            if len(v4_addresses) == len(v4_link_layer_address):
                v4_gateway_macs_resolved = True
        else:
            v4_gateway_macs_resolved = True

        request = snappi_api.states_request()
        request.choice = request.IPV6_NEIGHBORS
        states = snappi_api.get_states(request)

        if len(v6_addresses) > 0:
            v6_link_layer_address = [
                state.link_layer_address
                for state in states.ipv6_neighbors
                if state.link_layer_address is not None
            ]
            if len(v6_addresses) == len(v6_link_layer_address):
                v6_gateway_macs_resolved = True
        else:
            v6_gateway_macs_resolved = True

        if v4_gateway_macs_resolved and v6_gateway_macs_resolved:
            break
        else:
            time.sleep(poll_interval_sec)
            attempts += 1

    print("Attempts: ", attempts)
    print("Maxmimum Attempts:", max_attempts)
    if attempts >= max_attempts:
        import pdb

        pdb.set_trace()
        raise Exception(
            "ARP is not resolved in {} seconds".format(
                max_attempts * poll_interval_sec
            )
        )

    return attempts


def static_lag(api, utils):
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
    p1, p2 = config.ports.port(
        name="txp1", location=utils.settings.ports[0]
    ).port(name="rxp2", location=utils.settings.ports[1])

    config.layer1.layer1(
        name="layer1",
        port_names=[p.name for p in config.ports],
        speed=utils.settings.speed,
        media=utils.settings.media,
    )

    lag1, lag2 = config.lags.lag(name="lag1").lag(name="lag2")
    lp1 = lag1.ports.port(port_name=p1.name)[-1]
    lp2 = lag2.ports.port(port_name=p2.name)[-1]
    lag1.protocol.static.lag_id = 1
    lag2.protocol.static.lag_id = 2

    lp1.ethernet.name, lp2.ethernet.name = "eth1", "eth2"

    lp1.ethernet.mac = "00:11:02:00:00:01"
    lp2.ethernet.mac = "00:22:02:00:00:01"

    lp1.ethernet.vlans.vlan(priority=1, name="vlan1", id=1)[-1]
    lp2.ethernet.vlans.vlan(priority=1, name="vlan2", id=1)[-1]

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
    f1.tx_rx.port.tx_name = p1.name
    f1.tx_rx.port.rx_name = p2.name
    f2.tx_rx.port.rx_name = p1.name
    f2.tx_rx.port.tx_name = p2.name
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

    api.set_config(config)

    wait_for_arp(api, max_attempts=10, poll_interval_sec=2)

    print("Starting transmit on all flows ...")
    cs = api.control_state()
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    api.set_control_state(cs)

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

@pytest.mark.skip(reason="skip to CICD faster")
def test_static_lag(api, utils):
    for i in range(0, 4):
        static_lag(api, utils)
    # test1(api, utils)
    # test2(api, utils)
