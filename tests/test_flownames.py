import json
import os
from abstract_open_traffic_generator import control


def test_flownames(api, utils):
    path = os.path.join(utils.get_root_dir(), 'config_files/test.json')
    fd = open(path, 'r')
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
