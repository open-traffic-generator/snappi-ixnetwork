import pytest


# @pytest.mark.skip("4 port configuration is not supported in ci")
def test_compaction_4device(api, b2b_raw_config, utils):
    """
    Test for the bgpv4 metrics
    """
    api._enable_port_compaction(True)
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    device_count = 4
    for i in range(1, device_count + 1):
        dev = b2b_raw_config.devices.device(name=f"dev1{i}")[-1]
        eth1 = dev.ethernets.add()
        eth1.connection.port_name = p1.name
        eth1.mac = f"00:00:00:00:00:1{i}"
        ip1 = eth1.ipv4_addresses.add()

        eth1.name = f"eth1_{i}"
        ip1.name = f"ip1_{i}"
        ip1.address = f"10.{i}.1.1"
        ip1.gateway = f"10.{i}.1.2"
        ip1.prefix = 24

    for i in range(1, device_count + 1):
        dev = b2b_raw_config.devices.device(name=f"dev2{i}")[-1]
        eth1 = dev.ethernets.add()
        eth1.connection.port_name = p2.name
        eth1.mac = f"00:00:00:00:00:2{i}"
        ip1 = eth1.ipv4_addresses.add()

        eth1.name = f"eth2_{i}"
        ip1.name = f"ip2_{i}"
        ip1.address = f"10.{i}.1.2"
        ip1.gateway = f"10.{i}.1.1"
        ip1.prefix = 24

    f1 = b2b_raw_config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = ["ip1_4"]
    f1.tx_rx.device.rx_names = ["ip2_3"]
    f1.packet.ethernet().vlan().tcp()

    api.set_config(b2b_raw_config)
    # Set the flag back to false else other tests will fail
    api._enable_port_compaction(False)

if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
