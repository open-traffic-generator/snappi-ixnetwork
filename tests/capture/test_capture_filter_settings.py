def test_capture_filter_settings(api, settings):
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
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    filter1, filter2 = cap.filters.ethernet().custom()

    filter1.src.value = attrs["SA1"]
    filter1.src.mask = attrs["SAMask1"]
    filter1.src.negate = True

    filter1.dst.value = attrs["DA1"]
    filter1.dst.mask = attrs["DAMask1"]
    filter1.dst.negate = True

    filter2.value = attrs["Pattern1"]
    filter2.offset = attrs["PatternOffset1"]
    filter2.mask = attrs["PatternMask1"]
    filter2.negate = True

    try:
        api.set_config(config)
    except Exception as e:
        print(e)

    validate_capture_filter_settings(api, attrs)


def test_ethernet_capture_filter_settings(api, settings):
    attrs = {
        "DA1": "0000faceface",
        "DAMask1": "00000000000b",
        "SA1": "0000faceface",
        "SAMask1": "00000000000a",
        "Pattern1": "fffefdfcfbfa",
        "PatternMask1": "00000000000c",
        "Pattern2": "fffeabacfbfa",
        "PatternMask2": "00000000000c",
    }

    config = api.config()

    (tx,) = config.ports.port(name="tx", location=settings.ports[0])
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    filter1, filter2 = cap.filters.ethernet().ethernet()

    filter1.src.value = attrs["SA1"]
    filter1.src.mask = attrs["SAMask1"]
    filter1.src.negate = True

    filter1.dst.value = attrs["DA1"]
    filter1.dst.mask = attrs["DAMask1"]
    filter1.dst.negate = True

    filter2.ether_type.value = attrs["Pattern1"]
    filter2.ether_type.mask = attrs["PatternMask1"]
    filter2.ether_type.negate = True

    filter2.pfc_queue.value = attrs["Pattern2"]
    filter2.pfc_queue.mask = attrs["PatternMask2"]
    filter2.pfc_queue.negate = True

    try:
        api.set_config(config)
    except Exception as e:
        print(e)

    validate_capture_filter_settings(api, attrs)


def test_vlan_capture_filter_settings(api, settings):
    attrs = {
        "DA1": "0000faceface",
        "DAMask1": "00000000000b",
        "SA1": "0000faceface",
        "SAMask1": "00000000000a",
        "Pattern1": "12",
        "PatternMask1": "13",
        "Pattern2": "14",
        "PatternMask2": "15",
    }

    config = api.config()

    (tx,) = config.ports.port(name="tx", location=settings.ports[0])
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    filter1, filter2 = cap.filters.ethernet().vlan()

    filter1.src.value = attrs["SA1"]
    filter1.src.mask = attrs["SAMask1"]
    filter1.src.negate = True

    filter1.dst.value = attrs["DA1"]
    filter1.dst.mask = attrs["DAMask1"]
    filter1.dst.negate = True

    filter2.priority.value = attrs["Pattern1"]
    filter2.priority.mask = attrs["PatternMask1"]
    filter2.priority.negate = True

    filter2.cfi.value = attrs["Pattern2"]
    filter2.cfi.mask = attrs["PatternMask2"]
    filter2.cfi.negate = True

    try:
        api.set_config(config)
    except Exception as e:
        print(e)

    validate_capture_filter_settings(api, attrs)


def test_ipv4_capture_filter_settings(api, settings):
    attrs = {
        "DA1": "0000faceface",
        "DAMask1": "00000000000b",
        "SA1": "0000faceface",
        "SAMask1": "00000000000a",
        "Pattern1": "01010101",
        "PatternMask1": "02020202",
        "Pattern2": "03030303",
        "PatternMask2": "04040404",
    }

    config = api.config()

    (tx,) = config.ports.port(name="tx", location=settings.ports[0])
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    filter1, filter2 = cap.filters.ethernet().ipv4()

    filter1.src.value = attrs["SA1"]
    filter1.src.mask = attrs["SAMask1"]
    filter1.src.negate = True

    filter1.dst.value = attrs["DA1"]
    filter1.dst.mask = attrs["DAMask1"]
    filter1.dst.negate = True

    filter2.src.value = attrs["Pattern1"]
    filter2.src.mask = attrs["PatternMask1"]
    filter2.src.negate = True

    filter2.dst.value = attrs["Pattern2"]
    filter2.dst.mask = attrs["PatternMask2"]
    filter2.dst.negate = True

    try:
        api.set_config(config)
    except Exception as e:
        print(e)

    validate_capture_filter_settings(api, attrs)


def test_ipv6_capture_filter_settings(api, settings):
    attrs = {
        "DA1": "0000faceface",
        "DAMask1": "00000000000b",
        "SA1": "0000faceface",
        "SAMask1": "00000000000a",
        "Pattern1": "00010001000100010001000100010001",
        "PatternMask1": "00020002000200020002000200020002",
        "Pattern2": "00030003000300030003000300030003",
        "PatternMask2": "00040004000400040004000400040004",
    }

    config = api.config()

    (tx,) = config.ports.port(name="tx", location=settings.ports[0])
    config.options.port_options.location_preemption = True

    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [tx.name]
    filter1, filter2 = cap.filters.ethernet().ipv6()

    filter1.src.value = attrs["SA1"]
    filter1.src.mask = attrs["SAMask1"]
    filter1.src.negate = True

    filter1.dst.value = attrs["DA1"]
    filter1.dst.mask = attrs["DAMask1"]
    filter1.dst.negate = True

    filter2.src.value = attrs["Pattern1"]
    filter2.src.mask = attrs["PatternMask1"]
    filter2.src.negate = True

    filter2.dst.value = attrs["Pattern2"]
    filter2.dst.mask = attrs["PatternMask2"]
    filter2.dst.negate = True

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
