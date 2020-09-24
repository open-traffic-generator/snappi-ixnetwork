import pytest
import json
from abstract_open_traffic_generator.config import Config


def test_json_config(serializer, api, b2b_devices):
    config = Config(ports=b2b_devices)
    config = serializer.json(config)
    api.set_config(config)

def test_dict_config(serializer, api, b2b_devices):
    config = Config(ports=b2b_devices)
    config = serializer.json_to_dict(serializer.json(config))
    api.set_config(config)

def test_config(serializer, api, b2b_devices):
    config = Config(ports=b2b_devices)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
