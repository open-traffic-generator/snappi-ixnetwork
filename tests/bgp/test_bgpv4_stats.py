def test_bgpv4_stats(api, b2b_raw_config, utils):
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name='tx_bgp').device(name='rx_bgp')
    d1.container_name, d2.container_name = p1.name, p2.name
    d1.device_count, d2.device_count = 10, 10
    eth1, eth2 = d1.ethernet, d2.ethernet
    ip1, ip2 = eth1.ipv4, eth2.ipv4
    bgp1, bgp2 = ip1.bgpv4, ip2.bgpv4

    ip1.address.increment.start = '10.1.1.1'
    ip1.address.increment.step = '0.0.1.0'
    ip1.gateway.increment.start = '10.1.1.2'
    ip1.gateway.increment.step = '0.0.1.0'
    ip1.prefix.value = 24

    ip2.address.increment.start = '10.1.1.2'
    ip2.address.increment.step = '0.0.1.0'
    ip2.gateway.increment.start = '10.1.1.1'
    ip2.gateway.increment.step = '0.0.1.0'
    ip2.prefix.value = 24

    bgp1.dut_ipv4_address.increment.start = '10.1.1.2'
    bgp1.dut_ipv4_address.increment.step = '0.0.1.0'

    bgp2.dut_ipv4_address.increment.start = '10.1.1.1'
    bgp2.dut_ipv4_address.increment.step = '0.0.1.0'

    utils.start_traffic(api, b2b_raw_config)
    req = api.metrics_request()
    req.choice = req.BGPV4
    req.bgpv4
    results = api.get_metrics(req)
    enums = [
        'sessions_total', 'sessions_up',
        'sessions_down', 'sessions_not_started',
        'routes_advertised', 'routes_withdrawn'
    ]
    expected_results = {
        'tx_bgp': [10, 10, 0, 0, 0, 0],
        'rx_bgp': [10, 10, 0, 0, 0, 0]
    }
    assert len(results.bgpv4_metrics) == 2
    for bgp_res in results.bgpv4_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.choice = req.BGPV4
    req.bgpv4.device_names = ['rx_bgp']
    results = api.get_metrics(req)

    assert len(results.bgpv4_metrics) == 1
    assert results.bgpv4_metrics[0].name == 'rx_bgp'
    for bgp_res in results.bgpv4_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.choice = req.BGPV4
    req.bgpv4.column_names = ['sessions_total', 'sessions_up']
    results = api.get_metrics(req)
    assert len(results.bgpv4_metrics) == 2
    assert results.bgpv4_metrics[0].sessions_total == 10
    assert results.bgpv4_metrics[0].sessions_up == 10
    assert results.bgpv4_metrics[1].sessions_total == 10
    assert results.bgpv4_metrics[1].sessions_up == 10
    utils.stop_traffic(api)
