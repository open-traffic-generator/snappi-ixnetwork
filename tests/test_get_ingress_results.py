import pytest
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.flow_ipv4 import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator.result import FlowRequest


def test_get_ingress_results(serializer, options, tx_port, rx_port, api):
    """UDP Flow test traffic configuration
    """
    udp_endpoint = PortTxRx(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    udp_header = Udp(src_port=Pattern(Counter(start="12001", step="2", count=100), ingress_result_name='UDP SRC PORT'),
                     dst_port=Pattern("20"))
    udp_flow = Flow(name='UDP Flow',
                    tx_rx=TxRx(udp_endpoint),
                    packet=[
                        Header(Ethernet()),
                        Header(Vlan()),
                        Header(Ipv4()),
                        Header(udp_header)
                    ],
                    size=Size(128),
                    rate=Rate(unit='pps', value=1000),
                    duration=Duration(FixedPackets(packets=10000)))
    config = Config(ports=[tx_port, rx_port],
        flows=[udp_flow],
        options=options
    )
    state = State(ConfigState(config=config, state='set'))
    print(serializer.json(state))
    api.set_state(state)
    state = State(FlowTransmitState(state='start'))
    api.set_state(state)

    from pandas import DataFrame
    request = FlowRequest(ingress_result_names=['UDP SRC PORT'])
    while True:
        results = api.get_flow_results(request)
        df = DataFrame.from_dict(results)
        print(df)
        if df.frames_tx.sum() >= 10000 and df.frames_tx_rate.sum() == 0:
            break


if __name__ == '__main__':
    pytest.main(['-s', __file__])
