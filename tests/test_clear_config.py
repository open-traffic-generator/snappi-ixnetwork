import pytest
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator.config import *


def test_clear_config(serializer, api):
    """Demonstrates how to clear an IxNetwork session configuration
    """
    api.set_state(State(ConfigState(config=Config(), state='set')))
    assert(len(api._assistant.Ixnetwork.Vport.find()) == 0)
    assert(len(api._assistant.Ixnetwork.Topology.find()) == 0)
    assert(len(api._assistant.Ixnetwork.Traffic.TrafficItem.find()) == 0)


if __name__ == '__main__':
    pytest.main(['-s', __file__])