import pytest


@pytest.mark.skip("Already bgpv4 and bgpv6 testcases are available")
def test_devices(api, utils):
    """This is a BGPv4 demo test script with router ranges"""
    config = api.config()

    tx, rx = config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    config.options.port_options.location_preemption = True
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [tx.name, rx.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    tx_device, rx_device = config.devices.device(
        name="tx_device", container_name=tx.name
    ).device(name="rx_device", container_name=rx.name)

    # tx_device config
    tx_eth = tx_device.ethernet
    tx_eth.name = "tx_eth"
    tx_ipv4 = tx_eth.ipv4
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address.value = "21.1.1.2"
    tx_ipv4.prefix.value = "24"
    tx_ipv4.gateway.value = "21.1.1.1"
    tx_bgpv4 = tx_ipv4.bgpv4
    tx_bgpv4.name = "tx_bgpv4"
    tx_bgpv4.as_type = "ibgp"
    tx_bgpv4.dut_ipv4_address.value = "22.1.1.1"
    tx_bgpv4.as_number.value = "65200"

    tx_rr = tx_bgpv4.bgpv4_route_ranges.bgpv4routerange()[-1]
    tx_rr.name = "tx_rr"
    tx_rr.address_count = "2000"
    tx_rr.address.value = "200.1.0.1"
    tx_rr.prefix.value = "32"

    tx_v6rr = tx_bgpv4.bgpv6_route_ranges.bgpv6routerange()[-1]
    tx_v6rr.name = "tx_v6rr"
    tx_v6rr.address_count = "1000"
    tx_v6rr.address.value = "10::1"
    tx_v6rr.prefix.value = "64"

    # rx_device config
    rx_eth = rx_device.ethernet
    rx_eth.name = "rx_eth"
    rx_ipv4 = rx_eth.ipv4
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address.value = "22.1.1.1"
    rx_ipv4.prefix.value = "24"
    rx_ipv4.gateway.value = "22.1.1.2"
    rx_bgpv4 = rx_ipv4.bgpv4
    rx_bgpv4.name = "rx_bgp"
    rx_bgpv4.as_type = "ibgp"
    rx_bgpv4.dut_ipv4_address.value = "22.1.1.2"
    rx_bgpv4.as_number.value = "65200"

    rx_rr = rx_bgpv4.bgpv4_route_ranges.bgpv4routerange()[-1]
    rx_rr.name = "rx_rr"
    rx_rr.address_count = "1000"
    rx_rr.address.value = "200.2.0.1"
    rx_rr.prefix.value = "32"

    # flow config
    flow = config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_rr.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    api.set_config(config)


if __name__ == "__main__":
    pytest.main(["-s", __file__])
