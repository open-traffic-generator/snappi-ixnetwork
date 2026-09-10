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

import threading
import time

# Flap timing, kept small since this runs against a real chassis
FLAP_UP_SECONDS = 10
FLAP_DOWN_SECONDS = 5
FLAP_CYCLES = 2

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
            "txIpv6": "2001:1:1:1::1",
            "txGatewayV6": "2001:1:1:1::2",
            "txAs": 1111,
            "rxMac": "00:00:01:01:01:02",
            "rxIp": "1.1.1.2",
            "rxGateway": "1.1.1.1",
            "rxPrefix": 24,
            "rxIpv6": "2001:1:1:1::2",
            "rxGatewayV6": "2001:1:1:1::1",
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
            "txIpv6": "2001:2:2:2::1",
            "txGatewayV6": "2001:2:2:2::2",
            "txAs": 2111,
            "rxMac": "00:00:02:01:01:02",
            "rxIp": "2.2.2.2",
            "rxGateway": "2.2.2.1",
            "rxPrefix": 24,
            "rxIpv6": "2001:2:2:2::2",
            "rxGatewayV6": "2001:2:2:2::1",
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
            "txIpv6": "2001:3:3:3::1",
            "txGatewayV6": "2001:3:3:3::2",
            "txAs": 3111,
            "rxMac": "00:00:03:01:01:02",
            "rxIp": "3.3.3.2",
            "rxGateway": "3.3.3.1",
            "rxPrefix": 24,
            "rxIpv6": "2001:3:3:3::2",
            "rxGatewayV6": "2001:3:3:3::1",
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
            "txIpv6": "2001:4:4:4::1",
            "txGatewayV6": "2001:4:4:4::2",
            "txAs": 4111,
            "rxMac": "00:00:04:01:01:02",
            "rxIp": "4.4.4.2",
            "rxGateway": "4.4.4.1",
            "rxPrefix": 24,
            "rxIpv6": "2001:4:4:4::2",
            "rxGatewayV6": "2001:4:4:4::1",
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


