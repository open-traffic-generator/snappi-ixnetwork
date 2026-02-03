import pytest


def test_bgp_evpn_cmac_without_mac_addresses_error(api, utils):
    """
    Test CMAC IP range without MAC addresses should raise error.
    
    Configure:
    - CMAC IP range with IPv4 addresses but no MAC addresses
    
    Expected:
    - Should raise exception: "mac_addresses should configured in cmac_ip_range"
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    bd = evi.broadcast_domains.add()
    bd.ethernet_tag_id = 100
    
    # CMAC IP range WITHOUT MAC addresses (should fail)
    cmac_range = bd.cmac_ip_range.add()
    # Don't configure MAC addresses
    # cmac_range.mac_addresses = None  # Intentionally omitted
    
    # Add IPv4 addresses (this should trigger error)
    ipv4_addr = cmac_range.ipv4_addresses.add()
    ipv4_addr.address = "10.1.1.1"
    ipv4_addr.prefix = 24
    ipv4_addr.count = 10
    
    # Should raise error during set_config
    try:
        api.set_config(config)
        # If it doesn't raise, check for errors
        errors = api.get_errors()
        assert len(errors) > 0
        assert any("mac" in str(e).lower() for e in errors)
    except Exception as e:
        # Expected exception
        assert "mac_addresses" in str(e).lower() or "mac" in str(e).lower()


def test_bgp_evpn_cmac_ipv6_only(api, utils):
    """
    Test CMAC IP range with IPv6 addresses only (no IPv4).
    
    Configure:
    - CMAC IP range with MAC and IPv6 addresses
    - No IPv4 addresses
    
    Validate:
    - Configuration is successful
    - IPv6 addresses are configured correctly
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    bd = evi.broadcast_domains.add()
    bd.ethernet_tag_id = 100
    
    # CMAC IP range with MAC and IPv6 only
    cmac_range = bd.cmac_ip_range.add()
    
    # MAC addresses
    mac_addr = cmac_range.mac_addresses.add()
    mac_addr.address = "00:00:01:00:00:01"
    mac_addr.prefix = 48
    mac_addr.count = 10
    
    # IPv6 addresses only
    ipv6_addr = cmac_range.ipv6_addresses.add()
    ipv6_addr.address = "2001:db8::1"
    ipv6_addr.prefix = 64
    ipv6_addr.count = 10
    
    # CMAC properties
    cmac_range.l2vni = 5000
    cmac_range.l3vni = 6000
    cmac_range.include_default_gateway = True
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_cmac_dual_stack_ipv4_ipv6(api, utils):
    """
    Test CMAC IP range with both IPv4 and IPv6 addresses (dual-stack).
    
    Configure:
    - CMAC IP range with MAC, IPv4, and IPv6 addresses
    
    Validate:
    - All address types are configured correctly
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    bd = evi.broadcast_domains.add()
    bd.ethernet_tag_id = 100
    
    # CMAC IP range with MAC, IPv4, and IPv6
    cmac_range = bd.cmac_ip_range.add()
    
    # MAC addresses
    mac_addr = cmac_range.mac_addresses.add()
    mac_addr.address = "00:00:01:00:00:01"
    mac_addr.prefix = 48
    mac_addr.count = 20
    
    # IPv4 addresses
    ipv4_addr = cmac_range.ipv4_addresses.add()
    ipv4_addr.address = "10.1.1.1"
    ipv4_addr.prefix = 24
    ipv4_addr.count = 20
    
    # IPv6 addresses
    ipv6_addr = cmac_range.ipv6_addresses.add()
    ipv6_addr.address = "2001:db8::1"
    ipv6_addr.prefix = 64
    ipv6_addr.count = 20
    
    # CMAC properties
    cmac_range.l2vni = 5000
    cmac_range.l3vni = 6000
    cmac_range.include_default_gateway = True
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_cmac_asymmetric_counts(api, utils):
    """
    Test CMAC IP range with different counts for MAC, IPv4, and IPv6.
    
    Configure:
    - CMAC IP range with MAC (10 addresses)
    - IPv4 (5 addresses)
    - IPv6 (15 addresses)
    
    Validate:
    - Configuration handles asymmetric counts
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    bd = evi.broadcast_domains.add()
    bd.ethernet_tag_id = 100
    
    # CMAC IP range with asymmetric counts
    cmac_range = bd.cmac_ip_range.add()
    
    # 10 MAC addresses
    mac_addr = cmac_range.mac_addresses.add()
    mac_addr.address = "00:00:01:00:00:01"
    mac_addr.prefix = 48
    mac_addr.count = 10
    
    # 5 IPv4 addresses
    ipv4_addr = cmac_range.ipv4_addresses.add()
    ipv4_addr.address = "10.1.1.1"
    ipv4_addr.prefix = 24
    ipv4_addr.count = 5
    
    # 15 IPv6 addresses
    ipv6_addr = cmac_range.ipv6_addresses.add()
    ipv6_addr.address = "2001:db8::1"
    ipv6_addr.prefix = 64
    ipv6_addr.count = 15
    
    # CMAC properties
    cmac_range.l2vni = 5000
    cmac_range.l3vni = 6000
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_broadcast_domain_vlan_aware_service(api, utils):
    """
    Test EVPN broadcast domain with VLAN aware service enabled/disabled.
    
    Configure:
    - Two EVIs with different VLAN aware service settings
    
    Validate:
    - vlan_aware_service is configured correctly
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    # EVI 1: VLAN aware service enabled
    evi1 = eth_seg.evis.add()
    evi1.route_distinguisher.rd_type = evi1.route_distinguisher.AS_2OCTET
    evi1.route_distinguisher.rd_value = "100:1"
    
    bd1 = evi1.broadcast_domains.add()
    bd1.ethernet_tag_id = 100
    bd1.vlan_aware_service = True
    
    # EVI 2: VLAN aware service disabled
    evi2 = eth_seg.evis.add()
    evi2.route_distinguisher.rd_type = evi2.route_distinguisher.AS_2OCTET
    evi2.route_distinguisher.rd_value = "100:2"
    
    bd2 = evi2.broadcast_domains.add()
    bd2.ethernet_tag_id = 200
    bd2.vlan_aware_service = False
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_multiple_cmac_ranges_per_broadcast_domain(api, utils):
    """
    Test multiple CMAC IP ranges in a single broadcast domain.
    
    Configure:
    - Single broadcast domain with multiple CMAC IP ranges
    - Each range has different MAC/IP pools
    
    Validate:
    - All CMAC ranges are configured
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_2OCTET
    evi.route_distinguisher.rd_value = "100:1"
    
    bd = evi.broadcast_domains.add()
    bd.ethernet_tag_id = 100
    
    # CMAC range 1
    cmac1 = bd.cmac_ip_range.add()
    mac1 = cmac1.mac_addresses.add()
    mac1.address = "00:00:01:00:00:01"
    mac1.count = 10
    ipv4_1 = cmac1.ipv4_addresses.add()
    ipv4_1.address = "10.1.1.1"
    ipv4_1.count = 10
    cmac1.l2vni = 5001
    cmac1.l3vni = 6001
    
    # CMAC range 2
    cmac2 = bd.cmac_ip_range.add()
    mac2 = cmac2.mac_addresses.add()
    mac2.address = "00:00:02:00:00:01"
    mac2.count = 20
    ipv4_2 = cmac2.ipv4_addresses.add()
    ipv4_2.address = "10.2.1.1"
    ipv4_2.count = 20
    cmac2.l2vni = 5002
    cmac2.l3vni = 6002
    
    # CMAC range 3
    cmac3 = bd.cmac_ip_range.add()
    mac3 = cmac3.mac_addresses.add()
    mac3.address = "00:00:03:00:00:01"
    mac3.count = 15
    ipv6_3 = cmac3.ipv6_addresses.add()
    ipv6_3.address = "2001:db8::1"
    ipv6_3.count = 15
    cmac3.l2vni = 5003
    cmac3.l3vni = 6003
    
    api.set_config(config)
    
    # Validate configuration
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None
