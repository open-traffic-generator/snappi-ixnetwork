import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *


def test_flow_duration_bursts(api, tx_port, rx_port):
    """
    configure flow duration with bursts and validate
    the config against restpy
    """
    BURST_ATTR = {
        'RepeatBurst': 50,
        'BurstPacketCount': 1000,
        'EnableInterBurstGap': True,
        'InterBurstGap': 200000,
        'InterBurstGapUnits': 'nanoseconds',
        'MinGapBytes': 12

    }
    config = Config(ports=[tx_port, rx_port])
    port_endpoint = PortTxRx(tx_port_name=tx_port.name,
                             rx_port_name=rx_port.name)
    flow = Flow(name='PFC Burst',
                tx_rx=TxRx(port_endpoint),
                duration=Duration(
                    Burst(packets=BURST_ATTR['BurstPacketCount'],
                          gap=BURST_ATTR['MinGapBytes'],
                          inter_burst_gap_unit=BURST_ATTR['InterBurstGapUnits'],
                          inter_burst_gap=BURST_ATTR['InterBurstGap'],
                          bursts=BURST_ATTR['RepeatBurst'])))
    config.flows.append(flow)

    api.set_state(State(ConfigState(config=config, state='set')))

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
        assert BURST_ATTR[attr] == getattr(tc, attr)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
