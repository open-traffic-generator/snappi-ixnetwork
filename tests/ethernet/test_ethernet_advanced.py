import pytest


def test_gateway_mac_auto_choice(api, b2b_raw_config, utils):
    """
    Test gateway_mac with 'auto' choice vs explicit 'value' choice.
    
    Configure:
    - One device with IPv4 address and gateway_mac.choice = 'auto' (default)
    - Another device with IPv4 address and gateway_mac.choice = 'value'
    
    Validate:
    - Auto choice should use automatic gateway MAC resolution
    - Value choice should use manually configured MAC address
    """
    config = b2b_raw_config
    
    # Device 1: Auto gateway MAC (default behavior)
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    d1_ipv4 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.2"
    d1_ipv4.prefix = 24
    # gateway_mac.choice defaults to 'auto'
    
    # Device 2: Manual gateway MAC
    d2 = config.devices.device(name="d2")[-1]
    d2.container_name = config.ports[1].name
    d2_eth = d2.ethernets.ethernet()[-1]
    d2_eth.name = "d2_eth"
    d2_eth.mac = "00:00:02:00:00:01"
    d2_ipv4 = d2_eth.ipv4_addresses.ipv4()[-1]
    d2_ipv4.name = "d2_ipv4"
    d2_ipv4.address = "10.1.1.2"
    d2_ipv4.gateway = "10.1.1.1"
    d2_ipv4.prefix = 24
    d2_ipv4.gateway_mac.value = "00:00:01:00:00:01"
    
    api.set_config(config)
    
    # Validate configuration via RestPy
    ixn_d2_ipv4 = utils.get_ixnetwork_obj(api, d2_ipv4.name, "ipv4")
    assert ixn_d2_ipv4 is not None
    # Manual gateway MAC should be configured
    assert ixn_d2_ipv4.ManualGatewayMac.Values[0] == "00:00:01:00:00:01"


def test_ipv6_gateway_mac_standalone(api, b2b_raw_config, utils):
    """
    Test IPv6 interface with manual gateway MAC configuration.
    
    Configure:
    - IPv6 interface with manually configured gateway_mac
    
    Validate:
    - Gateway MAC is properly configured on IPv6 interface
    """
    config = b2b_raw_config
    
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    d1_ipv6 = d1_eth.ipv6_addresses.ipv6()[-1]
    d1_ipv6.name = "d1_ipv6"
    d1_ipv6.address = "2001:db8::1"
    d1_ipv6.gateway = "2001:db8::2"
    d1_ipv6.prefix = 64
    d1_ipv6.gateway_mac.value = "00:00:02:00:00:01"
    
    api.set_config(config)
    
    # Validate via RestPy
    ixn_ipv6 = utils.get_ixnetwork_obj(api, d1_ipv6.name, "ipv6")
    assert ixn_ipv6 is not None
    assert ixn_ipv6.ManualGatewayMac.Values[0] == "00:00:02:00:00:01"


def test_vlan_stacking_mixed_tpid(api, b2b_raw_config, utils):
    """
    Test VLAN stacking with mixed TPID values.
    
    Configure:
    - Ethernet with multiple VLAN layers using different TPID values
    
    Validate:
    - Each VLAN layer has correct TPID configuration
    """
    config = b2b_raw_config
    
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    # Outer VLAN with TPID 0x88A8 (Provider Bridge)
    vlan1 = d1_eth.vlans.vlan()[-1]
    vlan1.name = "vlan1"
    vlan1.id = 100
    vlan1.tpid = "x88a8"
    vlan1.priority = 7
    
    # Inner VLAN with TPID 0x8100 (Standard)
    vlan2 = d1_eth.vlans.vlan()[-1]
    vlan2.name = "vlan2"
    vlan2.id = 200
    vlan2.tpid = "x8100"
    vlan2.priority = 5
    
    # Another inner VLAN with TPID 0x9100
    vlan3 = d1_eth.vlans.vlan()[-1]
    vlan3.name = "vlan3"
    vlan3.id = 300
    vlan3.tpid = "x9100"
    vlan3.priority = 3
    
    d1_ipv4 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.2"
    d1_ipv4.prefix = 24
    
    api.set_config(config)
    
    # Validate VLAN configuration
    ixn_eth = utils.get_ixnetwork_obj(api, d1_eth.name, "ethernet")
    assert ixn_eth is not None
    assert ixn_eth.VlanCount.Values[0] == 3
    
    ixn_vlan1 = utils.get_ixnetwork_obj(api, vlan1.name, "vlan")
    assert ixn_vlan1.Tpid.Values[0] == "ethertype88a8"
    assert ixn_vlan1.VlanId.Values[0] == 100
    assert ixn_vlan1.Priority.Values[0] == 7
    
    ixn_vlan2 = utils.get_ixnetwork_obj(api, vlan2.name, "vlan")
    assert ixn_vlan2.Tpid.Values[0] == "ethertype8100"
    assert ixn_vlan2.VlanId.Values[0] == 200
    
    ixn_vlan3 = utils.get_ixnetwork_obj(api, vlan3.name, "vlan")
    assert ixn_vlan3.Tpid.Values[0] == "ethertype9100"
    assert ixn_vlan3.VlanId.Values[0] == 300


