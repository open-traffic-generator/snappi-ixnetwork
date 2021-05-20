import pytest


def test_flow_duration_bursts(api):
    """
    configure flow duration with bursts and validate
    the config against restpy
    """
    BURST_ATTR = {
        'RepeatBurst': 50,
        'BurstPacketCount': 100,
        'EnableInterBurstGap': True,
        'InterBurstGap': 200000,
        'InterBurstGapUnits': 'nanoseconds',
        'MinGapBytes': 12

    }
    config = api.config()

    p1, p2 = config.ports.port(name='tx').port(name='rx')

    f1 = config.flows.flow('PFC Burst')[-1]
    f1.tx_rx.port.tx_name = p1.name
    f1.tx_rx.port.rx_name = p2.name

    # setup the flow to contain a single pfcpause packet header
    f1.packet.pfcpause()

    burst = f1.duration.burst
    burst.bursts = BURST_ATTR['RepeatBurst']
    burst.packets = BURST_ATTR['BurstPacketCount']
    burst.gap = BURST_ATTR['MinGapBytes']
    burst.inter_burst_gap.microseconds = BURST_ATTR['InterBurstGap']

    api.set_config(config)

    validate_config(api,
                    BURST_ATTR)


def validate_config(api,
                    BURST_ATTR):
    """
    Validate Config
    """

    ixnetwork = api._ixnetwork
    tc = (ixnetwork.Traffic.TrafficItem.find()
          .ConfigElement.find().TransmissionControl)
    for attr in BURST_ATTR:
        if attr == 'InterBurstGap':
            assert BURST_ATTR[attr] * 1000.0 == getattr(tc, attr)
        else:
            assert BURST_ATTR[attr] == getattr(tc, attr)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
