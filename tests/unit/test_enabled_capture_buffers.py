import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from snappi_ixnetwork.capture import Capture


class TestCaptureResults(unittest.TestCase):
    def setUp(self):
        self.port = SimpleNamespace(
            Stop=Mock(),
            HardwareEnabled=True,
            SoftwareEnabled=False,
            DataCaptureState="ready",
            ControlCaptureState="ready",
        )
        self.api = SimpleNamespace(
            warning=Mock(),
            special_char=lambda name: name,
            _vport=SimpleNamespace(
                Name="p1",
                href="/vport/1",
                find=Mock(return_value=(SimpleNamespace(Capture=self.port))),
            ),
            _ixnetwork=SimpleNamespace(
                href="/ixnetwork",
                SaveCaptureFiles=Mock(),
                MergeCapture=Mock(),
                Globals=SimpleNamespace(PersistencePath="/capture-root"),
            ),
            _request=Mock(),
        )
        self.capture = Capture(self.api)
        for target in ("Timer", "time.sleep"):
            handle = patch("snappi_ixnetwork.capture." + target)
            handle.start()
            self.addCleanup(handle.stop)

    def result(self):
        return self.capture.results(SimpleNamespace(port_name="p1"))

    def test_software_only_ignores_disabled_hardware_file(self):
        self.port.HardwareEnabled = False
        self.port.SoftwareEnabled = True
        self.api._ixnetwork.MergeCapture.side_effect = RuntimeError(
            "merge unavailable"
        )

        def request(method, url, *args):
            if method == "POST":
                return None
            return (
                b"current-software"
                if url.endswith("_SW.cap")
                else b"old-hardware"
            )

        self.api._request.side_effect = request
        self.assertEqual(self.result().getvalue(), b"current-software")
        self.api._ixnetwork.MergeCapture.assert_not_called()

    def test_missing_hardware_cannot_use_disabled_software_file(self):
        self.api._ixnetwork.MergeCapture.side_effect = RuntimeError(
            "merge unavailable"
        )

        def request(method, url, *args):
            if method == "POST":
                return None
            if url.endswith("_SW.cap"):
                return b"old-software"
            raise RuntimeError("HTTP 404 current hardware absent")

        self.api._request.side_effect = request
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            self.result()

    def test_no_enabled_buffers_fail_before_file_operations(self):
        self.port.HardwareEnabled = False
        self.port.SoftwareEnabled = False
        self.api._request.side_effect = lambda method, url, *args: (
            b"old-capture" if method == "GET" else None
        )
        with self.assertRaisesRegex(RuntimeError, "no enabled buffers"):
            self.result()
        self.api._ixnetwork.SaveCaptureFiles.assert_not_called()
        self.api._ixnetwork.MergeCapture.assert_not_called()
        self.api._request.assert_not_called()

    def test_both_enabled_buffers_keep_merged_output(self):
        self.port.SoftwareEnabled = True
        self.api._request.side_effect = lambda method, url, *args: (
            b"current-merged" if method == "GET" else None
        )
        self.assertEqual(self.result().getvalue(), b"current-merged")
        self.api._ixnetwork.MergeCapture.assert_called_once()

    def test_hardware_only_does_not_merge_disabled_software(self):
        self.api._ixnetwork.MergeCapture.side_effect = RuntimeError(
            "merge unavailable"
        )
        self.api._request.side_effect = lambda method, url, *args: (
            b"current-hardware" if method == "GET" else None
        )
        self.assertEqual(self.result().getvalue(), b"current-hardware")
        self.api._ixnetwork.MergeCapture.assert_not_called()
