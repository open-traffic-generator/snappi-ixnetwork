from abstract_open_traffic_generator.config import Config
from abstract_open_traffic_generator.capture import (Capture)
from abstract_open_traffic_generator.control import *


def test_capture_settings(serializer, api, tx_port, options):
    """Demonstrates how to configure basic capture settings
    """
    config = Config(ports=[tx_port], options=options)

    config.captures.append(
        Capture(name='capture',
                port_names=[tx_port.name],
                choice=[],
                overwrite=True))

    api.set_state(State(ConfigState(config=config, state='set')))
    validate_capture_filter_settings(api)


def validate_capture_filter_settings(api):
    """
    Validate capture filter settings using restpy
    """
    ixnetwork = api._ixnetwork
    assert ixnetwork.Vport.find().Capture.CaptureMode \
        == "captureContinuousMode"
