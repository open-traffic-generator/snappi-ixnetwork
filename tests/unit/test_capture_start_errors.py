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

    def test_selected_start_rejection_reaches_caller(self):
        self.api._request.side_effect = RuntimeError("capture rejected")
        with self.assertRaisesRegex(RuntimeError, "capture rejected"):
            self.capture.set_capture_state(
                SimpleNamespace(state="start", port_names=["p1"])
            )

    def test_successful_selected_start_keeps_selected_operation(self):
        self.capture.set_capture_state(
            SimpleNamespace(state="start", port_names=["p1"])
        )
        self.api._request.assert_called_once_with(
            "POST",
            "/ixnetwork/vport/capture/operations/start",
            {"arg1": "/vport/1/capture"},
        )

    def test_all_enabled_ports_keep_global_start(self):
        self.capture.set_capture_state(
            SimpleNamespace(state="start", port_names=["p1", "p2"])
        )
        self.api._ixnetwork.StartCapture.assert_called_once()
