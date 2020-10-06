import pytest
import time
from scapy.all import *


def test_pcap_file():
    """Demonstrates how to start capture and get capture results
    """
    # do stuff using scapy and the pcap file
    reader = rdpcap('c:/users/anbalogh/downloads/rx.pcap')
    for item in reader:
        print(item.time)
        item.show()


if __name__ == '__main__':
    pytest.main(['-s', __file__])