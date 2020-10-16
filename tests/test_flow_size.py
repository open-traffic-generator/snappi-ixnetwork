import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.config import *
import abstract_open_traffic_generator.control as control


def test_flow_sizes(serializer, api, tx_port, rx_port, b2b_ipv4_devices):
    """
    This will test supported Flow Size
            'float': 'fixed',
            'int': 'fixed',
            'SizeIncrement': 'increment',
            'SizeRandom': 'random',
    """
    port_endpoint = PortTxRx(tx_port_name=tx_port.name,
                             rx_port_names=[rx_port.name])
    pause = Header(
        PfcPause(dst=Pattern('01:80:C2:00:00:01'),
                 class_enable_vector=Pattern('1'),
                 pause_class_0=Pattern('1')))
    fixed_size = Flow(name='Fixed Size',
                      tx_rx=TxRx(port_endpoint),
                      packet=[pause],
                      size=Size(44),
                      rate=Rate('line', value=100),
                      duration=Duration(FixedPackets(packets=0)))

    increment = SizeIncrement(start=100, end=1200, step=10)
    increment_size = Flow(name='Increment Size',
                          tx_rx=TxRx(port_endpoint),
                          packet=[pause],
                          size=Size(increment),
                          rate=Rate('line', value=100),
                          duration=Duration(FixedPackets(packets=0)))

    random = SizeRandom()
    random_size = Flow(name='Random Size',
                       tx_rx=TxRx(port_endpoint),
                       packet=[pause],
                       size=Size(random),
                       rate=Rate('line', value=100),
                       duration=Duration(FixedPackets(packets=0)))

    config = Config(ports=[tx_port, rx_port],
                    devices=b2b_ipv4_devices,
                    flows=[fixed_size, increment_size, random_size])
    state = control.State(
        control.ConfigState(config=config, state='set'))
    print(serializer.json(state))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
