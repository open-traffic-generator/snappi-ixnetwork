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

    def test_not_ready_hardware_fails_before_save(self):
        self.port.DataCaptureState = "notReady"
        self.api._ixnetwork.SaveCaptureFiles.side_effect = RuntimeError(
            "save attempted"
        )
        with self.assertRaisesRegex(RuntimeError, "did not become ready"):
            self.result()
        self.api._ixnetwork.SaveCaptureFiles.assert_not_called()
        self.assertEqual(self.api._vport.find.call_count, 31)

    def test_not_ready_software_fails_before_save(self):
        self.port.HardwareEnabled = False
        self.port.SoftwareEnabled = True
        self.port.ControlCaptureState = "notReady"
        self.api._ixnetwork.SaveCaptureFiles.side_effect = RuntimeError(
            "save attempted"
        )
        with self.assertRaisesRegex(RuntimeError, "did not become ready"):
            self.result()
        self.api._ixnetwork.SaveCaptureFiles.assert_not_called()

    def test_ready_buffer_reaches_save(self):
        self.api._ixnetwork.SaveCaptureFiles.side_effect = RuntimeError(
            "save reached"
        )
        with self.assertRaisesRegex(RuntimeError, "save reached"):
            self.result()
        self.api._ixnetwork.SaveCaptureFiles.assert_called_once()

    def test_disabled_not_ready_buffer_does_not_block_save(self):
        self.port.ControlCaptureState = "notReady"
        self.api._ixnetwork.SaveCaptureFiles.side_effect = RuntimeError(
            "save reached"
        )
        with self.assertRaisesRegex(RuntimeError, "save reached"):
            self.result()
