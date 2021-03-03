import pytest
import json
from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.control import *
from abstract_open_traffic_generator import (
    config, port, layer1, flow, control, result, capture
)


def test_flownames(serializer, api, utils):
    fd = open('C:/Users/rangabar.KEYSIGHT/Downloads/test/test.json', 'r')
    config = fd.read()
    config = json.loads(config)
    api.set_state(
        {
            'choice': 'config_state',
            'config_state': {
                'config': config,
                'state': 'set'
            }
        }
    )
    api.set_state(control.State(control.FlowTransmitState(state='start')))
    p, f = utils.get_all_stats(api)
    assert len(f) == len(config['flows'])
