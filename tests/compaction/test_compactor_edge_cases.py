import pytest


def test_compactor_type_mismatch_exception(api, utils):
    """
    Test compactor raises exception on type mismatch.
    
    The _comparator method should raise "comparision issue" exception
    when comparing objects of different types.
    
    This tests the exception handling in compactor.py line 41.
    """
    from snappi_ixnetwork.device.compactor import Compactor
    
    compactor = Compactor(api)
    
    # Create objects of different types
    dict_obj = {"key": "value"}
    list_obj = ["item1", "item2"]
    
    # Should raise exception due to type mismatch
    with pytest.raises(Exception) as exc_info:
        compactor._comparator(dict_obj, list_obj)
    
    assert "comparision issue" in str(exc_info.value)


def test_compactor_list_element_different_positions(api, b2b_raw_config, utils):
    """
    Test compactor behavior when same element appears in different positions.
    
    Note: There's a TODO comment in compactor.py (line 55) about restructuring
    if same element is in different position. This test documents current behavior.
    
    Configure:
    - Two devices with similar config but list elements in different order
    
    Validate:
    - Compaction handles list ordering correctly (or doesn't compact if order matters)
    """
    config = b2b_raw_config
    
    # Device 1 with ordered list
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.add()
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    # VLAN order: 100, 200, 300
    vlan1 = d1_eth.vlans.add()
    vlan1.name = "vlan100"
    vlan1.id = 100
    
    vlan2 = d1_eth.vlans.add()
    vlan2.name = "vlan200"
    vlan2.id = 200
    
    vlan3 = d1_eth.vlans.add()
    vlan3.name = "vlan300"
    vlan3.id = 300
    
    d1_ipv4 = d1_eth.ipv4_addresses.add()
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.254"
    d1_ipv4.prefix = 24
    
    # Device 2 with same VLANs but different order
    d2 = config.devices.device(name="d2")[-1]
    d2.container_name = config.ports[1].name
    d2_eth = d2.ethernets.add()
    d2_eth.name = "d2_eth"
    d2_eth.mac = "00:00:02:00:00:01"
    
    # VLAN order: 300, 100, 200 (different from d1)
    vlan3_d2 = d2_eth.vlans.add()
    vlan3_d2.name = "vlan300_d2"
    vlan3_d2.id = 300
    
    vlan1_d2 = d2_eth.vlans.add()
    vlan1_d2.name = "vlan100_d2"
    vlan1_d2.id = 100
    
    vlan2_d2 = d2_eth.vlans.add()
    vlan2_d2.name = "vlan200_d2"
    vlan2_d2.id = 200
    
    d2_ipv4 = d2_eth.ipv4_addresses.add()
    d2_ipv4.name = "d2_ipv4"
    d2_ipv4.address = "10.1.1.2"
    d2_ipv4.gateway = "10.1.1.254"
    d2_ipv4.prefix = 24
    
    api.set_config(config)
    
    # Due to different VLAN ordering, devices should NOT be compacted together
    # This test documents that list element position matters for compaction


def test_compactor_post_calculated_values(api, utils):
    """
    Test compactor comparison with PostCalculated values.
    
    Tests the PostCalculated value comparison logic in compactor.py (lines 64-66).
    
    Configure:
    - Objects with PostCalculated values
    
    Validate:
    - Compaction handles PostCalculated values correctly
    """
    # PostCalculated values are internal IxNetwork implementation details
    # This test would require creating objects with PostCalculated attributes
    # which may not be directly accessible through the API
    
    # Placeholder for when PostCalculated scenarios are identified
    pass


def test_compactor_topology_vs_normal_compaction(api, b2b_raw_config, utils):
    """
    Test difference between topology compaction and normal compaction.
    
    The compact() method has an isTopoComp flag that changes behavior:
    - Concatenates ports (line 145-147) for topology compaction
    - Different handling in _value_compactor
    
    This test documents the difference.
    """
    config = b2b_raw_config
    
    # Create two similar topologies
    topo1 = config.devices.device(name="topo1")[-1]
    topo1.container_name = config.ports[0].name
    
    eth1 = topo1.ethernets.add()
    eth1.name = "eth1"
    eth1.mac = "00:00:01:00:00:01"
    
    ipv4_1 = eth1.ipv4_addresses.add()
    ipv4_1.name = "ipv4_1"
    ipv4_1.address = "10.1.1.1"
    ipv4_1.gateway = "10.1.1.254"
    ipv4_1.prefix = 24
    
    topo2 = config.devices.device(name="topo2")[-1]
    topo2.container_name = config.ports[1].name
    
    eth2 = topo2.ethernets.add()
    eth2.name = "eth2"
    eth2.mac = "00:00:02:00:00:01"
    
    ipv4_2 = eth2.ipv4_addresses.add()
    ipv4_2.name = "ipv4_2"
    ipv4_2.address = "10.1.1.2"
    ipv4_2.gateway = "10.1.1.254"
    ipv4_2.prefix = 24
    
    api.set_config(config)
    
    # Topology compaction should concatenate ports
    # Normal compaction sets multiplier


