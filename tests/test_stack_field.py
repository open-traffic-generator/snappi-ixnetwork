import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.config import Config


def test_sonic_pfc_pause_flows(serializer, tx_port, api):
    """Demonstrate setting different patterns on a custom template
    """
    pause = PfcPause(
        dst=Pattern('01:80:C2:00:00:01'),
        class_enable_vector=Pattern('1'),
        pause_class_0=Pattern('3'),
        pause_class_1=Pattern(Counter(start='3', step='6', count=99)),
        pause_class_2=Pattern(Counter(start='3', step='6', count=99, up=False)),
        pause_class_3=Pattern(['6', '9', '2', '39']),
        pause_class_4=Pattern(Random(min='3', max='33', step=1, seed='4', count=10))
    )
    pause_flow = Flow(name='Pause Storm',
        endpoint=Endpoint(PortEndpoint(tx_port_name=tx_port.name)),
        packet=[Header(pause)],
        size=Size(412),
        rate=Rate('line', value=22.565),
        duration=Duration(Fixed(delay=12, packets=44)))
    config = Config(
        ports=[
            tx_port
        ], 
        flows = [
            pause_flow
        ]
    )
    print(serializer.json(config))

    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
