import pytest

@pytest.fixture()
def bgp_convergence_config(utils, api):
    """
    1.Configure IPv4 EBGP sessions between Keysight ports(rx & tx)
    2.Configure and advertise IPv4 routes from rx
    """

    conv_config = api.config()

    tx, rx = conv_config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    conv_config.options.port_options.location_preemption = True
    ly = conv_config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [tx.name, rx.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    tx_device, rx_device = conv_config.devices.device(name="tx_device").device(
        name="rx_device"
    )

    # tx_device config
    tx_eth = tx_device.ethernets.add()
    tx_eth.connection.port_name = tx.name
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:00:00:00:00:aa"
    tx_ipv4 = tx_eth.ipv4_addresses.add()
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address = "21.1.1.2"
    tx_ipv4.prefix = 24
    tx_ipv4.gateway = "21.1.1.1"
    tx_bgpv4 = tx_device.bgp
    tx_bgpv4.router_id = "192.0.0.1"
    tx_bgpv4_int = tx_bgpv4.ipv4_interfaces.add()
    tx_bgpv4_int.ipv4_name = tx_ipv4.name
    tx_bgpv4_peer = tx_bgpv4_int.peers.add()
    tx_bgpv4_peer.name = "tx_bgpv4"
    tx_bgpv4_peer.as_type = "ebgp"
    tx_bgpv4_peer.peer_address = "21.1.1.1"
    tx_bgpv4_peer.as_number = 65201

    # rx_device config
    rx_eth = rx_device.ethernets.add()
    rx_eth.connection.port_name = rx.name
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv4 = rx_eth.ipv4_addresses.add()
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address = "21.1.1.1"
    rx_ipv4.prefix = 24
    rx_ipv4.gateway = "21.1.1.2"
    rx_bgpv4 = rx_device.bgp
    rx_bgpv4.router_id = "192.0.0.2"
    rx_bgpv4_int = rx_bgpv4.ipv4_interfaces.add()
    rx_bgpv4_int.ipv4_name = rx_ipv4.name
    rx_bgpv4_peer = rx_bgpv4_int.peers.add()
    rx_bgpv4_peer.name = "rx_bgpv4"
    rx_bgpv4_peer.as_type = "ebgp"
    rx_bgpv4_peer.peer_address = "21.1.1.2"
    rx_bgpv4_peer.as_number = 65200
    rx_rr = rx_bgpv4_peer.v4_routes.add(name="rx_rr")
    rx_rr.addresses.add(count=1000, address="200.1.0.1", prefix=32)

    # flow config
    flow = conv_config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_device.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    flow.size.fixed = 1024
    flow.rate.percentage = 50
    flow.metrics.enable = True

    # flow2 config
    rx1_rr = rx_bgpv4_peer.v4_routes.add(name="rx1_rr")
    rx1_rr.addresses.add(count=1000, address="200.1.0.1", prefix=32)

    # flow config
    flow2 = conv_config.flows.flow(name="background_flow")[-1]
    flow2.tx_rx.device.tx_names = [tx_device.name]
    flow2.tx_rx.device.rx_names = [rx1_rr.name]

    flow2.size.fixed = 1024
    flow2.rate.percentage = 50
    flow2.metrics.enable = True

    return conv_config