import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from snappi_ixnetwork.capture import Capture


class TestCaptureControl(unittest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(
            select_vports=Mock(
                return_value={
                    "p1": {
                        "href": "/vport/1",
                        "capture": {"hardwareEnabled": True},
                    },
                    "p2": {
                        "href": "/vport/2",
                        "capture": {"hardwareEnabled": True},
                    },
                }
            ),
            _ixnetwork=SimpleNamespace(
                href="/ixnetwork", StartCapture=Mock(), StopCapture=Mock()
            ),
            _request=Mock(),
            snappi_config=SimpleNamespace(captures=[]),
        )
        self.capture = Capture(self.api)
        timer = patch("snappi_ixnetwork.capture.Timer")
        timer.start()
        self.addCleanup(timer.stop)

    def test_stored_stop_request_does_not_restart_capture(self):
        self.capture.set_capture_state(
            SimpleNamespace(state="stop", port_names=["p1"])
        )
        self.api._request.reset_mock()
        self.capture._start_capture()
        self.api._request.assert_not_called()
        self.api._ixnetwork.StartCapture.assert_not_called()

    def test_absent_request_does_not_start_capture(self):
        self.capture._start_capture()
        self.api._request.assert_not_called()
        self.api._ixnetwork.StartCapture.assert_not_called()

    def test_explicit_start_request_still_starts_capture(self):
        self.capture.set_capture_state(
            SimpleNamespace(state="start", port_names=["p1", "p2"])
        )
        self.api._ixnetwork.StartCapture.assert_called_once()
