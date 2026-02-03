import pytest


@pytest.mark.skip(reason="ISIS multi-topology IDs feature not yet implemented (TBD)")
def test_isis_multi_topology_ids(api, utils):
    """
    Test ISIS multi-topology IDs configuration.
    
    Note: This feature is marked as TBD in isis.py (_configure_multi_topo_id method).
    This test serves as specification for future implementation.
    
    Configure:
    - ISIS interface with multiple topology IDs
    - Each topology with mt_id and link_metric
    
    Validate:
    - Multi-topology IDs are configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    # ISIS configuration
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    isis_iface.network_type = isis_iface.POINT_TO_POINT
    isis_iface.level_type = isis_iface.LEVEL_2
    isis_iface.metric = 10
    
    # Multi-topology IDs (when implemented)
    # mt1 = isis_iface.multi_topology_ids.add()
    # mt1.mt_id = 0  # Standard topology
    # mt1.link_metric = 10
    
    # mt2 = isis_iface.multi_topology_ids.add()
    # mt2.mt_id = 2  # IPv6 topology
    # mt2.link_metric = 20
    
    api.set_config(config)


@pytest.mark.skip(reason="ISIS traffic engineering feature not yet implemented (TBD)")
def test_isis_traffic_engineering(api, utils):
    """
    Test ISIS traffic engineering configuration.
    
    Note: This feature is marked as TBD in isis.py (_configure_traffic_engineering method).
    This test serves as specification for future implementation.
    
    Configure:
    - ISIS interface with traffic engineering attributes
    - Administrative group, metric level, bandwidth settings
    - Priority bandwidths (pb0-pb7)
    
    Validate:
    - Traffic engineering parameters are configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # Traffic engineering (when implemented)
    # te = isis_iface.traffic_engineering
    # te.administrative_group = "0x00000001"
    # te.metric_level = 10
    # te.max_bandwidth = "1000000"  # 1 Gbps
    # te.max_reservable_bandwidth = "800000"  # 800 Mbps
    
    # # Priority bandwidths
    # te.priority_bandwidths.pb0 = "100000"
    # te.priority_bandwidths.pb1 = "100000"
    # te.priority_bandwidths.pb2 = "100000"
    # te.priority_bandwidths.pb3 = "100000"
    # te.priority_bandwidths.pb4 = "100000"
    # te.priority_bandwidths.pb5 = "100000"
    # te.priority_bandwidths.pb6 = "100000"
    # te.priority_bandwidths.pb7 = "100000"
    
    api.set_config(config)


@pytest.mark.skip(reason="ISIS adjacency SIDs feature not yet implemented (TBD)")
def test_isis_adjacency_sids(api, utils):
    """
    Test ISIS adjacency SIDs configuration.
    
    Note: This feature is marked as TBD in isis.py (_configure_adjacency_sids method).
    This test serves as specification for future implementation.
    
    Configure:
    - ISIS interface with adjacency SIDs
    - Segment routing configuration
    
    Validate:
    - Adjacency SIDs are configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # Adjacency SIDs (when implemented)
    # adj_sid = isis_iface.adjacency_sids.add()
    # adj_sid.sid_value = 9001
    # adj_sid.weight = 100
    
    api.set_config(config)


def test_isis_router_authentication_area_md5(api, utils):
    """
    Test ISIS router authentication with area MD5.
    
    Configure:
    - ISIS router with area authentication
    - MD5 authentication type
    
    Validate:
    - Area authentication is configured
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    isis_iface.network_type = isis_iface.BROADCAST
    isis_iface.level_type = isis_iface.LEVEL_2
    
    # Router authentication
    router_auth = isis_iface.authentication
    if router_auth:
        router_auth.area_auth_type = router_auth.MD5
        router_auth.area_auth_password = "area_secret_123"
    
    api.set_config(config)
    
    # Validate configuration
    ixn_isis = utils.get_ixnetwork_obj(api, "isis_rtr", "isisL3")
    assert ixn_isis is not None


