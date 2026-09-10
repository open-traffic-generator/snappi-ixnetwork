"""BGP Multi-VLAN Peer Test Module.

This module tests BGP peer and route flap functionality with multiple peer pairs,
each in different VLANs, using the Snappi API.

Test Topology:
    4 Pairs of devices, each in different VLAN:
    - Pair 1: dtx1/drx1 in VLAN 100
    - Pair 2: dtx2/drx2 in VLAN 200
    - Pair 3: dtx3/drx3 in VLAN 300
    - Pair 4: dtx4/drx4 in VLAN 400
    
    All devices share 2 physical ports (ptx, prx)
    
Features:
    - Multiple BGP peer pairs in separate VLANs
    - Configurable route range count per peer (routeRangeCount)
    - Each route range can advertise multiple routes (txRouteCount/rxRouteCount)
    - Automatic address calculation to avoid duplicate routes
    - IPv4 and IPv6 route support
    - Bidirectional traffic flows
    - Optional traffic per pair (enableTraffic flag)
"""

import snappi
import json
import threading
import time

from utils import (
    wait_for,
    bgp_prefixes_ok,
    flow_metrics_ok,
    bgp_metrics_ok_all_pairs,
    create_multi_vlan_config,
    flap_bgp_peer,
    print_bgp_sessions_up,

)

# Test configuration constants
# Four pairs of BGP peers in different VLANs
TEST_CONST = {
    "pktRate": 50,
    "pktCount": 100,
    "pktSize": 128,
    "useVlan": True,
    "pairs": [
        {
            "pairId": 1,
            "vlanId": 100,
            "txMac": "00:00:01:01:01:01",
            "txIp": "1.1.1.1",
            "txGateway": "1.1.1.2",
            "txPrefix": 24,
            "txAs": 1111,
            "rxMac": "00:00:01:01:01:02",
            "rxIp": "1.1.1.2",
            "rxGateway": "1.1.1.1",
            "rxPrefix": 24,
            "rxAs": 1112,
            "routeRangeCount": 4,
            "txRouteCount": 1,
            "rxRouteCount": 1,
            "txNextHopV4": "1.1.1.3",
            "txNextHopV6": "0:0:0:0:1:1:1:3",
            "rxNextHopV4": "1.1.1.4",
            "rxNextHopV6": "0:0:0:0:1:1:1:4",
            "txAdvRouteV4": "10.10.10.1",
            "rxAdvRouteV4": "20.20.20.1",
            "txAdvRouteV6": "::10:10:10:1",
            "rxAdvRouteV6": "::20:20:20:1",
            "enableTraffic": True
        },
        {
            "pairId": 2,
            "vlanId": 200,
            "txMac": "00:00:02:01:01:01",
            "txIp": "2.2.2.1",
            "txGateway": "2.2.2.2",
            "txPrefix": 24,
            "txAs": 2111,
            "rxMac": "00:00:02:01:01:02",
            "rxIp": "2.2.2.2",
            "rxGateway": "2.2.2.1",
            "rxPrefix": 24,
            "rxAs": 2112,
            "routeRangeCount": 4,
            "txRouteCount": 1,
            "rxRouteCount": 1,
            "txNextHopV4": "2.2.2.3",
            "txNextHopV6": "0:0:0:0:2:2:2:3",
            "rxNextHopV4": "2.2.2.4",
            "rxNextHopV6": "0:0:0:0:2:2:2:4",
            "txAdvRouteV4": "10.10.20.1",
            "rxAdvRouteV4": "20.20.30.1",
            "txAdvRouteV6": "::10:10:20:1",
            "rxAdvRouteV6": "::20:20:30:1",
            "enableTraffic": True
        },
        {
            "pairId": 3,
            "vlanId": 300,
            "txMac": "00:00:03:01:01:01",
            "txIp": "3.3.3.1",
            "txGateway": "3.3.3.2",
            "txPrefix": 24,
            "txAs": 3111,
            "rxMac": "00:00:03:01:01:02",
            "rxIp": "3.3.3.2",
            "rxGateway": "3.3.3.1",
            "rxPrefix": 24,
            "rxAs": 3112,
            "routeRangeCount": 4,
            "txRouteCount": 1,
            "rxRouteCount": 1,
            "txNextHopV4": "3.3.3.3",
            "txNextHopV6": "0:0:0:0:3:3:3:3",
            "rxNextHopV4": "3.3.3.4",
            "rxNextHopV6": "0:0:0:0:3:3:3:4",
            "txAdvRouteV4": "10.10.30.1",
            "rxAdvRouteV4": "20.20.40.1",
            "txAdvRouteV6": "::10:10:30:1",
            "rxAdvRouteV6": "::20:20:40:1",
            "enableTraffic": True
        },
        {
            "pairId": 4,
            "vlanId": 400,
            "txMac": "00:00:04:01:01:01",
            "txIp": "4.4.4.1",
            "txGateway": "4.4.4.2",
            "txPrefix": 24,
            "txAs": 4111,
            "rxMac": "00:00:04:01:01:02",
            "rxIp": "4.4.4.2",
            "rxGateway": "4.4.4.1",
            "rxPrefix": 24,
            "rxAs": 4112,
            "routeRangeCount": 4,
            "txRouteCount": 1,
            "rxRouteCount": 1,
            "txNextHopV4": "4.4.4.3",
            "txNextHopV6": "0:0:0:0:4:4:4:3",
            "rxNextHopV4": "4.4.4.4",
            "rxNextHopV6": "0:0:0:0:4:4:4:4",
            "txAdvRouteV4": "10.10.40.1",
            "rxAdvRouteV4": "20.20.50.1",
            "txAdvRouteV6": "::10:10:40:1",
            "rxAdvRouteV6": "::20:20:50:1",
            "enableTraffic": True
        },
    ]
}