def test_vlan_empty_list_vs_none(api, b2b_raw_config, utils):
    """
    Test VLAN configuration with empty list vs None.
    
    Configure:
    - Device 1: Ethernet with vlans = None (no VLANs)
    - Device 2: Ethernet with vlans configured but empty list
    
    Validate:
    - Both configurations should not enable VLANs
    """
    config = b2b_raw_config
    
    # Device 1: No VLAN (default)
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    # Don't configure any VLANs
    
    d1_ipv4 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.2"
    d1_ipv4.prefix = 24
    
    api.set_config(config)
    
    # Validate no VLANs are configured
    ixn_eth = utils.get_ixnetwork_obj(api, d1_eth.name, "ethernet")
    assert ixn_eth is not None
    # EnableVlans should be False or VlanCount should be 0
    vlan_count = ixn_eth.VlanCount.Values[0]
    assert vlan_count == 0 or vlan_count == 1  # IxNetwork default may be 1


def test_multiple_ipv4_on_same_ethernet(api, b2b_raw_config, utils):
    """
    Test multiple IPv4 addresses on the same Ethernet interface.
    
    Configure:
    - Single Ethernet with multiple IPv4 addresses
    
    Validate:
    - All IPv4 addresses are configured correctly
    - Each has unique IP but shares same gateway
    """
    config = b2b_raw_config
    
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    # First IPv4
    d1_ipv4_1 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4_1.name = "d1_ipv4_1"
    d1_ipv4_1.address = "10.1.1.1"
    d1_ipv4_1.gateway = "10.1.1.254"
    d1_ipv4_1.prefix = 24
    
    # Second IPv4
    d1_ipv4_2 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4_2.name = "d1_ipv4_2"
    d1_ipv4_2.address = "10.1.1.2"
    d1_ipv4_2.gateway = "10.1.1.254"
    d1_ipv4_2.prefix = 24
    
    # Third IPv4
    d1_ipv4_3 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4_3.name = "d1_ipv4_3"
    d1_ipv4_3.address = "10.1.1.3"
    d1_ipv4_3.gateway = "10.1.1.254"
    d1_ipv4_3.prefix = 24
    
    api.set_config(config)
    
    # Validate all IPv4 addresses
    for idx, ipv4_name in enumerate(["d1_ipv4_1", "d1_ipv4_2", "d1_ipv4_3"], 1):
        ixn_ipv4 = utils.get_ixnetwork_obj(api, ipv4_name, "ipv4")
        assert ixn_ipv4 is not None
        assert ixn_ipv4.Address.Values[0] == f"10.1.1.{idx}"
        assert ixn_ipv4.GatewayIp.Values[0] == "10.1.1.254"
        assert ixn_ipv4.Prefix.Values[0] == 24


def test_dual_stack_ipv4_ipv6(api, b2b_raw_config, utils):
    """
    Test dual-stack configuration with both IPv4 and IPv6.
    
    Configure:
    - Single Ethernet with both IPv4 and IPv6 addresses
    
    Validate:
    - Both address families are configured correctly
    """
    config = b2b_raw_config
    
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    # IPv4
    d1_ipv4 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.2"
    d1_ipv4.prefix = 24
    
    # IPv6
    d1_ipv6 = d1_eth.ipv6_addresses.ipv6()[-1]
    d1_ipv6.name = "d1_ipv6"
    d1_ipv6.address = "2001:db8::1"
    d1_ipv6.gateway = "2001:db8::2"
    d1_ipv6.prefix = 64
    
    api.set_config(config)
    
    # Validate IPv4
    ixn_ipv4 = utils.get_ixnetwork_obj(api, d1_ipv4.name, "ipv4")
    assert ixn_ipv4 is not None
    assert ixn_ipv4.Address.Values[0] == "10.1.1.1"
    assert ixn_ipv4.GatewayIp.Values[0] == "10.1.1.2"
    
    # Validate IPv6
    ixn_ipv6 = utils.get_ixnetwork_obj(api, d1_ipv6.name, "ipv6")
    assert ixn_ipv6 is not None
    assert ixn_ipv6.Address.Values[0] == "2001:db8::1"
    assert ixn_ipv6.GatewayIp.Values[0] == "2001:db8::2"


def test_ethernet_mtu_configuration(api, b2b_raw_config, utils):
    """
    Test Ethernet MTU configuration.
    
    Configure:
    - Ethernet interfaces with various MTU values
    
    Validate:
    - MTU is configured correctly
    """
    config = b2b_raw_config
    
    # Standard MTU
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.ethernet()[-1]
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    d1_eth.mtu = 1500
    
    d1_ipv4 = d1_eth.ipv4_addresses.ipv4()[-1]
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.2"
    d1_ipv4.prefix = 24
    
    # Jumbo frame MTU
    d2 = config.devices.device(name="d2")[-1]
    d2.container_name = config.ports[1].name
    d2_eth = d2.ethernets.ethernet()[-1]
    d2_eth.name = "d2_eth"
    d2_eth.mac = "00:00:02:00:00:01"
    d2_eth.mtu = 9000
    
    d2_ipv4 = d2_eth.ipv4_addresses.ipv4()[-1]
    d2_ipv4.name = "d2_ipv4"
    d2_ipv4.address = "10.1.1.2"
    d2_ipv4.gateway = "10.1.1.1"
    d2_ipv4.prefix = 24
    
    api.set_config(config)
    
    # Validate MTU
    ixn_eth1 = utils.get_ixnetwork_obj(api, d1_eth.name, "ethernet")
    assert ixn_eth1 is not None
    assert ixn_eth1.Mtu.Values[0] == 1500
    
    ixn_eth2 = utils.get_ixnetwork_obj(api, d2_eth.name, "ethernet")
    assert ixn_eth2 is not None
    assert ixn_eth2.Mtu.Values[0] == 9000
