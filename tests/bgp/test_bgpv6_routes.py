def test_bgpv6_routes(api, b2b_raw_config, utils):
    """
    Test for the bgpv6 routes
    """
    size = 1500
    packets = 1000
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name='tx_bgp').device(name='rx_bgp')
    d1.container_name, d2.container_name = p1.name, p2.name
    d1.device_count, d2.device_count = 10, 10
    eth1, eth2 = d1.ethernet, d2.ethernet
    ip1, ip2 = eth1.ipv6, eth2.ipv6
    bgp1, bgp2 = ip1.bgpv6, ip2.bgpv6

    ip1.address.increment.start = '2000::1'
    ip1.address.increment.step = '::1'
    ip1.gateway.increment.start = '3000::1'
    ip1.gateway.increment.step = '::1'
    ip1.prefix.value = 64

    ip2.address.increment.start = '3000::1'
    ip2.address.increment.step = '::1'
    ip2.gateway.increment.start = '2000::1'
    ip2.gateway.increment.step = '::1'
    ip2.prefix.value = 64

    bgp1.dut_ipv6_address.increment.start = '3000::1'
    bgp1.dut_ipv6_address.increment.step = '::1'

    bgp2.dut_ipv6_address.increment.start = '2000::1'
    bgp2.dut_ipv6_address.increment.step = '::1'

    bgp1_rr = bgp1.bgpv6_route_ranges.bgpv6routerange(name="bgp1_rr")[-1]
    bgp2_rr = bgp2.bgpv6_route_ranges.bgpv6routerange(name="bgp2_rr")[-1]

    bgp1_rr.name = "bgp1_rr"
    bgp1_rr.address.increment.start = "4000::1"
    bgp1_rr.address.increment.step = "::1"
    bgp1_rr.prefix.value = 64

    bgp2_rr.name = "bgp2_rr"
    bgp2_rr.address.increment.start = "6000::1"
    bgp2_rr.address.increment.step = "::1"
    bgp2_rr.prefix.value = 64

    flow_bgp = b2b_raw_config.flows.flow(name='flow_bgp')[-1]

    flow_bgp.rate.percentage = 1
    flow_bgp.duration.fixed_packets.packets = packets
    flow_bgp.size.fixed = size

    flow_bgp.tx_rx.device.tx_names = [bgp1_rr.name]
    flow_bgp.tx_rx.device.rx_names = [bgp2_rr.name]

    utils.start_traffic(api, b2b_raw_config, start_capture=False)

    utils.wait_for(
        lambda: results_ok(api, ['flow_bgp'], packets),
        'stats to be as expected', timeout_seconds=10
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
