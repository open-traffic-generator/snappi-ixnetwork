import pytest
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control


def test_ports(serializer, api, options):
    """Demonstrates adding ports to a configuration and setting the
    configuration on the traffic generator.
    The traffic generator should have no  items configured other than
    the ports in this test.
    """
    ports = [
        port.Port(name='port1', location='10.36.74.26;01;01'),
        port.Port(name='port2', location='10.36.74.26;01;02'),
        port.Port(name='port no location')
    ]
    configuration = config.Config(ports=ports, options=options)
    state = control.State(
        control.ConfigState(config=configuration, state='set'))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