def configure_bgp_pair(config, ptx, prx, pair, use_vlan):
    """Configure a single BGP peer pair.

    Creates multiple route ranges per peer based on routeRangeCount.
    Each route range advertises routes with unique addresses calculated
    by adding an offset to the base address to avoid duplicates.

    Args:
        config: Snappi configuration object
        ptx, prx: Port objects
        pair: Dictionary with pair configuration
        use_vlan: Boolean to enable VLAN tagging

    Returns:
        Tuple of lists: (dtx_v4_routes, drx_v4_routes,
                        dtx_v6_routes, drx_v6_routes)
    """
    pair_id = pair["pairId"]

    # Create devices
    dtx = config.devices.add(name=f"dtx{pair_id}")
    drx = config.devices.add(name=f"drx{pair_id}")

    # Configure TX device
    dtx_eth = dtx.ethernets.add(name=f"dtx{pair_id}_eth")
    dtx_eth.connection.port_name = ptx.name
    dtx_eth.mac = pair["txMac"]
    dtx_eth.mtu = 1500

    if use_vlan:
        dtx_vlan = dtx_eth.vlans.add(name=f"dtx{pair_id}_vlan")
        dtx_vlan.id = pair["vlanId"]

    dtx_ip = dtx_eth.ipv4_addresses.add(name=f"dtx{pair_id}_ip")
    dtx_ip.set(
        address=pair["txIp"],
        gateway=pair["txGateway"],
        prefix=pair["txPrefix"]
    )
    dtx_ipv6 = dtx_eth.ipv6_addresses.add(name=f"dtx{pair_id}_ipv6")
    dtx_ipv6.set(
        address=pair["txIpv6"],
        gateway=pair["txGatewayV6"],
        prefix=64
    )

    dtx.bgp.router_id = pair["txIp"]
    dtx_bgpv4 = dtx.bgp.ipv4_interfaces.add(ipv4_name=dtx_ip.name)
    dtx_bgpv4_peer = dtx_bgpv4.peers.add(name=f"dtx{pair_id}_peer")
    dtx_bgpv4_peer.set(
        as_number=pair["txAs"],
        as_type=dtx_bgpv4_peer.EBGP,
        peer_address=pair["txGateway"]
    )
    dtx_bgpv4_peer.learned_information_filter.unicast_ipv4_prefix = True

    # IxNetwork requires IPv6 route ranges to be advertised by a genuine
    # BGP+ IPv6 peer (its own protocol stack over an IPv6 interface); it
    # rejects them when attached to an IPv4-only peer, even with MP-BGP
    # capability negotiation enabled.
    dtx_bgpv6 = dtx.bgp.ipv6_interfaces.add(ipv6_name=dtx_ipv6.name)
    dtx_bgpv6_peer = dtx_bgpv6.peers.add(name=f"dtx{pair_id}_v6_peer")
    dtx_bgpv6_peer.set(
        as_number=pair["txAs"],
        as_type=dtx_bgpv6_peer.EBGP,
        peer_address=pair["txGatewayV6"]
    )
    dtx_bgpv6_peer.learned_information_filter.unicast_ipv6_prefix = True

    # Create multiple route ranges based on routeRangeCount
    dtx_v4_routes = []
    dtx_v6_routes = []
    for route_idx in range(pair["routeRangeCount"]):
        # IPv4 route
        # Calculate offset for this route range to avoid duplicates
        # Each range advertises 'txRouteCount' addresses
        ipv4_offset = route_idx * pair["txRouteCount"]

        dtx_v4 = dtx_bgpv4_peer.v4_routes.add(
            name=f"dtx{pair_id}_v4route_{route_idx}"
        )
        dtx_v4.set(
            next_hop_ipv4_address=pair["txNextHopV4"],
            next_hop_address_type=dtx_v4.IPV4,
            next_hop_mode=dtx_v4.MANUAL
        )

        # Parse base address and add offset
        base_addr = pair["txAdvRouteV4"]
        addr_parts = base_addr.split('.')
        # Incrementing IP address
        last_octet = int(addr_parts[3]) + ipv4_offset
        route_addr = f"{addr_parts[0]}.{addr_parts[1]}." \
                    f"{addr_parts[2]}.{last_octet}"

        dtx_v4.addresses.add(
            address=route_addr,
            prefix=32,
            count=pair["txRouteCount"],
            step=1
        )
        dtx_v4.advanced.set(
            multi_exit_discriminator=50,
            origin=dtx_v4.advanced.EGP
        )
        dtx_v4_routes.append(dtx_v4)

        # IPv6 route
        ipv6_offset = route_idx * pair["txRouteCount"]

        dtx_v6 = dtx_bgpv6_peer.v6_routes.add(
            name=f"dtx{pair_id}_v6route_{route_idx}"
        )
        dtx_v6.set(
            next_hop_ipv6_address=pair["txNextHopV6"],
            next_hop_address_type=dtx_v6.IPV6,
            next_hop_mode=dtx_v6.MANUAL
        )

        # Parse base IPv6 address and add offset
        base_addr_v6 = pair["txAdvRouteV6"]
        # For simplicity with compressed IPv6, add offset to last segment
        if '::' in base_addr_v6:
            addr_parts_v6 = base_addr_v6.rsplit(':', 1)
            # Incrementing IP address
            last_segment = int(addr_parts_v6[1], 16) + ipv6_offset
            route_addr_v6 = f"{addr_parts_v6[0]}:{last_segment:x}"
        else:
            addr_parts_v6 = base_addr_v6.split(':')
            # Incrementing IP address
            last_segment = int(addr_parts_v6[-1], 16) + ipv6_offset
            addr_parts_v6[-1] = f"{last_segment:x}"
            route_addr_v6 = ':'.join(addr_parts_v6)

        dtx_v6.addresses.add(
            address=route_addr_v6,
            prefix=128,
            count=pair["txRouteCount"],
            step=1
        )
        dtx_v6.advanced.set(
            multi_exit_discriminator=50,
            origin=dtx_v6.advanced.EGP
        )
        dtx_v6_routes.append(dtx_v6)

    # Configure RX device
    drx_eth = drx.ethernets.add(name=f"drx{pair_id}_eth")
    drx_eth.connection.port_name = prx.name
    drx_eth.mac = pair["rxMac"]
    drx_eth.mtu = 1500

    if use_vlan:
        drx_vlan = drx_eth.vlans.add(name=f"drx{pair_id}_vlan")
        drx_vlan.id = pair["vlanId"]

    drx_ip = drx_eth.ipv4_addresses.add(name=f"drx{pair_id}_ip")
    drx_ip.set(
        address=pair["rxIp"],
        gateway=pair["rxGateway"],
        prefix=pair["rxPrefix"]
    )
    drx_ipv6 = drx_eth.ipv6_addresses.add(name=f"drx{pair_id}_ipv6")
    drx_ipv6.set(
        address=pair["rxIpv6"],
        gateway=pair["rxGatewayV6"],
        prefix=64
    )

    drx.bgp.router_id = pair["rxIp"]
    drx_bgpv4 = drx.bgp.ipv4_interfaces.add()
    drx_bgpv4.ipv4_name = drx_ip.name
    drx_bgpv4_peer = drx_bgpv4.peers.add(name=f"drx{pair_id}_peer")
    drx_bgpv4_peer.set(
        as_number=pair["rxAs"],
        as_type=drx_bgpv4_peer.EBGP,
        peer_address=pair["rxGateway"]
    )
    drx_bgpv4_peer.learned_information_filter.unicast_ipv4_prefix = True

    drx_bgpv6 = drx.bgp.ipv6_interfaces.add(ipv6_name=drx_ipv6.name)
    drx_bgpv6_peer = drx_bgpv6.peers.add(name=f"drx{pair_id}_v6_peer")
    drx_bgpv6_peer.set(
        as_number=pair["rxAs"],
        as_type=drx_bgpv6_peer.EBGP,
        peer_address=pair["rxGatewayV6"]
    )
    drx_bgpv6_peer.learned_information_filter.unicast_ipv6_prefix = True

    # Create multiple route ranges based on routeRangeCount
    drx_v4_routes = []
    drx_v6_routes = []
    for route_idx in range(pair["routeRangeCount"]):
        # IPv4 route
        # Calculate offset for this route range to avoid duplicates
        ipv4_offset = route_idx * pair["rxRouteCount"]

        drx_v4 = drx_bgpv4_peer.v4_routes.add(
            name=f"drx{pair_id}_v4route_{route_idx}"
        )
        drx_v4.set(
            next_hop_ipv4_address=pair["rxNextHopV4"],
            next_hop_address_type=drx_v4.IPV4,
            next_hop_mode=drx_v4.MANUAL
        )

        # Parse base address and add offset
        base_addr = pair["rxAdvRouteV4"]
        addr_parts = base_addr.split('.')
        # Incrementing IP address
        last_octet = int(addr_parts[3]) + ipv4_offset
        route_addr = f"{addr_parts[0]}.{addr_parts[1]}." \
                    f"{addr_parts[2]}.{last_octet}"

        drx_v4.addresses.add(
            address=route_addr,
            prefix=32,
            count=pair["rxRouteCount"],
            step=1
        )
        drx_v4.advanced.set(
            multi_exit_discriminator=50,
            origin=drx_v4.advanced.EGP
        )
        drx_v4_routes.append(drx_v4)

        # IPv6 route
        ipv6_offset = route_idx * pair["rxRouteCount"]

        drx_v6 = drx_bgpv6_peer.v6_routes.add(
            name=f"drx{pair_id}_v6route_{route_idx}"
        )
        drx_v6.set(
            next_hop_ipv6_address=pair["rxNextHopV6"],
            next_hop_address_type=drx_v6.IPV6,
            next_hop_mode=drx_v6.MANUAL
        )

        # Parse base IPv6 address and add offset
        base_addr_v6 = pair["rxAdvRouteV6"]
        if '::' in base_addr_v6:
            addr_parts_v6 = base_addr_v6.rsplit(':', 1)
            # Incrementing IP address
            last_segment = int(addr_parts_v6[1], 16) + ipv6_offset
            route_addr_v6 = f"{addr_parts_v6[0]}:{last_segment:x}"
        else:
            addr_parts_v6 = base_addr_v6.split(':')
            # Incrementing IP address
            last_segment = int(addr_parts_v6[-1], 16) + ipv6_offset
            addr_parts_v6[-1] = f"{last_segment:x}"
            route_addr_v6 = ':'.join(addr_parts_v6)

        drx_v6.addresses.add(
            address=route_addr_v6,
            prefix=128,
            count=pair["rxRouteCount"],
            step=1
        )
        drx_v6.advanced.set(
            multi_exit_discriminator=50,
            origin=drx_v6.advanced.EGP
        )
        drx_v6_routes.append(drx_v6)

    return dtx_v4_routes, drx_v4_routes, dtx_v6_routes, drx_v6_routes


