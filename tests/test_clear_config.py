def test_clear_config(api):
    """Demonstrates how to clear an IxNetwork session configuration"""
    api.set_config(api.config())
    assert len(api._assistant.Ixnetwork.Vport.find()) == 0
    assert len(api._assistant.Ixnetwork.Topology.find()) == 0
    assert len(api._assistant.Ixnetwork.Traffic.TrafficItem.find()) == 0
