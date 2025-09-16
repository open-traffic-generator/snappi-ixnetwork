import pytest


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
        ip1.address = f"20.{i}.1.1"
        ip1.gateway = f"20.{i}.1.2"
        ip1.prefix = 24

    f1 = b2b_raw_config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = ["ip1_4"]
    f1.tx_rx.device.rx_names = ["ip2_3"]
    f1.packet.ethernet().vlan().tcp()

    api.set_config(b2b_raw_config)

    # utils.start_traffic(api, b2b_raw_config)
    # utils.wait_for(
    #     lambda: results_ok(api), "stats to be as expected", timeout_seconds=20
    # )
    # enums = [
    #     "session_state",
    #     "routes_advertised",
    #     "routes_received",
    #     "route_withdraws_sent",
    #     "route_withdraws_received",
    #     "updates_sent",
    #     "updates_received",
    #     "opens_sent",
    #     "opens_received",
    #     "keepalives_sent",
    #     "keepalives_received",
    #     "notifications_sent",
    #     "notifications_received",
    # ]
    # expected_results = {
    #     "tx_bgp": ["up", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #     "rx_bgp": ["up", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    # }
    # req = api.metrics_request()
    # req.bgpv4.peer_names = []
    # req.bgpv4.column_names = enums[:3]
    # results = api.get_metrics(req)
    # assert len(results.bgpv4_metrics) == 2
    # for bgp_res in results.bgpv4_metrics:
    #     for i, enum in enumerate(enums[:3]):
    #         val = expected_results[bgp_res.name][i]
    #         if "session_state" in enum:
    #             assert getattr(bgp_res, enum) == val
    #         else:
    #             assert getattr(bgp_res, enum) >= val

    # req = api.metrics_request()
    # req.bgpv4.peer_names = []
    # req.bgpv4.column_names = []
    # results = api.get_metrics(req)

    # assert len(results.bgpv4_metrics) == 2
    # for bgp_res in results.bgpv4_metrics:
    #     for i, enum in enumerate(enums):
    #         val = expected_results[bgp_res.name][i]
    #         if "session_state" in enum:
    #             assert getattr(bgp_res, enum) == val
    #         else:
    #             assert getattr(bgp_res, enum) >= val

    # req = api.metrics_request()
    # req.bgpv4.peer_names = ["rx_bgp"]
    # results = api.get_metrics(req)
    
    # assert len(results.bgpv4_metrics) == 1
    # assert results.bgpv4_metrics[0].name == "rx_bgp"
    # for bgp_res in results.bgpv4_metrics:
    #     for i, enum in enumerate(enums):
    #         val = expected_results[bgp_res.name][i]
    #         if "session_state" in enum:
    #             assert getattr(bgp_res, enum) == val
    #         else:
    #             assert getattr(bgp_res, enum) >= val

    # req = api.metrics_request()
    # req.bgpv4.column_names = ["session_state"]
    # results = api.get_metrics(req)
    # assert len(results.bgpv4_metrics) == 2
    # assert results.bgpv4_metrics[0].session_state == "up"
    # assert results.bgpv4_metrics[1].session_state == "up"
    # utils.stop_traffic(api, b2b_raw_config)


def results_ok(api):
    req = api.metrics_request()
    req.bgpv4.column_names = ["session_state"]
    results = api.get_metrics(req)
    ok = []
    for r in results.bgpv4_metrics:
        ok.append(r.session_state == "up")
    return all(ok)


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
