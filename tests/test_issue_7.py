import pytest


@pytest.fixture
def config_v4_devices(api, utils):
    """Configure bgpv4 devices"""
    config = api.config()

    tx, rx = config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    tx_device, rx_device = config.devices.device(name="tx_device").device(
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
    tx_bgp4_int = tx_bgpv4.ipv4_interfaces.add()
    tx_bgp4_int.ipv4_name = tx_ipv4.name
    tc_bgp4_peer = tx_bgp4_int.peers.add()
    tc_bgp4_peer.name = "tx_bgpv4"
    tc_bgp4_peer.as_type = "ebgp"
    tc_bgp4_peer.peer_address = "21.1.1.1"
    tc_bgp4_peer.as_number = 65201

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
    flow = config.flows.flow(name="convergence_test")[-1]
    flow.tx_rx.device.tx_names = [tx_ipv4.name]
    flow.tx_rx.device.rx_names = [rx_rr.name]

    api.set_config(config)

@pytest.mark.skip(reason="skip to CICD faster")
def test_issue_7(api, config_v4_devices, utils):
    """This unit test to validate the fixes provided for the issue
    https://github.com/open-traffic-generator/snappi-convergence/issues/7"""
    config = api.config()

    tx, rx = config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    tx_device, rx_device = config.devices.device(name="tx_device").device(
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
    tx_ipv6.gateway = "2000::2"
    tx_bgpv6 = tx_device.bgp
    tx_bgpv6.router_id = "192.0.0.1"
    tx_bgpv6_int = tx_bgpv6.ipv6_interfaces.add()
    tx_bgpv6_int.ipv6_name = tx_ipv6.name
    tx_bgpv6_peer = tx_bgpv6_int.peers.add()
    tx_bgpv6_peer.name = "tx_bgpv6"
    tx_bgpv6_peer.as_type = "ebgp"
    tx_bgpv6_peer.peer_address = "2000::2"
    tx_bgpv6_peer.as_number = 65201

    # rx_device config
    rx_eth = rx_device.ethernets.add()
    rx_eth.connection.port_name = rx.name
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv6 = rx_eth.ipv6_addresses.add()
    rx_ipv6.name = "rx_ipv6"
    rx_ipv6.address = "2000::2"
    rx_ipv6.prefix = 64
    rx_ipv6.gateway = "2000::1"
    rx_bgpv6 = rx_device.bgp
    rx_bgpv6.router_id = "192.0.0.2"
    rx_bgpv6_int = rx_bgpv6.ipv6_interfaces.add()
    rx_bgpv6_int.ipv6_name = rx_ipv6.name
    rx_bgpv6_peer = rx_bgpv6_int.peers.add()
    rx_bgpv6_peer.name = "rx_bgpv6"
    rx_bgpv6_peer.as_type = "ebgp"
    rx_bgpv6_peer.peer_address = "2000::1"
    rx_bgpv6_peer.as_number = 65200
    rx6_rr = rx_bgpv6_peer.v6_routes.add(name="rx6_rr")
    rx6_rr.addresses.add(count=1000, address="3000::1", prefix=64)

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
