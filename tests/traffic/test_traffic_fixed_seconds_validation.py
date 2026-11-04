import pytest
from snappi_ixnetwork.exceptions import SnappiIxnException


def _assert_integer_validation_error(api, config):
    """Helper to assert that set_config raises a 400 SnappiIxnException
    mentioning integer requirement."""
    try:
        api.set_config(config)
        assert False, "Expected SnappiIxnException was not raised"
    except SnappiIxnException as err:
        assert err.status_code == 400
        assert err.args[0] == 400
        assert isinstance(err.message, list)
        assert any(
            "integer" in msg.lower() for msg in err.message
        ), "Error message should mention integer requirement"


# ---------------------------------------------------------------------------
# fixed_seconds – seconds field
# ---------------------------------------------------------------------------

def test_fixed_seconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with fixed_seconds duration where seconds is a float.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because fixed_seconds.seconds only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.fixed_seconds.seconds = 10.5
    _assert_integer_validation_error(api, b2b_raw_config)


# ---------------------------------------------------------------------------
# fixed_seconds – delay field
# ---------------------------------------------------------------------------

def test_fixed_seconds_delay_nanoseconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with fixed_seconds duration where delay.nanoseconds is
    a float value.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because fixed_seconds delay only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.fixed_seconds.seconds = 5
    flow.duration.fixed_seconds.delay.nanoseconds = 100.7
    _assert_integer_validation_error(api, b2b_raw_config)


def test_fixed_seconds_delay_microseconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with fixed_seconds duration where delay.microseconds is
    a float value.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because fixed_seconds delay only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.fixed_seconds.seconds = 5
    flow.duration.fixed_seconds.delay.microseconds = 50.3
    _assert_integer_validation_error(api, b2b_raw_config)


# ---------------------------------------------------------------------------
# continuous – delay field
# ---------------------------------------------------------------------------

def test_continuous_delay_nanoseconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with continuous duration where delay.nanoseconds is
    a float value.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because continuous delay only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.choice = flow.duration.CONTINUOUS
    flow.duration.continuous.delay.nanoseconds = 200.9
    _assert_integer_validation_error(api, b2b_raw_config)


def test_continuous_delay_microseconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with continuous duration where delay.microseconds is
    a float value.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because continuous delay only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.choice = flow.duration.CONTINUOUS
    flow.duration.continuous.delay.microseconds = 75.1
    _assert_integer_validation_error(api, b2b_raw_config)


# ---------------------------------------------------------------------------
# fixed_packets – delay field
# ---------------------------------------------------------------------------

def test_fixed_packets_delay_nanoseconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with fixed_packets duration where delay.nanoseconds is
    a float value.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because fixed_packets delay only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.fixed_packets.packets = 1000
    flow.duration.fixed_packets.delay.nanoseconds = 300.5
    _assert_integer_validation_error(api, b2b_raw_config)


def test_fixed_packets_delay_microseconds_float_raises_error(api, b2b_raw_config):
    """
    Configure a flow with fixed_packets duration where delay.microseconds is
    a float value.

    Validation:
    - set_config should raise SnappiIxnException with status_code 400
      because fixed_packets delay only accepts integer values.
    """
    flow = b2b_raw_config.flows[0]
    flow.duration.fixed_packets.packets = 1000
    flow.duration.fixed_packets.delay.microseconds = 25.8
    _assert_integer_validation_error(api, b2b_raw_config)

