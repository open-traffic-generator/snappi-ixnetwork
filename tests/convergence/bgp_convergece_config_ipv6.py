import pytest

@pytest.fixture()
def bgp_convergence_multi_routes_ipv6_config(utils, api):
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
    tx_ipv6 = tx_eth.ipv6_addresses.add()
    tx_ipv6.name = "tx_ipv6"
    tx_ipv6.address = "2000::1"
    tx_ipv6.prefix = 64
    tx_ipv6.gateway = "3000::1"
    tx_bgpv6 = tx_device.bgp
    tx_bgpv6.router_id = "192.0.0.1"
    tx_bgpv6_int = tx_bgpv6.ipv6_interfaces.add()
    tx_bgpv6_int.ipv6_name = tx_ipv6.name
    tx_bgpv6_peer = tx_bgpv6_int.peers.add()
    tx_bgpv6_peer.name = "tx_bgpv6"
    tx_bgpv6_peer.as_type = "ibgp"
    tx_bgpv6_peer.peer_address = "3000::1"
    tx_bgpv6_peer.as_number = 10

    # rx_device config
    rx_eth = rx_device.ethernets.add()
    rx_eth.connection.port_name = rx.name
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv6 = rx_eth.ipv6_addresses.add()
    rx_ipv6.name = "rx_ipv6"
    rx_ipv6.address = "3000::1"
    rx_ipv6.prefix = 64
    rx_ipv6.gateway = "2000::1"
    rx_bgpv6 = rx_device.bgp
    rx_bgpv6.router_id = "192.0.0.2"
    rx_bgpv6_int = rx_bgpv6.ipv6_interfaces.add()
    rx_bgpv6_int.ipv6_name = rx_ipv6.name
    rx_bgpv6_peer = rx_bgpv6_int.peers.add()
    rx_bgpv6_peer.name = "rx_bgpv6"
    rx_bgpv6_peer.as_type = "ibgp"
    rx_bgpv6_peer.peer_address = "2000::1"
    rx_bgpv6_peer.as_number = 10
    rx_rr = rx_bgpv6_peer.v6_routes.add(name="rx_rr")
    rx_rr.addresses.add(count=1000, address="777:777:777::1", prefix=64)
    rx_rr.addresses.add(count=1000, address="222:222:222::1", prefix=64)

    # flow config
    flow = conv_config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_device.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    flow.size.fixed = 1024
    flow.rate.percentage = 50
    flow.metrics.enable = True

    # flow2 config
    rx1_rr = rx_bgpv6_peer.v6_routes.add(name="rx1_rr")
    rx1_rr.addresses.add(count=1000, address="333:333:333::1", prefix=64)

    # flow config
    flow2 = conv_config.flows.flow(name="background_flow")[-1]
    flow2.tx_rx.device.tx_names = [tx_device.name]
    flow2.tx_rx.device.rx_names = [rx1_rr.name]

    flow2.size.fixed = 1024
    flow2.rate.percentage = 50
    flow2.metrics.enable = True

    return conv_config