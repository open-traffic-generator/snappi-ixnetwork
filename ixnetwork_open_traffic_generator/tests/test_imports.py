import pytest


def test_imports():
    from ixnetwork_restpy import SessionAssistant
    from abstract_open_traffic_generator.port import Port, Location, Physical
    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi

    api = IxNetworkApi()