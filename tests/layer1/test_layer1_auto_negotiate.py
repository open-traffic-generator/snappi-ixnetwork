from itertools import product

import pytest


_PORT_NAME = "p1"


@pytest.mark.parametrize(
    "autonego, rs_fec",
    product([True, False], [True, False])
)
def test_auto_negotiate(api, utils, autonego, rs_fec):
    """
    Configure a port layer1 configuration with,
    - ieee_media_defaults: false

    Validate,
    - layer1 auto negotiate properties is as expected
    """
    config = api.config()
    p1 = config.ports.port(name=_PORT_NAME, location=utils.settings.ports[0])[-1]
    l1 = config.layer1.layer1(name="l1")[-1]
    l1.port_names = [p1.name]
    l1.speed = utils.settings.speed
    l1.media = utils.settings.media
    l1.ieee_media_defaults = False
    l1.auto_negotiate = autonego
    l1.auto_negotiation.rs_fec = rs_fec
    api.set_config(config)
    validate_auto_negotiate_config(api, autonego, rs_fec)


def validate_auto_negotiate_config(api, autonego, rs_fec):
    """
    Validate layer1 auto negotiate configs using restpy
    """
    ixnetwork = api._ixnetwork
    port = ixnetwork.Vport.find(Name=_PORT_NAME)
    lan = getattr(port.L1Config, port.Type[0].upper() + port.Type[1:])

    assert lan.EnableAutoNegotiation == autonego
    if autonego:
        assert lan.UseANResults
        assert not lan.FirecodeForceOn
        assert not lan.RsFecForceOn
        assert not lan.ForceDisableFEC
        assert lan.RsFecAdvertise == rs_fec
        assert lan.RsFecRequest == rs_fec
    else:
        assert not lan.UseANResults
        assert not lan.FirecodeForceOn
        assert lan.RsFecForceOn == rs_fec
        assert lan.ForceDisableFEC != rs_fec
