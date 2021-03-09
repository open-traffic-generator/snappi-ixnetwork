import pytest
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.layer1 as layer1
import abstract_open_traffic_generator.lag as lag
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control


def test_static_lag(serializer, api, options, utils):
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
    api.set_state(
        control.State(control.ConfigState(config=config.Config(), state='set'))
    )
    ports = [
        port.Port(name='txp1', location=utils.settings.ports[0]),
        port.Port(name='txp2', location=utils.settings.ports[1]),
        port.Port(name='rxp1', location=utils.settings.ports[2]),
        port.Port(name='rxp2', location=utils.settings.ports[3])
    ]
    l1 = [
        layer1.Layer1(
            name='layer1',
            port_names=[p.name for p in ports], 
            speed=utils.settings.speed, media=utils.settings.media
        )
    ]

    proto1 = lag.Protocol(choice=lag.Static(lag_id=1))
    proto2 = lag.Protocol(choice=lag.Static(lag_id=1))
    proto3 = lag.Protocol(choice=lag.Static(lag_id=2))
    proto4 = lag.Protocol(choice=lag.Static(lag_id=2))
    eth1 = lag.Ethernet(name='eth1',
                        mac='00:11:02:00:00:02',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan1', id=1)
                        ])
    eth2 = lag.Ethernet(name='eth2',
                        mac='00:22:03:00:00:03',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan2', id=1)
                        ])
    eth3 = lag.Ethernet(name='eth3',
                        mac='00:33:02:00:00:02',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan3', id=1)
                        ])
    eth4 = lag.Ethernet(name='eth4',
                        mac='00:44:03:00:00:03',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan4', id=1)
                        ])
    lag_port1 =\
        lag.Port(port_name=ports[0].name, protocol=proto1, ethernet=eth1)
    lag_port2 =\
        lag.Port(port_name=ports[1].name, protocol=proto2, ethernet=eth2)
    lag_port3 =\
        lag.Port(port_name=ports[2].name, protocol=proto3, ethernet=eth3)
    lag_port4 =\
        lag.Port(port_name=ports[3].name, protocol=proto4, ethernet=eth4)
    lag1 = lag.Lag(name='lag1', ports=[lag_port1, lag_port2])
    lag2 = lag.Lag(name='lag2', ports=[lag_port3, lag_port4])
    configuration = config.Config(
        ports=ports, options=options, lags=[lag1, lag2], layer1=l1
    )
    state = control.State(control.ConfigState(
        config=configuration, state='set'
    ))
    api.set_state(state)


def test_lacp_lag(serializer, api, options, utils):
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
    api.set_state(
        control.State(control.ConfigState(config=config.Config(), state='set'))
    )
    ports = [
        port.Port(name='txp1', location=utils.settings.ports[0]),
        port.Port(name='txp2', location=utils.settings.ports[1]),
        port.Port(name='rxp1', location=utils.settings.ports[2]),
        port.Port(name='rxp2', location=utils.settings.ports[3])
    ]
    l1 = [
        layer1.Layer1(
            name='layer1',
            port_names=[p.name for p in ports], 
            speed=utils.settings.speed, media=utils.settings.media
        )
    ]
    proto1 = lag.Protocol(choice=lag.Lacp(
        actor_system_id='00:11:03:00:00:03'
    ))
    proto2 = lag.Protocol(choice=lag.Lacp(
        actor_system_id='00:11:03:00:00:03'
    ))
    proto3 = lag.Protocol(choice=lag.Lacp(
        actor_system_id='00:22:03:00:00:03'
    ))
    proto4 = lag.Protocol(choice=lag.Lacp(
        actor_system_id='00:22:03:00:00:03'
    ))
    eth1 = lag.Ethernet(name='eth1',
                        mac='00:11:02:00:00:02',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan1', id=1)
                        ])
    eth2 = lag.Ethernet(name='eth2',
                        mac='00:22:03:00:00:03',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan2', id=1)
                        ])
    eth3 = lag.Ethernet(name='eth3',
                        mac='00:33:02:00:00:02',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan3', id=1)
                        ])
    eth4 = lag.Ethernet(name='eth4',
                        mac='00:44:03:00:00:03',
                        vlans=[
                            lag.Vlan(priority=1, name='vlan4', id=1)
                        ])
    lag_port1 =\
        lag.Port(port_name=ports[0].name, protocol=proto1, ethernet=eth1)
    lag_port2 =\
        lag.Port(port_name=ports[1].name, protocol=proto2, ethernet=eth2)
    lag_port3 =\
        lag.Port(port_name=ports[2].name, protocol=proto3, ethernet=eth3)
    lag_port4 =\
        lag.Port(port_name=ports[3].name, protocol=proto4, ethernet=eth4)
    lag1 = lag.Lag(name='lag1', ports=[lag_port1, lag_port2])
    lag2 = lag.Lag(name='lag2', ports=[lag_port3, lag_port4])
    configuration = config.Config(
        ports=ports, options=options, lags=[lag1, lag2], layer1=l1
    )
    state = control.State(control.ConfigState(
        config=configuration, state='set'
    ))
    api.set_state(state)
