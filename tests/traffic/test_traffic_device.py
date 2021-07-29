def test_traffic(api, b2b_raw_config):
    # import snappi

    # config = snappi.Api().config()
    b2b_raw_config.flows.clear()
    config = b2b_raw_config
    d1, d2 = config.devices.device(name="d1").device(name="d2")

    d1.container_name = config.ports[0].name
    d2.container_name = config.ports[1].name

    d1.ethernet.name = "eth1"
    d1.ethernet.mac = "00:ad:aa:13:11:01"

    d2.ethernet.name = "eth2"
    d2.ethernet.mac = "00:ad:aa:13:11:02"

    d1.ethernet.ipv4.name = "ipv41"
    d1.ethernet.ipv4.address = "10.1.1.1"
    d1.ethernet.ipv4.gateway = "10.1.1.2"

    d2.ethernet.ipv4.name = "ipv42"
    d2.ethernet.ipv4.address = "10.1.1.2"
    d2.ethernet.ipv4.gateway = "10.1.1.1"

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [d1.ethernet.ipv4.name]
    f1.tx_rx.device.rx_names = [d2.ethernet.ipv4.name]
    f1.packet.ethernet().vlan().tcp()
    api.set_config(config)
