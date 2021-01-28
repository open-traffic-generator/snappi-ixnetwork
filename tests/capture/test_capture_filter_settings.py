import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_capture_filter_settings(api, tx_port, options):
    """Demonstrates how to configure basic capture settings

    Validation: Validate the capture filter settings against Restpy
    """
    config = Config(ports=[tx_port], options=options)
    attrs = {
        'DA1': '0000faceface',
        'DAMask1': '00000000000b',
        'SA1': '0000faceface',
        'SAMask1': '00000000000a',
        'Pattern1': 'fffefdfcfbfa',
        'PatternMask1': '00000000000c',
        'PatternOffset1': 50
    }

    src = MacAddressFilter(mac='source',
                           filter=attrs['SA1'],
                           mask=attrs['SAMask1'])
    dst = MacAddressFilter(mac='destination',
                           filter=attrs['DA1'],
                           mask=attrs['DAMask1'])
    custom = CustomFilter(filter=attrs['Pattern1'],
                          mask=attrs['PatternMask1'],
                          offset=attrs['PatternOffset1'])

    config.captures.append(
        Capture(name='capture',
                port_names=[tx_port.name],
                choice=[
                    BasicFilter(src, and_operator=False, not_operator=True),
                    BasicFilter(dst, and_operator=False, not_operator=True),
                    BasicFilter(custom, and_operator=False, not_operator=True)
                ]))

    api.set_state(State(ConfigState(config=config, state='set')))

    validate_capture_filter_settings(api, attrs)


def validate_capture_filter_settings(api, attrs):
    """
    Validate capture filter settings using restpy
    """
    ixnetwork = api._ixnetwork
    filterPallette = ixnetwork.Vport.find().Capture.FilterPallette
    for attr in attrs:
        assert getattr(filterPallette, attr) == attrs[attr]
