import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_capture_overwrite(api, tx_port, options):
    """Demonstrates how to configure basic capture settings
    """
    config = Config(ports=[tx_port], options=options)
    config.captures.append(
        Capture(name='capture1',
                port_names=[tx_port.name],
                choice=[],
                overwrite=True))

    api.set_state(State(ConfigState(config=config, state='set')))
    validate_capture_overwrite(api)


def validate_capture_overwrite(api):
    """
    Validate capture overwrite using restpy
    """
    ixnetwork = api._ixnetwork
    assert ixnetwork.Vport.find().Capture.CaptureMode \
        == "captureContinuousMode"
