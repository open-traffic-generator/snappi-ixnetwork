import pytest
import time
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.flow import *
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator.result import *


def test_capture_pcap(serializer, api, tx_port, rx_port):
    """Demonstrates how to start capture and get capture results
    """
    # configure capture
    filter = MacAddressFilter(mac='source', filter='000000000000')
    rx_port.capture = Capture(choice=[BasicFilter(filter)], enable=True)

    # configure flow
    tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_names=[rx_port.name])
    flow = Flow(name='capture', tx_rx=TxRx(tx_rx), duration=Duration(FixedPackets(packets=100)))
    config = Config(ports=[tx_port, rx_port], flows=[flow])
    api.set_config(config)

    # start capture
    api.set_port_capture(PortCapture(port_names=[rx_port.name]))

    # start transmit
    api.set_flow_transmit(FlowTransmit(state='start'))
    time.sleep(5)

    # stop the capture and receive the capture as a stream of bytes
    pcap_bytes = api.get_capture_results(CaptureRequest(port_name=rx_port.name))

    # write the pcap bytes to a local file
    with open('%s.pcap' % rx_port.name, 'wb') as fid:
        fid.write(pcap_bytes)

    # do stuff using scapy and the pcap file
    from scapy.all import PcapReader
    reader = PcapReader('%s.pcap' % rx_port.name)
    for item in reader:
        print(item.time)
        item.show()

if __name__ == '__main__':
    pytest.main(['-s', __file__])