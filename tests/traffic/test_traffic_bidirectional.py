import pytest


def test_traffic_bidirectional(api, b2b_raw_config):
    """
    Configure IPv4 devices on the Tx and Rx ports and create a flow with
    device endpoints using the bidirectional option under flows->tx_rx->device.

    When bidirectional is enabled, IxNetwork creates traffic sub-flows in both
    the forward (tx_names -> rx_names) and reverse (rx_names -> tx_names)
    directions.

    Validation:
    - the imported IxNetwork traffic item has BiDirectional set to True.
    """
    b2b_raw_config.flows.clear()
    config = b2b_raw_config
    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [ip1.name]
    f1.tx_rx.device.rx_names = [ip2.name]
    f1.tx_rx.device.bidirectional = True
    f1.packet.ethernet().ipv4().tcp()

    api.set_config(config)

    validate_bidirectional(api, "f1", True)


def test_traffic_bidirectional_disabled(api, b2b_raw_config):
    """
    By default device flows are unidirectional. Verify that when bidirectional
    is not set the imported IxNetwork traffic item has BiDirectional False.
    """
    b2b_raw_config.flows.clear()
    config = b2b_raw_config
    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [ip1.name]
    f1.tx_rx.device.rx_names = [ip2.name]
    f1.packet.ethernet().ipv4().tcp()

    api.set_config(config)

    validate_bidirectional(api, "f1", False)


def validate_bidirectional(api, flow_name, expected):
    """
    Validate that the imported IxNetwork traffic item carries the expected
    BiDirectional value.
    """
    traffic_item = api._ixnetwork.Traffic.TrafficItem.find(Name=flow_name)
    assert traffic_item.BiDirectional == expected


if __name__ == "__main__":
    pytest.main(["-s", __file__])
