def test_bgpv6_routes(api, b2b_raw_config, utils):
    """
    Test for the bgpv6 routes
    """
    size = 1500
    packets = 1000
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="tx_bgp").device(name="rx_bgp")
    d1.container_name, d2.container_name = p1.name, p2.name
    eth1, eth2 = d1.ethernet, d2.ethernet
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv6, eth2.ipv6
    bgp1, bgp2 = ip1.bgpv6, ip2.bgpv6

    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"
    bgp1.name, bgp2.name = "bgp1", "bpg2"

    ip1.address = "2000::1"
    ip1.gateway = "3000::1"
    ip1.prefix = 64

    ip2.address = "3000::1"
    ip2.gateway = "2000::1"
    ip2.prefix = 64

    bgp1.dut_address = "3000::1"
    bgp1.local_address = "2000::1"
    bgp1.as_type = "ibgp"
    bgp1.as_number = 10

    bgp2.dut_address = "2000::1"
    bgp2.local_address = "3000::1"
    bgp2.as_type = "ibgp"
    bgp2.as_number = 10

    bgp1_rr1 = bgp1.bgpv6_routes.bgpv6route(name="bgp1_rr1")[-1]
    bgp1_rr2 = bgp1.bgpv6_routes.bgpv6route(name="bgp1_rr2")[-1]
    bgp2_rr1 = bgp2.bgpv6_routes.bgpv6route(name="bgp2_rr1")[-1]
    bgp2_rr2 = bgp2.bgpv6_routes.bgpv6route(name="bgp2_rr2")[-1]

    bgp1_rr1.addresses.bgpv6routeaddress(address="4000::1", prefix=64)
    bgp1_rr2.addresses.bgpv6routeaddress(address="5000::1", prefix=64)

    bgp2_rr1.addresses.bgpv6routeaddress(address="4000::1", prefix=64)
    bgp2_rr2.addresses.bgpv6routeaddress(address="5000::1", prefix=64)

    flow_bgp = b2b_raw_config.flows.flow(name="flow_bgp")[-1]

    flow_bgp.rate.percentage = 1
    flow_bgp.duration.fixed_packets.packets = packets
    flow_bgp.size.fixed = size
    flow_bgp.tx_rx.device.tx_names = [
        bgp1_rr1.name,
        bgp1_rr2.name,
        bgp2_rr1.name,
        bgp2_rr2.name,
    ]
    flow_bgp.tx_rx.device.rx_names = [
        bgp1_rr1.name,
        bgp1_rr2.name,
        bgp2_rr1.name,
        bgp2_rr2.name,
    ]
    flow_bgp.metrics.enable = True
    flow_bgp.metrics.loss = True
    utils.start_traffic(api, b2b_raw_config, start_capture=False)

    req = api.metrics_request()
    req.choice = "bgpv6"
    req.bgpv6.device_names = []
    results = api.get_metrics(req)
    enums = [
        "sessions_total",
        "sessions_up",
        "sessions_down",
        "sessions_not_started",
        "routes_advertised",
        "routes_withdrawn",
    ]
    expected_results = {
        "tx_bgp": [1, 1, 0, 0, 0, 0],
        "rx_bgp": [1, 1, 0, 0, 0, 0],
    }

    assert len(results.bgpv6_metrics) == 2
    for bgp_res in results.bgpv6_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.choice = "bgpv6"
    req.bgpv6.device_names = ["rx_bgp"]
    results = api.get_metrics(req)

    assert len(results.bgpv6_metrics) == 1
    assert results.bgpv6_metrics[0].name == "rx_bgp"
    for bgp_res in results.bgpv6_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.choice = "bgpv6"
    req.bgpv6.column_names = ["sessions_total", "sessions_up"]
    results = api.get_metrics(req)
    assert len(results.bgpv6_metrics) == 2
    assert results.bgpv6_metrics[0].sessions_total == 1
    assert results.bgpv6_metrics[0].sessions_up == 1
    assert results.bgpv6_metrics[1].sessions_total == 1
    assert results.bgpv6_metrics[1].sessions_up == 1

    utils.wait_for(
        lambda: results_ok(api, ["flow_bgp"], packets),
        "stats to be as expected",
        timeout_seconds=10,
    )
    utils.stop_traffic(api, b2b_raw_config)


def results_ok(api, flow_names, expected):
    """
    Returns True if there is no traffic loss else False
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    flow_rx = sum([f.frames_rx for f in flow_results])
    return flow_rx == expected
