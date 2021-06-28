def test_capture_filter_settings(api, settings):
    """Demonstrates how to configure basic capture settings

    Validation: Validate the capture filter settings against Restpy
    """

    attrs = {
        "DA1": "0000faceface",
        "DAMask1": "00000000000b",
        "SA1": "0000faceface",
        "SAMask1": "00000000000a",
        "Pattern1": "fffefdfcfbfa",
        "PatternMask1": "00000000000c",
        "PatternOffset1": 50,
    }

    config = api.config()

    (tx,) = config.ports.port(name="tx", location=settings.ports[0])

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    filter1, filter2 = cap.filters.filter().filter()

    # https://github.com/open-traffic-generator/snappi/issues/25
    # currently assigning the choice as work around
    filter1.choice = filter1.ETHERNET
    filter1.ethernet.src.value = attrs["SA1"]
    filter1.ethernet.src.mask = attrs["SAMask1"]
    filter1.ethernet.src.negate = True

    filter1.ethernet.dst.value = attrs["DA1"]
    filter1.ethernet.dst.mask = attrs["DAMask1"]
    filter1.ethernet.dst.negate = True

    filter2.custom.value = attrs["Pattern1"]
    filter2.custom.offset = attrs["PatternOffset1"]
    filter2.custom.mask = attrs["PatternMask1"]
    filter2.custom.negate = True

    try:
        api.set_config(config)
    except Exception as e:
        print(e)

    validate_capture_filter_settings(api, attrs)


def validate_capture_filter_settings(api, attrs):
    """
    Validate capture filter settings using restpy
    """
    ixnetwork = api._ixnetwork
    filterPallette = ixnetwork.Vport.find().Capture.FilterPallette
    for attr in attrs:
        assert getattr(filterPallette, attr) == attrs[attr]