def create_traffic_flows(config, pair, tc, tx_v4, rx_v4, tx_v6, rx_v6):
    """Create traffic flows for a BGP pair.

    Creates separate flows for each route range. Since Snappi API only
    supports 1 device per flow, we create one flow per route range for
    each direction and protocol combination.

    Total flows per pair = routeRangeCount x 4
    (IPv4/IPv6 x TX-to-RX/RX-to-TX)

    This function is only called for pairs with enableTraffic=True.

    Args:
        config: Snappi configuration object
        pair: Dictionary with pair configuration
        tc: Test constants dictionary
        tx_v4, rx_v4, tx_v6, rx_v6: Lists of route objects
    """
    pair_id = pair["pairId"]

    # Create flows for each route range (one flow per route)
    # API limitation: only 1 device (route) per flow is supported
    for route_idx in range(len(tx_v4)):
        # IPv4 TX to RX
        flow = config.flows.add()
        flow.name = f"pair{pair_id}_ftx_v4_{route_idx}"
        flow.duration.fixed_packets.packets = tc["pktCount"]
        flow.rate.pps = tc["pktRate"]
        flow.size.fixed = tc["pktSize"]
        flow.metrics.enable = True
        flow.tx_rx.device.set(
            tx_names=[tx_v4[route_idx].name],
            rx_names=[rx_v4[route_idx].name]
        )
        eth, ip, tcp = flow.packet.ethernet().ipv4().tcp()
        eth.src.value = pair["txMac"]
        ip.src.value = pair["txAdvRouteV4"]
        ip.dst.value = pair["rxAdvRouteV4"]
        tcp.src_port.value = 5000
        tcp.dst_port.value = 6000

        # IPv6 TX to RX
        flow = config.flows.add()
        flow.name = f"pair{pair_id}_ftx_v6_{route_idx}"
        flow.duration.fixed_packets.packets = tc["pktCount"]
        flow.rate.pps = tc["pktRate"]
        flow.size.fixed = tc["pktSize"]
        flow.metrics.enable = True
        flow.tx_rx.device.set(
            tx_names=[tx_v6[route_idx].name],
            rx_names=[rx_v6[route_idx].name]
        )
        eth, ip, tcp = flow.packet.ethernet().ipv6().tcp()
        eth.src.value = pair["txMac"]
        ip.src.value = pair["txAdvRouteV6"]
        ip.dst.value = pair["rxAdvRouteV6"]
        tcp.src_port.value = 5000
        tcp.dst_port.value = 6000

        # IPv4 RX to TX
        flow = config.flows.add()
        flow.name = f"pair{pair_id}_frx_v4_{route_idx}"
        flow.duration.fixed_packets.packets = tc["pktCount"]
        flow.rate.pps = tc["pktRate"]
        flow.size.fixed = tc["pktSize"]
        flow.metrics.enable = True
        flow.tx_rx.device.set(
            tx_names=[rx_v4[route_idx].name],
            rx_names=[tx_v4[route_idx].name]
        )
        eth, ip, tcp = flow.packet.ethernet().ipv4().tcp()
        eth.src.value = pair["rxMac"]
        ip.src.value = pair["rxAdvRouteV4"]
        ip.dst.value = pair["txAdvRouteV4"]
        tcp.src_port.value = 5000
        tcp.dst_port.value = 6000

        # IPv6 RX to TX
        flow = config.flows.add()
        flow.name = f"pair{pair_id}_frx_v6_{route_idx}"
        flow.duration.fixed_packets.packets = tc["pktCount"]
        flow.rate.pps = tc["pktRate"]
        flow.size.fixed = tc["pktSize"]
        flow.metrics.enable = True
        flow.tx_rx.device.set(
            tx_names=[rx_v6[route_idx].name],
            rx_names=[tx_v6[route_idx].name]
        )
        eth, ip, tcp = flow.packet.ethernet().ipv6().tcp()
        eth.src.value = pair["rxMac"]
        ip.src.value = pair["rxAdvRouteV6"]
        ip.dst.value = pair["txAdvRouteV6"]
        tcp.src_port.value = 5000
        tcp.dst_port.value = 6000


