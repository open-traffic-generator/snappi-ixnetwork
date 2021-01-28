import pytest


@pytest.mark.skip(reason="Bgp models have not been finalized")
def test_devices(serializer, api):
    """This is a BGPv4 demo test script
    """
    bgpv4 = Bgpv4(name='bgpv4',
        as_number_2_byte=Pattern('10'),
        dut_as_number_2_byte=Pattern('10'),
        as_number_4_byte=Pattern('20'),
        as_number_set_mode=Pattern('1'),
        as_type='IBGP',
        ipv4=Ipv4(name='ipv4',
            ethernet=Ethernet(name='eth1',
                vlans=[
                    Vlan(name='vlan1'),
                ]
            )
        ),
        bgpv4routerange=[
            Bgpv4RouteRange(name='bgpv4route1',
                            route_count=50,
                            address=Pattern('33.33.0.0'),
                            prefix=Pattern('16'),
                            as_path=Pattern('2'),
                            aigp_metric=Pattern('4')
                            ),
            Bgpv4RouteRange(name='bgpv4route2',
                            route_count=50,
                            address=Pattern('44.44.0.0'),
                            prefix=Pattern('16'),
                            as_path=Pattern('2'),
                            aigp_metric=Pattern('4')
                            ),
        ],
        bgpv6routerange=[
            Bgpv6RouteRange(name='bgpv6route1',
                            route_count=40,
                            address=Pattern('FF02::1'),
                            prefix=Pattern('64'),
                            as_path=Pattern('2'),
                            aigp_metric=Pattern('4')
                            ),
            Bgpv6RouteRange(name='bgpv6route2',
                            route_count=40,
                            address=Pattern('FF03::1'),
                            prefix=Pattern('64'),
                            as_path=Pattern('2'),
                            aigp_metric=Pattern('4')
                            ),
        ]
    )
    device = Device(name='device', choice=bgpv4, device_count=2)
    port = Port(name='port1', devices=[device])
    config = Config(ports=[port])
    state = State(ConfigState(config=config, state='set'))
    print(serializer.json(state))
    api.set_state(state)
    
    state = State(BgpControlState(state='start'))
    api.set_state(state)

    request = BgpInfoRequest(names=['bgpv4'])
    results = api.get_device_results(request)