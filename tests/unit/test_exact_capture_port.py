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

    def test_retrieval_does_not_stop_other_matching_ports(self):
        import re

        for target, other in [("p1", "p10"), ("p.1", "px1"), ("p|q", "q")]:
            with self.subTest(target=target):
                running = {target: True, other: True}
                lookups = []

                def find(Name):
                    selected = [n for n in running if re.search(Name, n)]
                    lookups.append(selected)

                    def stop(mode):
                        for name in selected:
                            running[name] = False

                    return SimpleNamespace(
                        Capture=SimpleNamespace(
                            Stop=stop,
                            HardwareEnabled=True,
                            SoftwareEnabled=False,
                            DataCaptureState="ready",
                            ControlCaptureState="ready",
                        )
                    )

                self.api._vport.find.side_effect = find
                self.api._ixnetwork.SaveCaptureFiles.side_effect = (
                    RuntimeError("save reached")
                )
                with self.assertRaisesRegex(RuntimeError, "save reached"):
                    self.capture.results(SimpleNamespace(port_name=target))
                self.assertFalse(running[target])
                self.assertTrue(running[other])
                self.assertEqual(lookups, [[target], [target]])
