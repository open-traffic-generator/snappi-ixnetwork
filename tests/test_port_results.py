import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.request import Port as Request


def test_ports(serializer, api, tx_port, rx_port):
    """Demonstrates how to retrieve port results
    """
    config = Config(ports=[tx_port, rx_port])
    api.set_config(config)

    request = Request()
    results = api.get_port_results(request)
    print(results['columns'])
    for row in results['rows']:
        print(row)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