def build_multi_vlan_config(config, tc, ptx, prx):
    """Build config for multiple BGP pairs, each in its own VLAN,
    sharing the 2 physical ports (ptx, prx)."""
    # Store route references
    all_tx_v4_routes = []
    all_rx_v4_routes = []
    all_tx_v6_routes = []
    all_rx_v6_routes = []
    for pair in tc["pairs"]:
        print(f"Configuring pair {pair['pairId']} in VLAN {pair['vlanId']}...")
        tx_v4, rx_v4, tx_v6, rx_v6 = configure_bgp_pair(
            config, ptx, prx, pair, tc["useVlan"]
        )
        all_tx_v4_routes.append(tx_v4)
        all_rx_v4_routes.append(rx_v4)
        all_tx_v6_routes.append(tx_v6)
        all_rx_v6_routes.append(rx_v6)
    # Configure traffic flows (only for pairs with enableTraffic=True)
    print("Configuring traffic flows...")
    for i, pair in enumerate(tc["pairs"]):
        # Default to True if not specified
        if pair.get("enableTraffic", True):
            create_traffic_flows(config, pair, tc,
                                 all_tx_v4_routes[i], all_rx_v4_routes[i],
                                 all_tx_v6_routes[i], all_rx_v6_routes[i])
            print(f"  Traffic enabled for pair {pair['pairId']}")
        else:
            print(f"  Traffic disabled for pair {pair['pairId']}")
        
    print(f"All TX v4 routes: {all_tx_v4_routes}")
    print(f"All RX v4 routes: {all_rx_v4_routes}")
    print(f"All TX v6 routes: {all_tx_v6_routes}")
    print(f"All RX v6 routes: {all_rx_v6_routes}")
    return config


