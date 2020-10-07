import pytest
from abstract_open_traffic_generator.port import Port
from abstract_open_traffic_generator.device import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator.result import BgpInfoRequest

def test_devices(serializer, api):
    """This is a BGPv4 demo test script
    """
    bgpv4 = Bgpv4(name='bgpv4',
        ipv4=Ipv4(name='ipv4',
            ethernet=Ethernet(name='eth1',
                vlans=[
                    Vlan(name='vlan1'),
                ]
            )
        ),
        bgpv4routerange=[
            Bgpv4RouteRange(name='bgpv4route1', route_count=50, address=Pattern('33.33.0.0'), prefix=Pattern('16')),
            Bgpv4RouteRange(name='bgpv4route2', route_count=50, address=Pattern('44.44.0.0'), prefix=Pattern('16')),
        ],
        bgpv6routerange=[
            Bgpv6RouteRange(name='bgpv6route1', route_count=40, address=Pattern('FF02::1'), prefix=Pattern('64')),
            Bgpv6RouteRange(name='bgpv6route2', route_count=40, address=Pattern('FF03::1'), prefix=Pattern('64')),
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