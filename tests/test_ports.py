import pytest
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control


def test_ports(serializer, api, tx_port, rx_port, options):
    """Demonstrates adding ports to a configuration and setting the
    configuration on the traffic generator.
    The traffic generator should have no  items configured other than
    the ports in this test.
    """
    ports = [tx_port, rx_port, port.Port(name='port no location')]
    configuration = config.Config(ports=ports, options=options)
    state = control.State(
        control.ConfigState(config=configuration, state='set'))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