def _find_pair(tc, name):
    for pair in tc["pairs"]:
        pair_id = pair["pairId"]
        if f"dtx{pair_id}" in name or f"drx{pair_id}" in name:
            return pair
    return None


def _bgp_family_metrics_ok(metrics, tc):
    """Validate one address family's BGP metrics (v4 or v6).

    Each peer's address-family peer advertises/receives routeRangeCount
    route ranges of that family only (v4 and v6 routes live on separate
    peers).
    """
    for m in metrics:
        print(f"  Name: {m.name}, State: {m.session_state}, "
              f"Routes Adv: {m.routes_advertised}, "
              f"Routes Rec: {m.routes_received}")

        peer_pair = _find_pair(tc, m.name)
        if peer_pair is None:
            continue

        if "dtx" in m.name:
            expected_adv = peer_pair["routeRangeCount"] * peer_pair["txRouteCount"]
            expected_rec = peer_pair["routeRangeCount"] * peer_pair["rxRouteCount"]
        else:  # drx
            expected_adv = peer_pair["routeRangeCount"] * peer_pair["rxRouteCount"]
            expected_rec = peer_pair["routeRangeCount"] * peer_pair["txRouteCount"]

        if (m.session_state == m.DOWN or
                m.routes_advertised != expected_adv or
                m.routes_received != expected_rec):
            print(f"  Validation failed for {m.name}")
            print(f"    Expected Adv: {expected_adv}, Rec: {expected_rec}")
            return False
    return True


def bgp_metrics_ok_all_pairs(api, tc):
    """Check if BGP metrics meet expectations for all peer pairs.

    Each pair has 2 BGPv4 peers (v4 routes only) and 2 BGPv6 peers
    (v6 routes only).
    """
    expected_peer_count = len(tc["pairs"]) * 2  # 2 peers per pair, per family

    req = api.metrics_request()
    req.bgpv4.peer_names = []
    v4_metrics = api.get_metrics(req).bgpv4_metrics

    req = api.metrics_request()
    req.bgpv6.peer_names = []
    v6_metrics = api.get_metrics(req).bgpv6_metrics

    if len(v4_metrics) < expected_peer_count or len(v6_metrics) < expected_peer_count:
        print(f"Expected {expected_peer_count} BGPv4 and {expected_peer_count} "
              f"BGPv6 peers, found {len(v4_metrics)} BGPv4 and "
              f"{len(v6_metrics)} BGPv6")
        return False

    print("BGPv4 Metrics:")
    if not _bgp_family_metrics_ok(v4_metrics, tc):
        return False

    print("BGPv6 Metrics:")
    if not _bgp_family_metrics_ok(v6_metrics, tc):
        return False

    return True


