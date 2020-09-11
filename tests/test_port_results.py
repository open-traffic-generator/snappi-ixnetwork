import pytest
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.result import PortRequest


def test_ports(serializer, api, options, tx_port, rx_port):
    """Demonstrates how to retrieve port results
    """
    config = Config(ports=[tx_port, rx_port], options=options)
    api.set_config(config)

    request = PortRequest()
    results = api.get_port_results(request)
    print(results['columns'])
    for row in results['rows']:
        print(row)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
