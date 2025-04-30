@pytest.mark.skip(
    reason="CI-Testing"
)
def test_capture_overwrite(api, settings):
    """Demonstrates how to configure basic capture settings"""
    config = api.config()

    (tx,) = config.ports.port(name="tx", location=settings.ports[0])
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    cap.overwrite = True
    api.set_config(config)
    validate_capture_overwrite(api)

@pytest.mark.skip(
    reason="CI-Testing"
)
def validate_capture_overwrite(api):
    """
    Validate capture overwrite using restpy
    """
    ixnetwork = api._ixnetwork
    assert (
        ixnetwork.Vport.find().Capture.CaptureMode == "captureContinuousMode"
    )
