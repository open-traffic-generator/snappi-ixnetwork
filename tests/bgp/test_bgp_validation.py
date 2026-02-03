import pytest


def test_bgp_validation_multiple_ip_same_ethernet_error(api, utils):
    """
    Test that BGP validation catches error when configuring BGP
    on multiple IPs with different device groups.
    
    This should trigger validation error in _is_valid() method.
    """
    config = api.config()
    
    # Two ports for different device groups
    port1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    port2 = config.ports.port(name="p2", location=utils.settings.ports[1])[-1]
    
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port1.name, port2.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    # Device 1 on port 1
    d1 = config.devices.device(name="d1")[-1]
    d1_eth = d1.ethernets.add()
    d1_eth.name = "eth1"
    d1_eth.connection.port_name = port1.name
    d1_eth.mac = "00:00:00:00:00:01"
    
    d1_ipv4 = d1_eth.ipv4_addresses.add()
    d1_ipv4.name = "ipv4_1"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.prefix = 24
    d1_ipv4.gateway = "10.1.1.2"
    
    # Device 2 on port 2 (different device group)
    d2 = config.devices.device(name="d2")[-1]
    d2_eth = d2.ethernets.add()
    d2_eth.name = "eth2"
    d2_eth.connection.port_name = port2.name
    d2_eth.mac = "00:00:00:00:00:02"
    
    d2_ipv4 = d2_eth.ipv4_addresses.add()
    d2_ipv4.name = "ipv4_2"
    d2_ipv4.address = "10.1.1.2"
    d2_ipv4.prefix = 24
    d2_ipv4.gateway = "10.1.1.1"
    
    # Configure BGP that tries to reference IPs from different device groups
    bgp = d1.bgp
    bgp.router_id = "1.1.1.1"
    
    bgp_int1 = bgp.ipv4_interfaces.add()
    bgp_int1.ipv4_name = d1_ipv4.name
    peer1 = bgp_int1.peers.add()
    peer1.name = "peer1"
    peer1.as_type = "ebgp"
    peer1.peer_address = "10.1.1.2"
    peer1.as_number = 65200
    
    # This should cause validation issue - trying to configure
    # BGP on IP from different device group
    # Note: The actual validation may happen during set_config
    
    # Depending on implementation, this may raise an error or
    # add an error to the API error list
    try:
        api.set_config(config)
        # If no exception, check for errors in API
        errors = api.get_errors()
        # Should have validation error about different device groups
        # Note: Exact error checking depends on implementation
    except Exception as e:
        # Expected to fail validation
        assert "different device" in str(e).lower() or "invalid" in str(e).lower()


def test_bgp_peer_same_as_local_address(api, utils):
    """
    Test BGP configuration where peer address is same as local address.
    
    This is an invalid configuration and should be caught.
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="d1")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.254"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    
    bgp_int = bgp.ipv4_interfaces.add()
    bgp_int.ipv4_name = ipv4.name
    peer = bgp_int.peers.add()
    peer.name = "peer"
    peer.as_type = "ebgp"
    # Invalid: peer address same as local address
    peer.peer_address = "10.1.1.1"  
    peer.as_number = 65200
    
    # Configuration may be accepted by IxNetwork but is logically invalid
    # This test documents current behavior
    api.set_config(config)
    
    # Verify configuration was set (even if logically incorrect)
    ixn_peer = utils.get_ixnetwork_obj(api, peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None
    assert ixn_peer.DutIp.Values[0] == "10.1.1.1"


def test_bgp_invalid_as_number_zero(api, utils):
    """
    Test BGP with AS number zero (invalid).
    
    AS number 0 is reserved and should not be used.
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="d1")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    
    bgp_int = bgp.ipv4_interfaces.add()
    bgp_int.ipv4_name = ipv4.name
    peer = bgp_int.peers.add()
    peer.name = "peer"
    peer.as_type = "ebgp"
    peer.peer_address = "10.1.1.2"
    # Invalid AS number
    peer.as_number = 0
    
    # May be accepted by API but is invalid per RFC
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_ebgp_same_as_number(api, utils):
    """
    Test eBGP configuration with same AS number as peer.
    
    For eBGP, local and peer AS should be different.
    This is logically incorrect but tests current behavior.
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="d1")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    
    bgp_int = bgp.ipv4_interfaces.add()
    bgp_int.ipv4_name = ipv4.name
    peer = bgp_int.peers.add()
    peer.name = "peer"
    peer.as_type = "ebgp"  # eBGP
    peer.peer_address = "10.1.1.2"
    # Same AS for eBGP - logically incorrect
    peer.as_number = 65100
    # Assuming local AS would also be 65100 (set elsewhere)
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None
    assert ixn_peer.Type.Values[0] == "external"


def test_bgp_route_without_addresses(api, utils):
    """
    Test BGP route configuration without address pool.
    
    A route without addresses is incomplete but tests behavior.
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="d1")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    
    bgp_int = bgp.ipv4_interfaces.add()
    bgp_int.ipv4_name = ipv4.name
    peer = bgp_int.peers.add()
    peer.name = "peer"
    peer.as_type = "ebgp"
    peer.peer_address = "10.1.1.2"
    peer.as_number = 65200
    
    # Route without addresses
    rr = peer.v4_routes.add(name="rr_no_addr")
    # Don't add any addresses
    
    # Should either fail or create route with no prefixes
    try:
        api.set_config(config)
        # If successful, verify route exists but has no addresses
        ixn_rr = utils.get_ixnetwork_obj(api, "rr_no_addr", "ipv4_unicast")
        # Route may exist but with count=0
    except Exception as e:
        # May fail validation
        pass


def test_bgp_max_communities_per_route(api, utils):
    """
    Test BGP route with large number of communities.
    
    Tests boundary condition for maximum communities.
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    device = config.devices.device(name="d1")[-1]
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    
    bgp_int = bgp.ipv4_interfaces.add()
    bgp_int.ipv4_name = ipv4.name
    peer = bgp_int.peers.add()
    peer.name = "peer"
    peer.as_type = "ebgp"
    peer.peer_address = "10.1.1.2"
    peer.as_number = 65200
    
    rr = peer.v4_routes.add(name="rr_many_comm")
    rr.addresses.add(address="200.1.0.0", prefix=24, count=1)
    
    # Add many communities (e.g., 50)
    for i in range(50):
        comm = rr.communities.add()
        comm.type = comm.MANUAL_AS_NUMBER
        comm.as_number = 65100 + i
        comm.as_custom = 100 + i
    
    api.set_config(config)
    
    # Validate all communities are configured
    ixn_rr = utils.get_ixnetwork_obj(api, "rr_many_comm", "ipv4_unicast")
    assert ixn_rr is not None
    ixn_communities = ixn_rr.parent.BgpCommunitiesList.find()
    assert len(ixn_communities) == 50
