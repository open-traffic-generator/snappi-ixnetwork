import pytest


def test_unique_names(serializer):
    """Test is designed to verify that the concrete implementation 
    enforces unique names across the configuration
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.port import Port
    from abstract_open_traffic_generator.flow import Flow
    from abstract_open_traffic_generator.capture import Capture

    ports = [
        Port(name='port'),
        Port(name='port'),
        Port(name=None)
    ]
    flows = [
        Flow(name='flow'),
        Flow(name='flow'),
        Flow(),
        Flow(name='port')
    ]
    captures = [
        Capture(name='capture'),
        Capture(name='capture')
    ]
    config = Config(ports=ports, flows=flows, captures=captures)
    print(serializer.json(config))

    from ixnetwork_open_traffic_generator import IxNetworkApi
    api = IxNetworkApi()
    try:
        api.set_config(config)
        assert('set_config MUST raise a NameError with duplicate entries')
    except NameError as e:
        print(e)
    except:
        assert('set_config MUST raise a NameError')


if __name__ == '__main__':
    pytest.main(['-s', __file__])