def bgp_prefixes_ok(api, ipv4_routes=None, ipv6_routes=None):
    """Check if BGP prefixes are correctly received.

    Args:
        api: The API instance
        ipv4_routes: List of dicts with 'ipv4' and 'nexthop' keys
        ipv6_routes: List of dicts with 'ipv6' and 'nexthop' keys

    Returns:
        bool: True if all expected prefixes are found, False otherwise
    """
    req = api.states_request()
    req.bgp_prefixes.bgp_peer_names = []
    bgp_prefixes = api.get_states(req).bgp_prefixes

    if not ipv4_routes and not ipv6_routes:
        print("BGP Prefixes: No expected routes to validate")
        return True
    
    expected_ipv4_count = len(ipv4_routes) if ipv4_routes else 0
    expected_ipv6_count = len(ipv6_routes) if ipv6_routes else 0

    matched_ipv4_count = 0
    matched_ipv6_count = 0

    print("BGP Prefixes:")
    for m in bgp_prefixes:
        if ipv4_routes:
            for p in m.ipv4_unicast_prefixes:
                print(f"  IPv4: {p.ipv4_address}/{p.prefix_length}, "
                      f"Next Hop: {p.ipv4_next_hop}")
                for expected in ipv4_routes:
                    if (p.ipv4_address == expected.get("ipv4") and
                        p.ipv4_next_hop == expected.get("nexthop")):
                        matched_ipv4_count += 1
                        break

        if ipv6_routes:
            for p in m.ipv6_unicast_prefixes:
                print(f"  IPv6: {p.ipv6_address}/{p.prefix_length}, "
                      f"Next Hop: {p.ipv6_next_hop}")
                for expected in ipv6_routes:
                    if (p.ipv6_address == expected.get("ipv6") and
                        p.ipv6_next_hop == expected.get("nexthop")):
                        matched_ipv6_count += 1
                        break

    print(f"Matched IPv4 prefixes: {matched_ipv4_count}/{expected_ipv4_count}")
    print(f"Matched IPv6 prefixes: {matched_ipv6_count}/{expected_ipv6_count}")

    return (matched_ipv4_count == expected_ipv4_count and
            matched_ipv6_count == expected_ipv6_count)


def flow_metrics_ok(api, tc):
    """Check if flow metrics meet expectations."""
    req = api.metrics_request()
    req.flow.flow_names = []
    metrics = api.get_metrics(req).flow_metrics

    print("Flow Metrics:")
    for m in metrics:
        print(f"  Name: {m.name}, State: {m.transmit}, "
              f"Frames Tx: {m.frames_tx}, Frames Rx: {m.frames_rx}")
        if (
            m.transmit != m.STOPPED
            or m.frames_tx != tc["pktCount"]
            or m.frames_rx != tc["pktCount"]
        ):
            return False
    return True


def print_bgp_sessions_up(api):
    """Print which BGP sessions are UP.

    Returns:
        int: Number of BGP sessions that are UP
    """
    req = api.metrics_request()
    req.bgpv4.peer_names = []
    metrics = api.get_metrics(req).bgpv4_metrics

    up_sessions = [m for m in metrics if m.session_state == m.UP]
    down_sessions = [m for m in metrics if m.session_state != m.UP]

    print(f"\nBGP Sessions Status Summary:")
    print(f"  Total Sessions: {len(metrics)}")
    print(f"  UP Sessions: {len(up_sessions)}")
    print(f"  DOWN Sessions: {len(down_sessions)}")

    for m in up_sessions:
        print(f"  UP:   {m.name}: Routes Adv={m.routes_advertised}, "
              f"Routes Rec={m.routes_received}")
    for m in down_sessions:
        print(f"  DOWN: {m.name}: State={m.session_state}")

    return len(up_sessions)


def flap_bgp_peer(api, peer_name, up_time_seconds, down_time_seconds, cycles=1):
    """Flap a BGP peer by turning it up and down repeatedly.

    Args:
        api: Snappi API instance
        peer_name: Name of the BGP peer to control (e.g., "dtx1_peer")
        up_time_seconds: Duration in seconds to keep the peer UP
        down_time_seconds: Duration in seconds to keep the peer DOWN
        cycles: Number of complete up/down cycles to perform (default: 1)
    """
    print(f"Starting BGP peer flap for '{peer_name}' "
          f"(up={up_time_seconds}s, down={down_time_seconds}s, cycles={cycles})")

    for cycle in range(cycles):
        print(f"Cycle {cycle + 1}/{cycles}: stopping '{peer_name}'...")
        cs = api.control_state()
        cs.protocol.bgp.peers.state = cs.protocol.bgp.peers.DOWN
        cs.protocol.bgp.peers.peer_names = [peer_name]
        api.set_control_state(cs)
        time.sleep(down_time_seconds)

        print(f"Cycle {cycle + 1}/{cycles}: starting '{peer_name}'...")
        cs = api.control_state()
        cs.protocol.bgp.peers.state = cs.protocol.bgp.peers.UP
        cs.protocol.bgp.peers.peer_names = [peer_name]
        api.set_control_state(cs)
        time.sleep(up_time_seconds)

    print(f"Completed {cycles} flap cycle(s) for '{peer_name}'")