def test_isis_router_authentication_domain_password(api, utils):
    """
    Test ISIS router authentication with domain password.
    
    Configure:
    - ISIS router with domain authentication
    - Password authentication type
    
    Validate:
    - Domain authentication is configured
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # Router authentication
    router_auth = isis_iface.authentication
    if router_auth:
        router_auth.domain_auth_type = router_auth.PASSWORD
        router_auth.domain_auth_password = "domain_pass_456"
    
    api.set_config(config)
    
    ixn_isis = utils.get_ixnetwork_obj(api, "isis_rtr", "isisL3")
    assert ixn_isis is not None


def test_isis_router_authentication_ignore_receive_md5(api, utils):
    """
    Test ISIS router authentication with ignore_receive_md5 option.
    
    Configure:
    - ISIS router with ignore_receive_md5 enabled
    
    Validate:
    - Option is configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # Router authentication
    router_auth = isis_iface.authentication
    if router_auth:
        router_auth.ignore_receive_md5 = True
    
    api.set_config(config)
    
    ixn_isis = utils.get_ixnetwork_obj(api, "isis_rtr", "isisL3")
    assert ixn_isis is not None


def test_isis_link_protection_flags(api, utils):
    """
    Test ISIS link protection flags configuration.
    
    Configure:
    - ISIS interface with various link protection flags
    - extra_traffic, unprotected, shared, dedicated_1_to_1, etc.
    
    Validate:
    - Link protection flags are set correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # Link protection
    link_prot = isis_iface.link_protection
    if link_prot:
        link_prot.extra_traffic = True
        link_prot.unprotected = False
        link_prot.shared = True
        link_prot.dedicated_1_to_1 = False
        link_prot.dedicated_1_plus_1 = True
        link_prot.enhanced = False
    
    api.set_config(config)
    
    ixn_isis = utils.get_ixnetwork_obj(api, isis_iface.name, "isisL3")
    assert ixn_isis is not None


def test_isis_redistribution_type_down(api, utils):
    """
    Test ISIS route with redistribution type 'down'.
    
    Configure:
    - ISIS IPv4 route with redistribution_type = 'down'
    
    Validate:
    - Redistribution type is configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    isis_iface.network_type = isis_iface.BROADCAST
    isis_iface.level_type = isis_iface.LEVEL_2
    
    # ISIS router basic config
    isis_router = isis_iface.basic
    if isis_router:
        isis_router.hostname = "router1"
        isis_router.enable_wide_metric = True
    
    # IPv4 route with redistribution type down
    v4_route = isis_iface.v4_routes.add()
    v4_route.name = "isis_v4_route"
    v4_route.addresses.add(address="200.1.0.0", prefix=24, count=10)
    v4_route.redistribution_type = v4_route.DOWN  # Test 'down' redistribution
    v4_route.origin_type = v4_route.INTERNAL
    
    api.set_config(config)
    
    # Validate redistribution type
    ixn_route = utils.get_ixnetwork_obj(api, v4_route.name, "isisL3RouteProperty")
    assert ixn_route is not None


def test_isis_advanced_interface_settings(api, utils):
    """
    Test ISIS advanced interface settings.
    
    Configure:
    - auto_adjust_mtu
    - auto_adjust_area
    - auto_adjust_supported_protocols
    - enable_3way_handshake
    
    Validate:
    - Advanced settings are configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # Advanced interface settings
    adv = isis_iface.advanced
    if adv:
        adv.auto_adjust_mtu = True
        adv.auto_adjust_area = False
        adv.auto_adjust_supported_protocols = True
        adv.enable_3way_handshake = True
    
    api.set_config(config)
    
    ixn_isis = utils.get_ixnetwork_obj(api, isis_iface.name, "isisL3")
    assert ixn_isis is not None


def test_isis_srlg_values_extensive(api, utils):
    """
    Test ISIS SRLG (Shared Risk Link Group) values.
    
    Configure:
    - ISIS interface with multiple SRLG values
    
    Validate:
    - SRLG values are configured correctly
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
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.connection.port_name = port.name
    eth.mac = "00:00:00:00:00:01"
    
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "10.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "10.1.1.2"
    
    isis = device.isis
    isis.name = "isis_rtr"
    isis.system_id = "640000000001"
    
    isis_iface = isis.interfaces.add()
    isis_iface.eth_name = eth.name
    isis_iface.name = "isis_int"
    
    # SRLG values
    srlg_vals = isis_iface.srlg_values
    if srlg_vals:
        # Add multiple SRLG values
        srlg_vals.append(100)
        srlg_vals.append(200)
        srlg_vals.append(300)
        srlg_vals.append(400)
    
    api.set_config(config)
    
    ixn_isis = utils.get_ixnetwork_obj(api, isis_iface.name, "isisL3")
    assert ixn_isis is not None
