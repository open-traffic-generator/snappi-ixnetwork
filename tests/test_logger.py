import pytest
import logging
import snappi
import utils as utl


def test_mac_addrs(b2b_raw_config_vports):
    """create snappi api with enable loglevel to logging.DEBUG
    Validate loglevel is satting with proper value"""
    api = snappi.api(
        location=utl.settings.location,
        ext=utl.settings.ext,
        loglevel=logging.DEBUG,
    )
    utl.configure_credentials(api, utl.settings.username, utl.settings.psd)

    api.set_config(b2b_raw_config_vports)
    assert api.log_level == logging.DEBUG


if __name__ == "__main__":
    pytest.main(["-s", __file__])
