from snappi_ixnetwork.exceptions import SnappiIxnException


def test_Bad_Request_server_side(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - counter pattern for src and dst MAC address and ether type

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    flow = b2b_raw_config.flows[0]
    count = 10
    src = ["00:0C:29:E3:53:EA"]
    dst = "00:0C:29:E3:53:F4"
    step = "00:00:00:00:01:00"
    eth_step = 2

    flow.packet.ethernet()
    eth = flow.packet[-1]
    eth.src.increment.start = src
    eth.src.increment.step = step
    eth.src.increment.count = count
    eth.dst.decrement.start = dst
    eth.dst.decrement.step = step
    eth.dst.decrement.count = count
    eth.ether_type.increment.step = eth_step
    eth.ether_type.increment.count = count
    try:
        api.set_config(b2b_raw_config)
        assert False
    except SnappiIxnException as err:
        print(err)
        assert err.status_code in [400, 500]
        assert err.args[0] in [400, 500]
        assert isinstance(err.message, list)
        assert isinstance(err.args[1], list)


def test_bad_request_client_side(api):
    config = api.config()
    api.set_config(config)
    config.ports.port(name="port")
    config.ports.port(name="port")
    try:
        api.set_config(config)
        assert False
    except SnappiIxnException as err:
        print(err)
        assert err.status_code == 400
        assert err.args[0] == 400
        assert isinstance(err.message, list)
        assert isinstance(err.args[1], list)


def test_error_list_from_server(api, b2b_raw_config, utils):
    config = api.config()
    api.set_config(config)
    size = 128

    count = 1
    mac_tx = utils.mac_or_ip_addr_from_counter_pattern(
        "00:10:10:20:20:10", "00:00:00:00:00:01", count, True
    )
    mac_rx = utils.mac_or_ip_addr_from_counter_pattern(
        "00:10:10:20:20:20", "00:00:00:00:00:01", count, False
    )
    ip_tx = utils.mac_or_ip_addr_from_counter_pattern(
        "10.1.1.1", "0.0.1.0", count, True, False
    )

    ip_rx = utils.mac_or_ip_addr_from_counter_pattern(
        "10.1.1.2", "0.0.1.0", count, True, False
    )

    addrs = {
        "mac_tx": mac_tx,
        "mac_rx": mac_rx,
        "ip_tx": ip_tx,
        "ip_rx": ip_rx,
    }

    for i in range(count * 2):
        port = int(i / count)
        node = "tx" if port == 0 else "rx"
        if i >= count:
            i = i - count
        dev = b2b_raw_config.devices.add()

        dev.name = "%s_dev_%d" % (node, i + 1)

        eth = dev.ethernets.add()
        eth.name = "%s_eth_%d" % (node, i + 1)
        eth.connection.port_name = b2b_raw_config.ports[port].name
        eth.mac = addrs["mac_%s" % node][i]

        ipv4 = eth.ipv4_addresses.add()
        ipv4.name = "%s_ipv4_%d" % (node, i + 1)
        ipv4.address = addrs["ip_%s" % node][i]
        ipv4.gateway = addrs["ip_%s" % ("rx" if node == "tx" else "tx")][i]
        ipv4.prefix = 24
    f1, f2 = b2b_raw_config.flows.flow(name="TxFlow-2")
    f1.name = "TxFlow-1"
    f1.tx_rx.device.tx_names = [
        b2b_raw_config.devices[i].name for i in range(count)
    ]
    f1.tx_rx.device.rx_names = [
        b2b_raw_config.devices[i].name for i in range(count, count * 2)
    ]
    f1.tx_rx.device.mode = f2.tx_rx.device.ONE_TO_ONE
    f1.size.fixed = size
    # f1.duration.fixed_packets.packets = packets
    f1.rate.percentage = 10

    f2.tx_rx.device.tx_names = [
        b2b_raw_config.devices[i].name for i in range(count)
    ]
    f2.tx_rx.device.rx_names = [
        b2b_raw_config.devices[i].name for i in range(count, count * 2)
    ]
    f2.tx_rx.device.mode = f2.tx_rx.device.ONE_TO_ONE
    f2.packet.ethernet().ipv4().tcp()
    tcp = f2.packet[-1]
    tcp.src_port.increment.start = 5000
    tcp.src_port.increment.step = 1
    tcp.src_port.increment.count = count
    tcp.dst_port.increment.start = 2000
    tcp.dst_port.increment.step = 1
    tcp.dst_port.increment.count = count
    f2.size.fixed = size * 2
    # f2.duration.fixed_packets.packets = packets
    f2.rate.percentage = 10
    api.set_config(b2b_raw_config)
    try:
        utils.get_all_stats(api)
        assert False
    except Exception as e:
        print(e)
        assert e.args[0] == 500
        assert isinstance(e.args[1], list)
