import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *


def test_flow_rates(serializer, api, tx_port, rx_port):
    """
    This will test supported Flow Rate
        - unit (Union[pps, bps, kbps, mbps, gbps, line]): The value is a unit of this
        - value (Union[float, int]): The actual rate
        - gap (Union[float, int]): The minimum gap in bytes between packets
    """
    port_endpoint = PortTxRx(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    pause = Header(PfcPause(
        dst=Pattern('01:80:C2:00:00:01'),
        class_enable_vector=Pattern('1'),
        pause_class_0=Pattern('1')
    ))
    
    rate_line = Flow(name='Line Rate',
                      tx_rx=TxRx(port_endpoint),
                      packet=[pause],
                      size=Size(44),
                      rate=Rate('line', value=100),
                      duration=Duration(FixedPackets(packets=0)))

    rate_pps = Flow(name='pps Rate',
                     tx_rx=TxRx(port_endpoint),
                     packet=[pause],
                     size=Size(44),
                     rate=Rate('pps', value=2000),
                     duration=Duration(FixedPackets(packets=0)))

    rate_bps = Flow(name='bps Rate',
                    tx_rx=TxRx(port_endpoint),
                    packet=[pause],
                    size=Size(44),
                    rate=Rate('bps', value=700),
                    duration=Duration(FixedPackets(packets=0)))

    rate_kbps = Flow(name='kbps Rate',
                    tx_rx=TxRx(port_endpoint),
                    packet=[pause],
                    size=Size(44),
                    rate=Rate('kbps', value=800),
                    duration=Duration(FixedPackets(packets=0)))

    rate_gbps = Flow(name='gbps Rate',
                     tx_rx=TxRx(port_endpoint),
                     packet=[pause],
                     size=Size(44),
                     rate=Rate('gbps', value=800),
                     duration=Duration(FixedPackets(packets=0)))
    
    config = Config(
        ports=[
            tx_port,
            rx_port
        ],
        flows=[
            rate_line,
            rate_pps,
            rate_bps,
            rate_kbps,
            rate_gbps
        ]
    )
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
