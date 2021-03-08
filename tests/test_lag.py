import pytest
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.lag as lag
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control

# @pytest.mark.skip(reason="LAG models not yet implemented")
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
        port.Port(name='port1', location='10.39.34.250;1;7'),
        port.Port(name='port2', location='10.39.34.250;1;8'),
    ]
    proto1 = lag.Protocol(choice=lag.Static(lag_id=2))
    proto2 = lag.Protocol(choice=lag.Static(lag_id=3))
    # proto1 = lag.Protocol(choice=lag.Lacp(actor_port_priority=3))
    # proto2 = lag.Protocol(choice=lag.Lacp(actor_port_priority=4))
    eth1 = lag.Ethernet(name='eth1',
                        mac='00:22:02:00:00:02',
                        vlans=[
                            # lag.Vlan(priority=, name='vlan1'),
                            lag.Vlan(priority=2, name='vlan2')
                        ])
    eth2 = lag.Ethernet(name='eth2',
                        mac='00:33:03:00:00:03',
                        vlans=[
                            # lag.Vlan(priority=3, name='vlan3'),
                            lag.Vlan(priority=4, name='vlan4')
                        ])
    lag_port1 = lag.Port(port_name=ports[0].name, protocol=proto1, ethernet=eth1)
    lag_port2 = lag.Port(port_name=ports[1].name, protocol=proto2, ethernet=eth2)
    lag1 = lag.Lag(name='lag1', ports=[lag_port1, lag_port2])
    configuration = config.Config(ports=ports, options=options, lags=[lag1])
    state = control.State(control.ConfigState(config=configuration, state='set'))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