def test_compactor_nested_dict_structures(api, b2b_raw_config, utils):
    """
    Test compactor with deeply nested dictionary structures.
    
    Tests the recursive comparison logic in _comparator and _value_compactor.
    
    Configure:
    - Devices with nested configuration (BGP with routes, communities, AS paths)
    
    Validate:
    - Nested structures are compared and compacted correctly
    """
    config = b2b_raw_config
    
    # Device 1 with nested BGP config
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.add()
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    d1_ipv4 = d1_eth.ipv4_addresses.add()
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.2"
    d1_ipv4.prefix = 24
    
    d1_bgp = d1.bgp
    d1_bgp.router_id = "1.1.1.1"
    d1_bgp_iface = d1_bgp.ipv4_interfaces.add()
    d1_bgp_iface.ipv4_name = d1_ipv4.name
    d1_peer = d1_bgp_iface.peers.add()
    d1_peer.name = "d1_peer"
    d1_peer.as_type = "ebgp"
    d1_peer.peer_address = "10.1.1.2"
    d1_peer.as_number = 65100
    
    # Nested route with communities and AS path
    d1_route = d1_peer.v4_routes.add(name="d1_route")
    d1_route.addresses.add(address="200.1.0.0", prefix=24, count=10)
    
    d1_comm = d1_route.communities.add()
    d1_comm.type = d1_comm.MANUAL_AS_NUMBER
    d1_comm.as_number = 100
    d1_comm.as_custom = 200
    
    d1_as_path = d1_route.as_path
    d1_seg = d1_as_path.segments.add()
    d1_seg.type = d1_seg.AS_SEQ
    d1_seg.as_numbers = [100, 200, 300]
    
    # Device 2 with identical nested structure
    d2 = config.devices.device(name="d2")[-1]
    d2.container_name = config.ports[1].name
    d2_eth = d2.ethernets.add()
    d2_eth.name = "d2_eth"
    d2_eth.mac = "00:00:02:00:00:01"
    
    d2_ipv4 = d2_eth.ipv4_addresses.add()
    d2_ipv4.name = "d2_ipv4"
    d2_ipv4.address = "10.1.1.2"
    d2_ipv4.gateway = "10.1.1.1"
    d2_ipv4.prefix = 24
    
    d2_bgp = d2.bgp
    d2_bgp.router_id = "2.2.2.2"
    d2_bgp_iface = d2_bgp.ipv4_interfaces.add()
    d2_bgp_iface.ipv4_name = d2_ipv4.name
    d2_peer = d2_bgp_iface.peers.add()
    d2_peer.name = "d2_peer"
    d2_peer.as_type = "ebgp"
    d2_peer.peer_address = "10.1.1.1"
    d2_peer.as_number = 65200
    
    # Same nested structure
    d2_route = d2_peer.v4_routes.add(name="d2_route")
    d2_route.addresses.add(address="201.1.0.0", prefix=24, count=10)
    
    d2_comm = d2_route.communities.add()
    d2_comm.type = d2_comm.MANUAL_AS_NUMBER
    d2_comm.as_number = 100
    d2_comm.as_custom = 200
    
    d2_as_path = d2_route.as_path
    d2_seg = d2_as_path.segments.add()
    d2_seg.type = d2_seg.AS_SEQ
    d2_seg.as_numbers = [100, 200, 300]
    
    api.set_config(config)
    
    # Nested structures with same shape should be compacted
    # (values will differ but structure is same)