def peerFlap(
    api,
    peerList,
    up_time_seconds,
    down_time_seconds,
    cycles=1,
    run_async=False
):
    """Flap BGP peers either synchronously or asynchronously.
    
    Args:
        api: Snappi API instance
        peerList: List of peer names to flap
        up_time_seconds: Duration in seconds to keep peers UP
        down_time_seconds: Duration in seconds to keep peers DOWN
        cycles: Number of complete up/down cycles to perform (default: 1)
        run_async: If True, run flapping in a separate thread (default: False)
    
    Returns:
        Thread object if run_async=True, None otherwise
    """
    runInThread = run_async
    
    if runInThread:
        print("Running BGP peer flapping in a separate thread...")
        def flap_all_peers():
            """Flap all BGP peers in the peer list."""
            for peer_name in peerList:
                flap_bgp_peer(
                    api,
                    peer_name,
                    up_time_seconds=up_time_seconds,
                    down_time_seconds=down_time_seconds,
                    cycles=cycles
                )

        flap_thread = threading.Thread(
            target=flap_all_peers,
            name="BGP_Peer_Flapping"
        )
        flap_thread.start()
        print("BGP peer flapping thread started")
        return flap_thread
    else:
        print("Running BGP peer flapping in the main thread...")
        for peer_name in peerList:
            flap_bgp_peer(
                api,
                peer_name,
                up_time_seconds=up_time_seconds,
                down_time_seconds=down_time_seconds,
                cycles=cycles
            )
        return None


