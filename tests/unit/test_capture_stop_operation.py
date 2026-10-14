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

    def test_selected_stop_uses_stop_and_does_not_clear(self):
        self.capture.set_capture_state(
            SimpleNamespace(state="stop", port_names=["p1"])
        )
        self.api._request.assert_called_once_with(
            "POST",
            "/ixnetwork/vport/capture/operations/stop",
            {"arg1": "/vport/1/capture"},
        )
        self.api._ixnetwork.StopCapture.assert_not_called()

    def test_no_selected_ports_keep_global_stop(self):
        self.capture.set_capture_state(
            SimpleNamespace(state="stop", port_names=[])
        )
        self.api._ixnetwork.StopCapture.assert_called_once()