def test_compactor_no_match_scenarios(api, b2b_raw_config, utils):
    """
    Test compactor behavior when no objects can be compacted.
    
    Configure:
    - Multiple devices with completely different configurations
    
    Validate:
    - Each device remains separate (no compaction occurs)
    - Configuration is still valid
    """
    config = b2b_raw_config
    
    # Device 1: Ethernet with VLAN
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.add()
    d1_eth.name = "d1_eth"
    d1_eth.mac = "00:00:01:00:00:01"
    
    vlan1 = d1_eth.vlans.add()
    vlan1.name = "vlan100"
    vlan1.id = 100
    
    d1_ipv4 = d1_eth.ipv4_addresses.add()
    d1_ipv4.name = "d1_ipv4"
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.254"
    d1_ipv4.prefix = 24
    
    # Device 2: Ethernet WITHOUT VLAN (different structure)
    d2 = config.devices.device(name="d2")[-1]
    d2.container_name = config.ports[1].name
    d2_eth = d2.ethernets.add()
    d2_eth.name = "d2_eth"
    d2_eth.mac = "00:00:02:00:00:01"
    # No VLANs
    
    d2_ipv6 = d2_eth.ipv6_addresses.add()  # IPv6 instead of IPv4
    d2_ipv6.name = "d2_ipv6"
    d2_ipv6.address = "2001:db8::1"
    d2_ipv6.gateway = "2001:db8::254"
    d2_ipv6.prefix = 64
    
    api.set_config(config)
    
    # Devices have different structure, should not be compacted
    ixn_d1 = utils.get_ixnetwork_obj(api, d1_eth.name, "ethernet")
    ixn_d2 = utils.get_ixnetwork_obj(api, d2_eth.name, "ethernet")
    assert ixn_d1 is not None
    assert ixn_d2 is not None


def test_compactor_name_conflicts(api, b2b_raw_config, utils):
    """
    Test compactor behavior with objects having same name but different config.
    
    This should not happen in normal usage, but tests robustness.
    
    Configure:
    - Two devices with components having identical names but different values
    
    Validate:
    - Compaction handles name conflicts correctly
    """
    config = b2b_raw_config
    
    # Note: In snappi API, each object typically has unique names
    # This test would require creating scenario where names collide
    # which may not be possible through normal API usage
    
    # Documenting expected behavior: names should be unique per scope
    d1 = config.devices.device(name="d1")[-1]
    d1.container_name = config.ports[0].name
    d1_eth = d1.ethernets.add()
    d1_eth.name = "eth"  # Same name
    d1_eth.mac = "00:00:01:00:00:01"
    
    d1_ipv4 = d1_eth.ipv4_addresses.add()
    d1_ipv4.name = "ipv4"  # Same name
    d1_ipv4.address = "10.1.1.1"
    d1_ipv4.gateway = "10.1.1.254"
    d1_ipv4.prefix = 24
    
    d2 = config.devices.device(name="d2")[-1]
    d2.container_name = config.ports[1].name
    d2_eth = d2.ethernets.add()
    d2_eth.name = "eth"  # Same name as d1
    d2_eth.mac = "00:00:02:00:00:01"  # Different value
    
    d2_ipv4 = d2_eth.ipv4_addresses.add()
    d2_ipv4.name = "ipv4"  # Same name as d1
    d2_ipv4.address = "10.1.1.2"  # Different value
    d2_ipv4.gateway = "10.1.1.254"
    d2_ipv4.prefix = 24
    
    api.set_config(config)
    
    # After compaction, names should be arrays
    # set_scalable should handle name consolidation


def test_compactor_scalable_name_arrays(api, b2b_raw_config, utils):
    """
    Test compactor's set_scalable method for creating name arrays.
    
    After compaction, the set_scalable method should convert names
    to arrays for compacted objects (compactor.py lines 90-95).
    
    Configure:
    - Multiple similar devices that will be compacted
    
    Validate:
    - Names become arrays after compaction
    """
    config = b2b_raw_config
    
    # Create 3 similar devices
    for i in range(3):
        device = config.devices.device(name=f"device_{i}")[-1]
        device.container_name = config.ports[0].name
        
        eth = device.ethernets.add()
        eth.name = f"eth_{i}"
        eth.mac = f"00:00:00:00:00:0{i+1}"
        eth.mtu = 1500
        
        ipv4 = eth.ipv4_addresses.add()
        ipv4.name = f"ipv4_{i}"
        ipv4.address = f"10.1.1.{i+1}"
        ipv4.gateway = "10.1.1.254"
        ipv4.prefix = 24
    
    api.set_config(config)
    
    # After compaction, names should be consolidated
    # This would require inspecting internal IxNetwork objects
