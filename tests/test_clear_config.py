import pytest


def test_clear_config(serializer, tx_port):
    """Demonstrates how to clear an IxNetwork session configuration
    """
    from abstract_open_traffic_generator.config import Config
    from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
    
    # set the ixnetwork connection parameters
    api = IxNetworkApi('10.36.66.49', port=11009)

    # set any empty configuration to clear the remote configuration 
    api.set_config(Config())


if __name__ == '__main__':
    pytest.main(['-s', __file__])