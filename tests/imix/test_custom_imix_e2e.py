import pytest


@pytest.mark.skip(reason="only for dut")
def test_stats_filter_e2e_dut(api, dut, dut_raw_config, utils):
    """
    configure flows with ipv4 imix
    - Send ipv4 imix predefined traffic


    Validation:
    1) Get port statistics based on port name & column names and assert
    each port & column has returned the values and assert
    2) Get flow statistics based on flow name & column names and assert
    each flow & column has returned the values and assert
    """

    dut_channel = dut.connect_dut()
    dut.config_dut(
        "tests/dut_config/cisco_dut.txt",
        dut_channel,
    )

    dut_raw_config.flows.clear()
    config = dut_raw_config

    d1, d2, eth1, eth2, no_of_packets = set_devices_ethernets(config)

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "11.1.1.2"
    ip1.gateway = "11.1.1.1"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    api, config = set_flows_config(api, config, ip1, ip2, no_of_packets)

    utils.start_traffic(api, dut_raw_config)

    utils.wait_for(
        lambda: results_ok(api, utils, no_of_packets),
        "stats to be as expected",
        timeout_seconds=20,
    )
    utils.stop_traffic(api, dut_raw_config)
    captures_ok(
        api, dut_raw_config, utils, no_of_packets, config.ports[1].name
    )

    dut.disconnect_dut(dut_channel)


def test_stats_filter_e2e(api, b2b_raw_config, utils):
    """
    configure flows with ipv4 imix
    - Send ipv4 imix predefined traffic


    Validation:
    1) Get port statistics based on port name & column names and assert
    each port & column has returned the values and assert
    2) Get flow statistics based on flow name & column names and assert
    each flow & column has returned the values and assert
    """

    b2b_raw_config.flows.clear()
    config = b2b_raw_config

    d1, d2, eth1, eth2, no_of_packets = set_devices_ethernets(config)

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    api, config = set_flows_config(api, config, ip1, ip2, no_of_packets)

    utils.start_traffic(api, b2b_raw_config)

    utils.wait_for(
        lambda: results_ok(api, utils, no_of_packets),
        "stats to be as expected",
        timeout_seconds=20,
    )
    utils.stop_traffic(api, b2b_raw_config)
    captures_ok(
        api, b2b_raw_config, utils, no_of_packets, config.ports[1].name
    )


def set_devices_ethernets(config):

    no_of_packets = 1000

    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    return d1, d2, eth1, eth2, no_of_packets


def set_flows_config(api, config, ip1, ip2, no_of_packets):
    sizes_list = [92, 560, 600]
    weights_list = [25.2, 24.8, 50]

    count_weight_pairs = 3
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [ip1.name]
    f1.tx_rx.device.rx_names = [ip2.name]
    for wp_id in range(count_weight_pairs):
        wp = f1.size.weight_pairs.custom.add()
        wp.size = sizes_list[wp_id]
        wp.weight = weights_list[wp_id]

    f1.rate.pps = 1000
    f1.duration.fixed_packets.packets = no_of_packets
    f1.metrics.enable = True
    eth, ip = f1.packet.ethernet().ipv4()
    api.set_config(config)

    return api, config


def results_ok(api, utils, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    print("Checking packet count")
    flow_rx = sum([f.frames_rx for f in flow_results])
    frames_ok = flow_rx == packets
    print("Checking byte count")
    flow_rx = sum([f.bytes_rx for f in flow_results])
    bytes_ok = 300000 <= flow_rx <= 500000

    print("fraemes ok {}".format(frames_ok))
    print("bytes ok {}".format(bytes_ok))
    return frames_ok and bytes_ok


def captures_ok(api, cfg, utils, packets, name):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    pkt_count = 0
    cap_dict = utils.get_all_captures(api, cfg)
    for buf in cap_dict[name]:
        assert len(buf) in [92, 560, 600]
        pkt_count += 1
    assert pkt_count == packets