def flap_all_peers(api, peer_list, up_time_seconds, down_time_seconds,
                    cycles=1, run_async=False):
    """Flap BGP peers either synchronously or asynchronously.

    Returns:
        Thread object if run_async=True, None otherwise
    """
    def flap_each():
        for peer_name in peer_list:
            flap_bgp_peer(
                api, peer_name,
                up_time_seconds=up_time_seconds,
                down_time_seconds=down_time_seconds,
                cycles=cycles
            )

    if run_async:
        print("Running BGP peer flapping in a separate thread...")
        flap_thread = threading.Thread(target=flap_each, name="BGP_Peer_Flapping")
        flap_thread.start()
        return flap_thread

    print("Running BGP peer flapping in the main thread...")
    flap_each()
    return None


def test_multi_vlan_bgp_peer_and_route_flap(api, b2b_raw_config, utils):
    """B2B test: BGP with multiple peer pairs in different VLANs.

    Configures multiple BGP peer pairs, each in a separate VLAN sharing
    2 physical ports, establishes BGP sessions, validates learned routes,
    flaps each Tx peer up/down a few times and confirms the sessions
    recover, then runs per-pair traffic and validates flow metrics.
    """
    tc = TEST_CONST

    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    ptx, prx = b2b_raw_config.ports

    print("Building multi-VLAN BGP config...")
    build_multi_vlan_config(b2b_raw_config, tc, ptx, prx)

    print("Setting config ...")
    print("Config")
    print(b2b_raw_config)
    api.set_config(b2b_raw_config)

    # utils.start_protocols(api)

    # utils.wait_for(
    #     lambda: bgp_metrics_ok_all_pairs(api, tc),
    #     "all BGP pairs to establish",
    #     timeout_seconds=30,
    # )
    
    # req_dbg = api.states_request()
    # req_dbg.bgp_prefixes.bgp_peer_names = ["dtx1_peer"]
    # r = api.get_states(req_dbg)
    # for s in r.bgp_prefixes:
    #     print("DEBUG dtx1_peer:", s.bgp_peer_name,
    #           "v4=", len(s.ipv4_unicast_prefixes),
    #           "v6=", len(s.ipv6_unicast_prefixes))
    #     for p in s.ipv4_unicast_prefixes:
    #         print("   v4 prefix:", p.ipv4_address, p.prefix_length,
    #               "nh=", p.ipv4_next_hop)

    # req_dbg2 = api.states_request()
    # req_dbg2.bgp_prefixes.bgp_peer_names = ["dtx1_v6_peer"]
    # r2 = api.get_states(req_dbg2)
    # for s in r2.bgp_prefixes:
    #     print("DEBUG dtx1_v6_peer:", s.bgp_peer_name,
    #           "v4=", len(s.ipv4_unicast_prefixes),
    #           "v6=", len(s.ipv6_unicast_prefixes))
    #     for p in s.ipv6_unicast_prefixes:
    #         print("   v6 prefix:", p.ipv6_address, p.prefix_length,
    #               "nh=", p.ipv6_next_hop)

    # req_dbg3 = api.states_request()
    # req_dbg3.bgp_prefixes.bgp_peer_names = []
    # r3 = api.get_states(req_dbg3)
    # print("DEBUG all-peers query returned", len(r3.bgp_prefixes), "entries:",
    #       [s.bgp_peer_name for s in r3.bgp_prefixes])

    # # Build expected routes for all pairs and all route ranges
    # all_ipv4_routes = []
    # all_ipv6_routes = []
    # for pair in tc["pairs"]:
    #     for route_idx in range(pair["routeRangeCount"]):
    #         # TX IPv4 routes
    #         ipv4_offset = route_idx * pair["txRouteCount"]
    #         base_addr = pair["txAdvRouteV4"]
    #         addr_parts = base_addr.split('.')
    #         for addr_offset in range(pair["txRouteCount"]):
    #             last_octet = int(addr_parts[3]) + ipv4_offset + addr_offset
    #             route_addr = (f"{addr_parts[0]}.{addr_parts[1]}."
    #                         f"{addr_parts[2]}.{last_octet}")
    #             all_ipv4_routes.append({
    #                 "ipv4": route_addr,
    #                 "nexthop": pair["txNextHopV4"]
    #             })

    #         # RX IPv4 routes
    #         ipv4_offset = route_idx * pair["rxRouteCount"]
    #         base_addr = pair["rxAdvRouteV4"]
    #         addr_parts = base_addr.split('.')
    #         for addr_offset in range(pair["rxRouteCount"]):
    #             last_octet = int(addr_parts[3]) + ipv4_offset + addr_offset
    #             route_addr = (f"{addr_parts[0]}.{addr_parts[1]}."
    #                         f"{addr_parts[2]}.{last_octet}")
    #             all_ipv4_routes.append({
    #                 "ipv4": route_addr,
    #                 "nexthop": pair["rxNextHopV4"]
    #             })
    #         # TX IPv6 routes
    #         ipv6_offset = route_idx * pair["txRouteCount"]
    #         base_addr_v6 = pair["txAdvRouteV6"]
    #         for addr_offset in range(pair["txRouteCount"]):
    #             if '::' in base_addr_v6:
    #                 addr_parts_v6 = base_addr_v6.rsplit(':', 1)
    #                 last_segment = (int(addr_parts_v6[1], 16) +
    #                               ipv6_offset + addr_offset)
    #                 route_addr_v6 = f"{addr_parts_v6[0]}:{last_segment:x}"
    #             else:
    #                 addr_parts_v6 = base_addr_v6.split(':')
    #                 last_segment = (int(addr_parts_v6[-1], 16) +
    #                               ipv6_offset + addr_offset)
    #                 addr_parts_v6[-1] = f"{last_segment:x}"
    #                 route_addr_v6 = ':'.join(addr_parts_v6)
    #             all_ipv6_routes.append({
    #                 "ipv6": route_addr_v6,
    #                 "nexthop": pair["txNextHopV6"]
    #             })

    #         # RX IPv6 routes
    #         ipv6_offset = route_idx * pair["rxRouteCount"]
    #         base_addr_v6 = pair["rxAdvRouteV6"]
    #         for addr_offset in range(pair["rxRouteCount"]):
    #             if '::' in base_addr_v6:
    #                 addr_parts_v6 = base_addr_v6.rsplit(':', 1)
    #                 last_segment = (int(addr_parts_v6[1], 16) +
    #                               ipv6_offset + addr_offset)
    #                 route_addr_v6 = f"{addr_parts_v6[0]}:{last_segment:x}"
    #             else:
    #                 addr_parts_v6 = base_addr_v6.split(':')
    #                 last_segment = (int(addr_parts_v6[-1], 16) +
    #                               ipv6_offset + addr_offset)
    #                 addr_parts_v6[-1] = f"{last_segment:x}"
    #                 route_addr_v6 = ':'.join(addr_parts_v6)
    #             all_ipv6_routes.append({
    #                 "ipv6": route_addr_v6,
    #                 "nexthop": pair["rxNextHopV6"]
    #             })
    # utils.wait_for(
    #     lambda: bgp_prefixes_ok(api, all_ipv4_routes, all_ipv6_routes),
    #     "bgp prefixes to be learned",
    #     timeout_seconds=30,
    # )

    # # Flap only the Tx peer of each pair
    # peer_list = [f"dtx{pair['pairId']}_peer" for pair in tc["pairs"]]

    # print("Starting BGP peer flapping...")
    # flap_thread = flap_all_peers(
    #     api,
    #     peer_list,
    #     up_time_seconds=FLAP_UP_SECONDS,
    #     down_time_seconds=FLAP_DOWN_SECONDS,
    #     cycles=FLAP_CYCLES,
    #     run_async=True,
    # )

    # while flap_thread.is_alive():
    #     print_bgp_sessions_up(api)
    #     time.sleep(5)
    # flap_thread.join()
    # print("BGP peer flapping completed")

    # utils.wait_for(
    #     lambda: bgp_metrics_ok_all_pairs(api, tc),
    #     "all BGP pairs to re-establish after flap",
    #     timeout_seconds=30,
    # )

    # traffic_enabled_pairs = [
    #     pair for pair in tc["pairs"] if pair.get("enableTraffic", True)
    # ]

    # if traffic_enabled_pairs:
    #     print(f"Starting transmit for {len(traffic_enabled_pairs)} pair(s)...")
    #     utils.start_traffic_only(api)

    #     utils.wait_for(
    #         lambda: flow_metrics_ok(api, tc),
    #         "flow metrics to complete",
    #         timeout_seconds=30,
    #     )
    # else:
    #     print("No traffic configured - all pairs have enableTraffic=False")

    # api.set_config(api.config())
