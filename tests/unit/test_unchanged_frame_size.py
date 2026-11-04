import unittest
from types import SimpleNamespace

from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.trafficitem import TrafficItem


class FrameSize:
    def __init__(self):
        self.value = 128
        self.writes = []

    @property
    def FixedSize(self):
        return self.value

    @FixedSize.setter
    def FixedSize(self, value):
        self.writes.append(value)
        self.value = value


class TestUnchangedFrameSize(unittest.TestCase):
    def setUp(self):
        self.driver = object.__new__(TrafficItem)
        self.size = FrameSize()
        self.stream = SimpleNamespace(FrameSize=self.size)

    def test_equal_fixed_size_has_no_assignment(self):
        self.driver._update_size(
            self.stream, SimpleNamespace(choice="fixed", fixed=128)
        )
        self.assertEqual(self.size.writes, [])

    def test_changed_fixed_size_is_assigned(self):
        self.driver._update_size(
            self.stream, SimpleNamespace(choice="fixed", fixed=256)
        )
        self.assertEqual(self.size.writes, [256])

    def test_unsupported_size_choice_still_raises(self):
        with self.assertRaises(SnappiIxnException):
            self.driver._update_size(
                self.stream, SimpleNamespace(choice="random")
            )
        self.assertEqual(self.size.writes, [])
