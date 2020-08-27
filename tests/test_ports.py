import pytest


def test_create_tx_rx_port(serializer, tx_port, rx_port):
    assert(tx_port.name is not None)
    assert(tx_port.location is not None)
    assert(rx_port.name is not None)
    assert(rx_port.location is not None)
    print(serializer.json([tx_port, rx_port]))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
