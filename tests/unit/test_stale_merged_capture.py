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

    def test_failed_merge_does_not_download_old_merged_file(self):
        self.port.SoftwareEnabled = True
        self.api._ixnetwork.MergeCapture.side_effect = RuntimeError(
            "merge failed"
        )

        def request(method, url, *args):
            if method == "POST":
                return None
            if url.endswith("/p1.cap"):
                return b"old-merged"
            if url.endswith("/p1_HW.cap"):
                return b"current-hardware"
            raise RuntimeError("missing software file")

        self.api._request.side_effect = request
        self.assertEqual(self.result().getvalue(), b"current-hardware")
        urls = [
            c.args[1]
            for c in self.api._request.call_args_list
            if c.args[0] == "GET"
        ]
        self.assertFalse(any(u.endswith("/p1.cap") for u in urls))

    def test_missing_current_files_cannot_use_old_merged_file(self):
        self.port.SoftwareEnabled = True
        self.api._ixnetwork.MergeCapture.side_effect = RuntimeError(
            "merge failed"
        )

        def request(method, url, *args):
            if method == "POST":
                return None
            if url.endswith("/p1.cap"):
                return b"old-merged"
            raise RuntimeError("HTTP 404 current file absent")

        self.api._request.side_effect = request
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            self.result()

    def test_successful_merge_remains_preferred(self):
        self.port.SoftwareEnabled = True
        self.api._request.side_effect = lambda method, url, *args: (
            b"current-merged" if method == "GET" else None
        )
        self.assertEqual(self.result().getvalue(), b"current-merged")
        urls = [
            c.args[1]
            for c in self.api._request.call_args_list
            if c.args[0] == "GET"
        ]
        self.assertEqual(len(urls), 1)
        self.assertTrue(urls[0].endswith("/p1.cap"))

    def test_merge_failure_keeps_current_individual_fallback(self):
        self.port.SoftwareEnabled = True
        self.api._ixnetwork.MergeCapture.side_effect = RuntimeError(
            "merge failed"
        )

        def request(method, url, *args):
            if method == "POST":
                return None
            if url.endswith("/p1_HW.cap"):
                return b"current-hardware"
            raise RuntimeError("missing capture")

        self.api._request.side_effect = request
        self.assertEqual(self.result().getvalue(), b"current-hardware")
