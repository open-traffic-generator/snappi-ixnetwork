import pytest

# @pytest.mark.skip("4 port configuration is not supported in ci")
def test_compaction_traffic_device(api, b2b_raw_config):
    # import snappi

    # config = snappi.Api().config()
    api._enable_port_compaction(True)
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
    f1.packet.ethernet().vlan().tcp()
    api.set_config(config)
