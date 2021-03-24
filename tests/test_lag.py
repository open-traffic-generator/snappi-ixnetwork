import pytest
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.layer1 as layer1
import abstract_open_traffic_generator.lag as lag
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control
import abstract_open_traffic_generator.flow as flow
import abstract_open_traffic_generator.device as device


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
        port.Port(name='txp2', location=utils.settings.ports[2]),
        port.Port(name='rxp1', location=utils.settings.ports[1]),
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
    
    devices = []
    devices.append(
        device.Device(
            name='device1',
            container_name=lag1.name,
            device_count=15,
            choice=device.Ipv4(
                name='ipv41',
                address=device.Pattern('1.1.1.1'),
                prefix=device.Pattern('24'),
                gateway=device.Pattern('1.1.1.2'),
                ethernet=device.Ethernet(
                    name='eth1',
                    mac=device.Pattern('00:00:fa:ce:fa:ce'),
                    mtu=device.Pattern('1200')))))
    devices.append(
        device.Device(
            name='device2',
            container_name=lag2.name,
            device_count=15,
            choice=device.Ipv4(
                name='ipv42',
                address=device.Pattern('1.1.1.2'),
                prefix=device.Pattern('24'),
                gateway=device.Pattern('1.1.1.1'),
                ethernet=device.Ethernet(
                    name='eth2',
                    mac=device.Pattern('00:00:fa:ce:fa:aa'),
                    mtu=device.Pattern('1200')))))

    packets = 2000
    f1_size = 74
    f2_size = 1500

    flow1 = flow.Flow(
        name='f1',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[0].name,
                rx_port_name=ports[2].name
            )
        )
    )

    flow2 = flow.Flow(
        name='f2',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[1].name,
                rx_port_name=ports[3].name
            )
        )
    )

    flow1.duration = flow.Duration(flow.FixedPackets(packets=packets))
    flow1.size = flow.Size(f1_size)
    flow1.rate = flow.Rate(value=10, unit='line')

    flow2.duration = flow.Duration(flow.FixedPackets(packets=packets))
    flow2.size = flow.Size(f2_size)
    flow2.rate = flow.Rate(value=10, unit='line')

    configuration = config.Config(
        ports=ports, options=options, lags=[lag1, lag2], layer1=l1,
        flows=[flow1, flow2]
    )

    utils.start_traffic(api, configuration, start_capture=False)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )

    utils.wait_for(
        lambda: utils.is_stats_accumulated(api, packets * 2),
        'stats to be accumulated'
    )

    utils.wait_for(
        lambda: results_ok(
            api, utils, f1_size, f2_size, packets
        ),
        'stats to be as expected', timeout_seconds=10
    )


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
        port.Port(name='txp2', location=utils.settings.ports[2]),
        port.Port(name='rxp1', location=utils.settings.ports[1]),
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

    devices = []
    devices.append(
        device.Device(
            name='device1',
            container_name=lag1.name,
            device_count=15,
            choice=device.Ipv4(
                name='ipv41',
                address=device.Pattern('1.1.1.1'),
                prefix=device.Pattern('24'),
                gateway=device.Pattern('1.1.1.2'),
                ethernet=device.Ethernet(
                    name='ether1',
                    mac=device.Pattern('00:00:fa:ce:fa:ce'),
                    mtu=device.Pattern('1200')))))
    devices.append(
        device.Device(
            name='device2',
            container_name=lag2.name,
            device_count=15,
            choice=device.Ipv4(
                name='ipv42',
                address=device.Pattern('1.1.1.2'),
                prefix=device.Pattern('24'),
                gateway=device.Pattern('1.1.1.1'),
                ethernet=device.Ethernet(
                    name='ether2',
                    mac=device.Pattern('00:00:fa:ce:fa:aa'),
                    mtu=device.Pattern('1200')))))

    packets = 2000
    f1_size = 74
    f2_size = 1500

    flow1 = flow.Flow(
        name='f1',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[0].name,
                rx_port_name=ports[2].name
            )
        )
    )

    flow2 = flow.Flow(
        name='f2',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[1].name,
                rx_port_name=ports[3].name
            )
        )
    )

    flow1.duration = flow.Duration(flow.FixedPackets(packets=packets))
    flow1.size = flow.Size(f1_size)
    flow1.rate = flow.Rate(value=10, unit='line')

    flow2.duration = flow.Duration(flow.FixedPackets(packets=packets))
    flow2.size = flow.Size(f2_size)
    flow2.rate = flow.Rate(value=10, unit='line')

    configuration = config.Config(
        ports=ports, options=options, lags=[lag1, lag2], layer1=l1,
        flows=[flow1, flow2], devices=devices
    )

    utils.start_traffic(api, configuration, start_capture=False)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )

    utils.wait_for(
        lambda: utils.is_stats_accumulated(api, packets * 2),
        'stats to be accumulated'
    )

    utils.wait_for(
        lambda: results_ok(
            api, utils, f1_size, f2_size, packets
        ),
        'stats to be as expected', timeout_seconds=10
    )


def results_ok(api, utils, size1, size2, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets * 2)
    bytes_ok = utils.total_bytes_ok(
        port_results, flow_results, packets * size1 + packets * size2
    )
    return frames_ok and bytes_ok
