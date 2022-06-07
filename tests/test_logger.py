import pytest
import logging


def test_mac_addrs(api_with_debug, b2b_raw_config_vports):
    """create snappi api with enable loglevel to logging.DEBUG
    Validate loglevel is satting with proper value"""
    api_with_debug.set_config(b2b_raw_config_vports)
    assert api_with_debug.log_level == logging.DEBUG


if __name__ == "__main__":
    pytest.main(["-s", __file__])