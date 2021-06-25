def test_bgpv4_stats(api, b2b_raw_config, utils):
    """
    Test for the bgpv4 metrics
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name='tx_bgp').device(name='rx_bgp')
    d1.container_name, d2.container_name = p1.name, p2.name
    # d1.device_count, d2.device_count = 10, 10
    eth1, eth2 = d1.ethernet, d2.ethernet
    eth1.mac, eth2.mac = '00:00:00:00:00:11', '00:00:00:00:00:22'
    ip1, ip2 = eth1.ipv4, eth2.ipv4
    bgp1, bgp2 = ip1.bgpv4, ip2.bgpv4
    eth1.name, eth2.name = 'eth1', 'eth2'
    ip1.name, ip2.name = 'ip1', 'ip2'
    bgp1.name, bgp2.name = 'bgp1', 'bpg2'

    ip1.address = '10.1.1.1'
    ip1.gateway = '10.1.1.2'
    ip1.prefix = 24

    ip2.address = '10.1.1.2'
    ip2.gateway = '10.1.1.1'
    ip2.prefix = 24

    bgp1.dut_address = '10.1.1.2'
    bgp1.local_address = '10.1.1.1'
    bgp1.as_type = 'ibgp'
    bgp1.as_number = 10

    bgp2.dut_address = '10.1.1.1'
    bgp2.local_address = '10.1.1.2'
    bgp2.as_type = 'ibgp'
    bgp2.as_number = 10

    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api),
        'stats to be as expected', timeout_seconds=20
    )
    enums = [
        'sessions_total', 'sessions_up',
        'sessions_down', 'sessions_not_started',
        'routes_advertised', 'routes_withdrawn'
    ]
    expected_results = {
        'tx_bgp': [1, 1, 0, 0, 0, 0],
        'rx_bgp': [1, 1, 0, 0, 0, 0]
    }
    req = api.metrics_request()
    req.bgpv4.device_names = []
    req.bgpv4.column_names = enums[:-2]
    results = api.get_metrics(req)

    assert len(results.bgpv4_metrics) == 2
    for bgp_res in results.bgpv4_metrics:
        for i, enum in enumerate(enums[:-2]):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.bgpv4.device_names = []
    req.bgpv4.column_names = []
    results = api.get_metrics(req)

    assert len(results.bgpv4_metrics) == 2
    for bgp_res in results.bgpv4_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.bgpv4.device_names = ['rx_bgp']
    results = api.get_metrics(req)

    assert len(results.bgpv4_metrics) == 1
    assert results.bgpv4_metrics[0].name == 'rx_bgp'
    for bgp_res in results.bgpv4_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[bgp_res.name][i]
            assert getattr(bgp_res, enum) == val

    req = api.metrics_request()
    req.bgpv4.column_names = ['sessions_total', 'sessions_up']
    results = api.get_metrics(req)
    assert len(results.bgpv4_metrics) == 2
    assert results.bgpv4_metrics[0].sessions_total == 1
    assert results.bgpv4_metrics[0].sessions_up == 1
    assert results.bgpv4_metrics[1].sessions_total == 1
    assert results.bgpv4_metrics[1].sessions_up == 1
    utils.stop_traffic(api, b2b_raw_config)


def results_ok(api):
    req = api.metrics_request()
    req.bgpv4.column_names = ['sessions_total', 'sessions_up']
    results = api.get_metrics(req)
    ok = []
    for r in results.bgpv4_metrics:
        ok.append(r.sessions_total == r.sessions_up)
    return all(ok)
