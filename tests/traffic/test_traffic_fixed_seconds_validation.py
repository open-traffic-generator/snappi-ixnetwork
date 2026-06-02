import pytest
from snappi_ixnetwork.exceptions import SnappiIxnException


def test_fixed_seconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with fixed_seconds duration where seconds is a float.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because fixed_seconds.seconds only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.fixed_seconds.seconds = 10.5  # Set seconds to a float value
    try:
        api.set_config(b2b_raw_config)
        assert False, "Expected SnappiIxnException was not raised"
    except SnappiIxnException as err:
        assert err.status_code == 400
        assert err.args[0] == 400
        assert isinstance(err.message, list)
        assert any(
            "integer" in msg.lower() for msg in err.message
        ), "Error message should mention integer requirement"
