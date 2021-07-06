import pytest


@pytest.fixture
def config_v4_devices(api):
    """Configure bgpv4 devices"""
    config = api.config()

    tx, rx = config.ports.port(name="tx").port(name="rx")

    tx_device, rx_device = config.devices.device(
        name="tx_device", container_name=tx.name
    ).device(name="rx_device", container_name=rx.name)

    # tx_device config
    tx_eth = tx_device.ethernet
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:00:00:00:00:aa"
    tx_ipv4 = tx_eth.ipv4
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address = "21.1.1.2"
    tx_ipv4.prefix = 24
    tx_ipv4.gateway = "21.1.1.1"

    tx_bgpv4 = tx_ipv4.bgpv4
    tx_bgpv4.name = "tx_bgpv4"
    tx_bgpv4.as_type = "ebgp"
    tx_bgpv4.dut_address = "21.1.1.1"
    tx_bgpv4.local_address = "21.1.1.2"
    tx_bgpv4.as_number = 65201

    # rx_device config
    rx_eth = rx_device.ethernet
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv4 = rx_eth.ipv4
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address = "21.1.1.1"
    rx_ipv4.prefix = 24
    rx_ipv4.gateway = "21.1.1.2"
    rx_bgpv4 = rx_ipv4.bgpv4
    rx_bgpv4.name = "rx_bgpv4"
    rx_bgpv4.as_type = "ebgp"
    rx_bgpv4.dut_address = "21.1.1.2"
    rx_bgpv4.local_address = "21.1.1.1"
    rx_bgpv4.as_number = 65200
    rx_rr = rx_bgpv4.bgpv4_routes.bgpv4route(name="rx_rr")[-1]
    rx_rr.addresses.bgpv4routeaddress(
        count=1000, address="200.1.0.1", prefix=32
    )

    # flow config
    flow = config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_ipv4.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    api.set_config(config)


def test_issue_7(api, config_v4_devices):
    """This unit test to validate the fixes provided for the issue
    https://github.com/open-traffic-generator/snappi-convergence/issues/7"""
    config = api.config()

    tx, rx = config.ports.port(name="tx").port(name="rx")

    tx_device, rx_device = config.devices.device(
        name="tx_device", container_name=tx.name
    ).device(name="rx_device", container_name=rx.name)

    # tx_device config
    tx_eth = tx_device.ethernet
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:00:00:00:00:aa"
    tx_ipv6 = tx_eth.ipv6
    tx_ipv6.name = "tx_ipv6"
    tx_ipv6.address = "2000::1"
    tx_ipv6.prefix = 64
    tx_ipv6.gateway = "2000::2"
    tx_bgpv6 = tx_ipv6.bgpv6
    tx_bgpv6.name = "tx_bgpv6"
    tx_bgpv6.as_type = "ebgp"
    tx_bgpv6.dut_address = "2000::2"
    tx_bgpv6.local_address = "2000::1"
    tx_bgpv6.as_number = 65201

    # rx_device config
    rx_eth = rx_device.ethernet
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv6 = rx_eth.ipv6
    rx_ipv6.name = "rx_ipv6"
    rx_ipv6.address = "2000::2"
    rx_ipv6.prefix = 64
    rx_ipv6.gateway = "2000::1"
    rx_bgpv6 = rx_ipv6.bgpv6
    rx_bgpv6.name = "rx_bgpv6"
    rx_bgpv6.as_type = "ebgp"
    rx_bgpv6.dut_address = "2000::1"
    rx_bgpv6.local_address = "2000::2"
    rx_bgpv6.as_number = 65200
    rx6_rr = rx_bgpv6.bgpv6_routes.bgpv6route(name="rx6_rr")[-1]
    rx6_rr.addresses.bgpv6routeaddress(
        count=1000, address="3000::1", prefix=64
    )

    # flow config
    flow = config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_ipv6.name]
    flow.tx_rx.device.rx_names = [rx6_rr.name]

    api.set_config(config)

    validate_config(api)


def validate_config(api):
    assert (
        len(api._ixnetwork.Traffic.TrafficItem.find(Name="convergence_test"))
        == 1
    )

    assert (
        len(
            api._ixnetwork.Topology.find()
            .DeviceGroup.find(Name="tx_device")
            .Ethernet.find(Name="tx_eth")
            .Ipv4.find(Name="tx_ipv4")
        )
        == 0
    )

    assert (
        len(
            api._ixnetwork.Topology.find()
            .DeviceGroup.find(Name="tx_device")
            .Ethernet.find(Name="tx_eth")
            .Ipv6.find(Name="tx_ipv6")
        )
        == 1
    )

    assert (
        len(
            api._ixnetwork.Topology.find()
            .DeviceGroup.find(Name="rx_device")
            .Ethernet.find(Name="rx_eth")
            .Ipv4.find(Name="rx_ipv4")
        )
        == 0
    )

    assert (
        len(
            api._ixnetwork.Topology.find()
            .DeviceGroup.find(Name="rx_device")
            .Ethernet.find(Name="rx_eth")
            .Ipv6.find(Name="rx_ipv6")
        )
        == 1
    )


if __name__ == "__main__":
    pytest.main(["-s", __file__])
