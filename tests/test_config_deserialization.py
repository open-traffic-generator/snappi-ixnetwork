import pytest
import json
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.control import *


def test_json_config(serializer, api, b2b_devices):
    state = State(ConfigState(config=Config(ports=b2b_devices), state='set'))
    state = serializer.json(state)
    api.set_state(state)

def test_dict_config(serializer, api, b2b_devices):
    state = State(ConfigState(config=Config(ports=b2b_devices), state='set'))
    state = serializer.json_to_dict(serializer.json(state))
    api.set_state(state)

def test_config(serializer, api, b2b_devices):
    state = State(ConfigState(config=Config(ports=b2b_devices), state='set'))
    api.set_state(state)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
