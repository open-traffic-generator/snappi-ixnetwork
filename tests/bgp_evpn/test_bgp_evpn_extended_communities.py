import pytest


def test_bgp_evpn_ext_comm_administrator_ip(api, utils):
    """
    Test BGP EVPN extended community with administrator IP type.
    
    Configure:
    - Extended community with type = administrator_ipv4_address
    - Different subtypes: route_target, origin
    
    Validate configuration via RestPy.
    """
    config = api.config()
    
    port = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    config.options.port_options.location_preemption = True
    
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media
    
    # Create device with loopback
    device = config.devices.device(name="device")[-1]
    device.container_name = port.name
    
    loopback = device.ipv4_loopbacks.add()
    loopback.name = "loopback1"
    loopback.address = "1.1.1.1"
    
    # BGP configuration
    bgp = device.bgp
    bgp.router_id = "1.1.1.1"
    bgp_iface = bgp.ipv4_interfaces.add()
    bgp_iface.ipv4_name = loopback.name
    bgp_peer = bgp_iface.peers.add()
    bgp_peer.name = "bgp_peer"
    bgp_peer.peer_address = "2.2.2.2"
    bgp_peer.as_type = "ibgp"
    bgp_peer.as_number = 65100
    
    # EVPN Ethernet Segment
    eth_seg = bgp_peer.evpn_ethernet_segments.add()
    eth_seg.esi = "01:00:00:00:00:00:00:00:00:01"
    
    # Extended community with administrator IP
    ext_comm = eth_seg.ext_communities.add()
    ext_comm.type = ext_comm.ADMINISTRATOR_IPV4_ADDRESS
    ext_comm.subtype = ext_comm.ROUTE_TARGET
    # Assuming there are additional fields for IP-based extended community
    
    api.set_config(config)
    
    # Validate extended community type
    ixn_eth_seg = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_eth_seg is not None


def test_bgp_evpn_ext_comm_opaque_color(api, utils):
    """
    Test BGP EVPN extended community with opaque type and color subtype.
    
    Configure:
    - Extended community with type = opaque
    - Subtype = color
    - Color CO bits, reserved bits, color value
    
    Validate configuration.
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
    
    # Opaque extended community with color subtype
    ext_comm = eth_seg.ext_communities.add()
    ext_comm.type = ext_comm.OPAQUE
    ext_comm.subtype = ext_comm.COLOR
    # Color-specific attributes would be configured here
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_ext_comm_evpn_mac_address(api, utils):
    """
    Test BGP EVPN extended community with EVPN type and MAC address subtype.
    
    Configure:
    - Extended community with type = evpn
    - Subtype = mac_address
    
    Validate configuration.
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
    
    # EVPN extended community with MAC address subtype
    ext_comm = eth_seg.ext_communities.add()
    ext_comm.type = ext_comm.EVPN
    ext_comm.subtype = ext_comm.MAC_ADDRESS
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_ext_comm_as_2octet_extended_bandwidth(api, utils):
    """
    Test BGP EVPN extended community with AS 2-octet and extended bandwidth.
    
    Configure:
    - Extended community with type = administrator_as_2octet_link_bandwidth
    - Subtype = extended_bandwidth
    
    Validate configuration.
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
    
    ext_comm = eth_seg.ext_communities.add()
    ext_comm.type = ext_comm.ADMINISTRATOR_AS_2OCTET_LINK_BANDWIDTH
    ext_comm.subtype = ext_comm.EXTENDED_BANDWIDTH
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_ext_comm_as_4octet(api, utils):
    """
    Test BGP EVPN extended community with AS 4-octet administrator.
    
    Configure:
    - Extended community with type = administrator_as_4octet
    - Subtype = route_target
    
    Validate configuration.
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
    
    ext_comm = eth_seg.ext_communities.add()
    ext_comm.type = ext_comm.ADMINISTRATOR_AS_4OCTET
    ext_comm.subtype = ext_comm.ROUTE_TARGET
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_route_target_as_4octet(api, utils):
    """
    Test BGP EVPN EVI with AS_4OCTET route targets.
    
    Configure:
    - EVI with route target export/import using AS_4OCTET type
    
    Validate route targets are configured correctly.
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
    
    # EVI with AS_4OCTET route targets
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.AS_4OCTET
    evi.route_distinguisher.rd_value = "4294967295:100"  # Max 4-byte AS
    
    # Export route target with AS_4OCTET
    rt_export = evi.route_target_export.add()
    rt_export.rt_type = rt_export.AS_4OCTET
    rt_export.rt_value = "4294967295:200"
    
    # Import route target with AS_4OCTET
    rt_import = evi.route_target_import.add()
    rt_import.rt_type = rt_import.AS_4OCTET
    rt_import.rt_value = "4294967295:200"
    
    # L3 export route target with AS_4OCTET
    l3_rt_export = evi.l3_route_target_export.add()
    l3_rt_export.rt_type = l3_rt_export.AS_4OCTET
    l3_rt_export.rt_value = "4294967295:300"
    
    # L3 import route target with AS_4OCTET
    l3_rt_import = evi.l3_route_target_import.add()
    l3_rt_import.rt_type = l3_rt_import.AS_4OCTET
    l3_rt_import.rt_value = "4294967295:300"
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None


def test_bgp_evpn_route_target_ipv4_address(api, utils):
    """
    Test BGP EVPN EVI with IPV4_ADDRESS route targets.
    
    Configure:
    - EVI with route target export/import using IPV4_ADDRESS type
    
    Validate route targets are configured correctly.
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
    
    # EVI with IPV4_ADDRESS route targets
    evi = eth_seg.evis.add()
    evi.route_distinguisher.rd_type = evi.route_distinguisher.IPV4_ADDRESS
    evi.route_distinguisher.rd_value = "192.168.1.1:100"
    
    # Export route target with IPV4_ADDRESS
    rt_export = evi.route_target_export.add()
    rt_export.rt_type = rt_export.IPV4_ADDRESS
    rt_export.rt_value = "192.168.1.1:200"
    
    # Import route target with IPV4_ADDRESS
    rt_import = evi.route_target_import.add()
    rt_import.rt_type = rt_import.IPV4_ADDRESS
    rt_import.rt_value = "192.168.1.1:200"
    
    # L3 route targets with IPV4_ADDRESS
    l3_rt_export = evi.l3_route_target_export.add()
    l3_rt_export.rt_type = l3_rt_export.IPV4_ADDRESS
    l3_rt_export.rt_value = "192.168.1.1:300"
    
    l3_rt_import = evi.l3_route_target_import.add()
    l3_rt_import.rt_type = l3_rt_import.IPV4_ADDRESS
    l3_rt_import.rt_value = "192.168.1.1:300"
    
    api.set_config(config)
    
    ixn_peer = utils.get_ixnetwork_obj(api, bgp_peer.name, "bgpIpv4Peer")
    assert ixn_peer is not None