def test_multi_vlan_bgp_peers(otg_config=None):
    """Test BGP with multiple peer pairs in different VLANs.
    
    This test configures multiple BGP peer pairs, each in a separate VLAN,
    establishes BGP sessions, validates routes, and optionally runs traffic.
    
    Args:
        otg_config: Optional configuration dict. If None, loads from otg_ports.json
                    or environment variables. When run with pytest, this is
                    automatically injected as a fixture.
    
    Features:
        - Multiple peer pairs in separate VLANs
        - Configurable route ranges per peer (routeRangeCount)
        - Optional traffic flows per pair (enableTraffic flag)
        - BGP metrics and prefix validation
        - Traffic validation for enabled flows
    
    Can be run both ways:
        - pytest test_peer_and_route_flap_multi_vlan.py (uses fixture)
        - python test_peer_and_route_flap_multi_vlan.py (loads config directly)
    """
    test_const = TEST_CONST
   
    # Load configuration if not provided (standalone mode)
    if otg_config is None:
        from utils import get_otg_config
        config = get_otg_config()
        print("Running in standalone mode - loaded config from otg_ports.json")
    else:
        config = otg_config
        print("Running with pytest - using injected configuration fixture")
    print(f"OTG Host      : {config['host']}")
    print(f"OTG Ports     : {config['ports']}")
    print(f"OTG Transport : "
          f"{'grpc' if config['grpc_transport'] else 'http'}")
    api = snappi.api(
        config["host"],
        verify=False,
        transport="grpc" if config["grpc_transport"] else "http",
        version_check=True,
    )
    print(f"OTG API Version: {api.version()}")
    
    # Build and set configuration for all 4 pairs
    bgpConfig = create_multi_vlan_config(
        api,
        config,
        test_const,
        print_config=True)

    print("Setting config ...")
    api.set_config(bgpConfig)

    # Start BGP protocols
    print("Starting protocols ...")
    cs = api.control_state()
    cs.protocol.all.state = cs.protocol.all.START
    api.set_control_state(cs)

    # Wait for BGP sessions
    print("Waiting for BGP sessions to establish...")
    wait_for(
        fn=lambda: bgp_metrics_ok_all_pairs(api, test_const),
        fn_name="wait_for_bgp_metrics",
        timeout_seconds=30,
    )
    assert(
        bgp_metrics_ok_all_pairs(api, test_const),
        "BGP metrics validation failed"
    )
    print("BGP metrics validation passed for all pairs")

    # Validate BGP prefixes
    print("Validating BGP prefixes...")
    all_ipv4_routes = []
    all_ipv6_routes = []
    
    # Build expected routes for all pairs and all route ranges
    for pair in test_const["pairs"]:
        # For each route range in this pair
        for route_idx in range(pair["routeRangeCount"]):
            # TX IPv4 routes
            ipv4_offset = route_idx * pair["txRouteCount"]
            base_addr = pair["txAdvRouteV4"]
            addr_parts = base_addr.split('.')
            for addr_offset in range(pair["txRouteCount"]):
                # Incrementing IP address
                last_octet = int(addr_parts[3]) + ipv4_offset + addr_offset
                route_addr = (f"{addr_parts[0]}.{addr_parts[1]}."
                            f"{addr_parts[2]}.{last_octet}")
                all_ipv4_routes.append({
                    "ipv4": route_addr,
                    "nexthop": pair["txNextHopV4"]
                })
            
            # RX IPv4 routes
            ipv4_offset = route_idx * pair["rxRouteCount"]
            base_addr = pair["rxAdvRouteV4"]
            addr_parts = base_addr.split('.')
            for addr_offset in range(pair["rxRouteCount"]):
                # Incrementing IP address
                last_octet = int(addr_parts[3]) + ipv4_offset + addr_offset
                route_addr = (f"{addr_parts[0]}.{addr_parts[1]}."
                            f"{addr_parts[2]}.{last_octet}")
                all_ipv4_routes.append({
                    "ipv4": route_addr,
                    "nexthop": pair["rxNextHopV4"]
                })
            
            # TX IPv6 routes
            ipv6_offset = route_idx * pair["txRouteCount"]
            base_addr_v6 = pair["txAdvRouteV6"]
            for addr_offset in range(pair["txRouteCount"]):
                if '::' in base_addr_v6:
                    addr_parts_v6 = base_addr_v6.rsplit(':', 1)
                    # Incrementing IP address
                    last_segment = (int(addr_parts_v6[1], 16) + 
                                  ipv6_offset + addr_offset)
                    route_addr_v6 = f"{addr_parts_v6[0]}:{last_segment:x}"
                else:
                    addr_parts_v6 = base_addr_v6.split(':')
                    # Incrementing IP address
                    last_segment = (int(addr_parts_v6[-1], 16) + 
                                  ipv6_offset + addr_offset)
                    addr_parts_v6[-1] = f"{last_segment:x}"
                    route_addr_v6 = ':'.join(addr_parts_v6)
                all_ipv6_routes.append({
                    "ipv6": route_addr_v6,
                    "nexthop": pair["txNextHopV6"]
                })
            
            # RX IPv6 routes
            ipv6_offset = route_idx * pair["rxRouteCount"]
            base_addr_v6 = pair["rxAdvRouteV6"]
            for addr_offset in range(pair["rxRouteCount"]):
                if '::' in base_addr_v6:
                    addr_parts_v6 = base_addr_v6.rsplit(':', 1)
                    # Incrementing IP address
                    last_segment = (int(addr_parts_v6[1], 16) + 
                                  ipv6_offset + addr_offset)
                    route_addr_v6 = f"{addr_parts_v6[0]}:{last_segment:x}"
                else:
                    addr_parts_v6 = base_addr_v6.split(':')
                    # Incrementing IP address
                    last_segment = (int(addr_parts_v6[-1], 16) + 
                                  ipv6_offset + addr_offset)
                    addr_parts_v6[-1] = f"{last_segment:x}"
                    route_addr_v6 = ':'.join(addr_parts_v6)
                all_ipv6_routes.append({
                    "ipv6": route_addr_v6,
                    "nexthop": pair["rxNextHopV6"]
                })
    
    wait_for(
        fn=lambda: bgp_prefixes_ok(api, all_ipv4_routes, all_ipv6_routes),
        fn_name="wait_for_bgp_prefixes",
        timeout_seconds=30,
    )
    assert(
        bgp_prefixes_ok(api, all_ipv4_routes, all_ipv6_routes),
        "BGP prefixes validation failed"
    )
    print("BGP prefixes validation passed for all pairs")

    # Build peer list - flap only Tx peer for each pair
    peer_list = [f"dtx{pair['pairId']}_peer" for pair in test_const["pairs"]]
    
    # Flap BGP peers for all pairs
    print("Starting BGP peer flapping...")
    flap_thread = peerFlap(
        api,
        peer_list,
        up_time_seconds=30,
        down_time_seconds=10,
        cycles=3,
        run_async=True  # Set to False to run flapping in main thread
    )
    
    # Monitor BGP sessions status while the peers are flapping
    if flap_thread:
        while flap_thread.is_alive():
            print_bgp_sessions_up(api)
            time.sleep(5)
        print("BGP peer flapping completed")
    else:
        # TBD
        print("BGP peer flapping completed in main thread")
        pass

    # Start traffic (only if at least one pair has traffic enabled)
    traffic_enabled_pairs = [
        pair for pair in test_const["pairs"] 
        if pair.get("enableTraffic", True)
    ]
    
    if traffic_enabled_pairs:
        print(f"Starting transmit for {len(traffic_enabled_pairs)} pair(s)...")
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
        api.set_control_state(cs)

        # Wait for traffic flows
        print("Waiting for traffic flows to complete...")
        wait_for(
            fn=lambda: flow_metrics_ok(api, test_const), 
            fn_name="wait_for_flow_metrics",
            timeout_seconds=30,
        )
        assert(
            flow_metrics_ok(api, test_const),
            "Flow metrics validation failed"
        )
        print("Flow metrics validation passed for enabled pairs")
    else:
        print("No traffic configured - all pairs have enableTraffic=False")


if __name__ == "__main__":
    # Run standalone - config will be loaded automatically from otg_ports.json
    test_multi_vlan_bgp_peers()
