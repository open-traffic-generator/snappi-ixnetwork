import json
import sys
import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import State, ConfigState


def test_pfc_pause_config(api, tx_port, rx_port):
    """Configure only a pfc pause frame
    """
    tx_rx_map = PortTxRx(tx_port_name=tx_port.name,
                         rx_port_name=rx_port.name)
    pause = PfcPause()
    flow = Flow(name='Pause',
                tx_rx=TxRx(tx_rx_map),
                packet=[Header(pause)],
                size=Size(64),
                rate=Rate('pps', value=1000000),
                duration=Duration(
                    FixedPackets(packets=1024,
                                 delay=120,
                                 delay_unit='nanoseconds')))
    config = Config(ports=[tx_port, rx_port], flows=[flow])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
