import pytest
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control

@pytest.mark.skip(reason="LAG models not yet implemented")
def test_lag(serializer, api, options):
    """Demonstrates the following:
    1) Creating a lag comprised of multiple ports
    2) Creating emulated devices over the lag
    3) Creating traffic over the emulated devices that will transmit traffic to a single rx port.

        TX LAG              DUT             RX
        ------+         +---------+
        port 1|         |
        ..    | ------> | 
        port n|         |
        ------+
    """
    ports = [
        port.Port(name='port1', location='10.39.35.12;11;03'),
        port.Port(name='port2', location='10.39.35.12;11;04'),
        port.Port(name='port no location')
    ]
    configuration = config.Config(ports=ports, options=options)
    state = control.State(control.ConfigState(config=configuration, state='set'))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
