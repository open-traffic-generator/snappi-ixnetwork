import pytest
from ixnetwork_restpy import SessionAssistant
from abstract_open_traffic_generator.port import Port, Location, Physical
from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi


def test_create_ports():
    """Test the following:
    1) Define two abstract ports with physical locations
    2) Call the set state API to create a configuration
    3) Use ixnetwork_restpy to confirm the new configuration with only
    those two abstract ports with physical locations
    """
    pass

