import pytest


def test_capture_settings(serializer, api, tx_port):
    """Demonstrates how to configure capture
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.port import Capture, BasicFilter, MacAddressFilter, CustomFilter

    src = MacAddressFilter(mac='source', filter='0000faceface', mask='000000000000')
    dst = MacAddressFilter(mac='destination', filter='0000faceface', mask='000000000000')
    custom = CustomFilter(filter='fffefdfcfbfa', mask='000000000000', offset=50)

    tx_port.capture = Capture(choice=[
        BasicFilter(src, and_operator=False, not_operator=True),
        BasicFilter(dst, and_operator=False, not_operator=True),
        BasicFilter(custom, and_operator=False, not_operator=True)
    ])

    config = Config(ports=[tx_port])
    api.set_config(config)

def test_capture(serializer, api, tx_port, rx_port):
    """Demonstrates how to start capture and get capture results
    """
    from abstract_open_traffic_generator.config import Config
    from abstract_open_traffic_generator.port import Capture
    from abstract_open_traffic_generator.flow import Flow, TxRx, PortTxRx, Duration, Fixed
    from abstract_open_traffic_generator.control import FlowTransmit, PortCapture
    from abstract_open_traffic_generator.result import CaptureRequest

    tx_port.capture = Capture(enable=False)
    rx_port.capture = Capture(enable=True)
    tx_rx = PortTxRx(tx_port=tx_port.name, rx_port_names=[rx_port.name])
    flow = Flow(name='capture', tx_rx=TxRx(tx_rx), duration=Duration(Fixed(packets=10)))
    config = Config(ports=[tx_port], flows=[flow])
    api.set_config(config)

    api.set_port_capture(PortCapture(port_names=[rx_port.name]))
    api.set_flow_transmit(FlowTransmit(flow_names=[tx_port.name]))
    pcap_bytes = api.get_capture_results(CaptureRequest(port_name=tx_port.name))
    print(len(pcap_bytes))


if __name__ == '__main__':
    pytest.main(['-s', __file__])