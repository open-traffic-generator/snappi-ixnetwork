import pytest


@pytest.fixture()
def bgp_convergence_config(utils, cvg_api):
    """
    1.Configure IPv4 EBGP sessions between Keysight ports(rx & tx)
    2.Configure and advertise IPv4 routes from rx
    """

    conv_config = cvg_api.convergence_config()
    config = conv_config.config

    tx, rx = (
        config.ports
        .port(name='tx', location=utils.settings.ports[0])
        .port(name='rx', location=utils.settings.ports[1])
    )

    config.options.port_options.location_preemption = True
    ly = config.layer1.layer1()[-1]
    ly.name = 'ly'
    ly.port_names = [tx.name, rx.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    tx_device, rx_device = (
        config.devices
        .device(name="tx_device", container_name=tx.name)
        .device(name="rx_device", container_name=rx.name)
    )

    # tx_device config
    tx_eth = tx_device.ethernet
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:00:00:00:00:aa"
    tx_ipv4 = tx_eth.ipv4
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address = "21.1.1.2"
    tx_ipv4.prefix = "24"
    tx_ipv4.gateway = "21.1.1.1"
    tx_bgpv4 = tx_ipv4.bgpv4
    tx_bgpv4.name = "tx_bgpv4"
    tx_bgpv4.as_type = "ebgp"
    tx_bgpv4.dut_address = "21.1.1.1"
    tx_bgpv4.as_number = "65201"

    # rx_device config
    rx_eth = rx_device.ethernet
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv4 = rx_eth.ipv4
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address = "21.1.1.1"
    rx_ipv4.prefix = "24"
    rx_ipv4.gateway = "21.1.1.2"
    rx_bgpv4 = rx_ipv4.bgpv4
    rx_bgpv4.name = "rx_bgpv4"
    rx_bgpv4.as_type = "ebgp"
    rx_bgpv4.dut_address = "21.1.1.2"
    rx_bgpv4.as_number = "65200"
    rx_rr = rx_bgpv4.bgpv4_routes.bgpv4route(name="rx_rr")[-1]
    rx_rr.addresses.bgpv4routeaddress(count=1000,
                                      address='200.1.0.1',
                                      prefix=32)

    # flow config
    flow = config.flows.flow(name='convergence_test')[-1]
    flow.tx_rx.device.tx_names = [tx_device.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    flow.size.fixed = "1024"
    flow.rate.percentage = "50"
    flow.metrics.enable = True

    # flow2 config
    rx1_rr = rx_bgpv4.bgpv4_routes.bgpv4route(name="rx1_rr")[-1]
    rx1_rr.addresses.bgpv4routeaddress(count=1000,
                                       address='200.1.0.1',
                                       prefix=32)

    # flow config
    flow2 = config.flows.flow(name='background_flow')[-1]
    flow2.tx_rx.device.tx_names = [tx_device.name]
    flow2.tx_rx.device.rx_names = [rx1_rr.name]

    flow2.size.fixed = "1024"
    flow2.rate.percentage = "50"
    flow2.metrics.enable = True

    return conv_config
