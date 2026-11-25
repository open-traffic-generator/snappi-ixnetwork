import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from snappi_ixnetwork.trafficitem import TrafficItem


class FrameSize:
    def __init__(self, value=128):
        self.value = value
        self.writes = []

    @property
    def FixedSize(self):
        return self.value

    @FixedSize.setter
    def FixedSize(self, value):
        self.writes.append(value)
        self.value = value


class TestFlowPropertySelection(unittest.TestCase):
    def setUp(self):
        self.size = FrameSize()
        self.rate = SimpleNamespace(
            Type="framesPerSecond",
            Rate=20000,
            BitRateUnitsType="bitsPerSec",
            update=Mock(),
        )
        stream = SimpleNamespace(FrameSize=self.size, FrameRate=self.rate)
        item = SimpleNamespace(
            HighLevelStream=SimpleNamespace(find=lambda: stream)
        )
        traffic = SimpleNamespace(
            TrafficItem=SimpleNamespace(find=lambda **kwargs: item)
        )
        self.driver = object.__new__(TrafficItem)
        self.driver._api = SimpleNamespace(
            _ixnetwork=SimpleNamespace(Traffic=traffic)
        )
        self.driver._validate_update_flows_config = Mock()
        self.flow = SimpleNamespace(
            name="f1",
            size=SimpleNamespace(choice="fixed", fixed=256),
            rate=SimpleNamespace(choice="pps", pps=10000),
        )

    def update(self, properties):
        self.driver.update_flows(
            SimpleNamespace(property_names=properties, flows=[self.flow])
        )

    def test_rate_only_does_not_write_unselected_size(self):
        self.update(["rate"])
        self.assertEqual(self.size.writes, [])
        self.rate.update.assert_called_once_with(
            Type="framesPerSecond", Rate=10000
        )

    def test_size_only_does_not_write_unselected_rate(self):
        self.update(["size"])
        self.assertEqual(self.size.writes, [256])
        self.rate.update.assert_not_called()

    def test_omitted_selection_updates_both(self):
        self.update(None)
        self.assertEqual(self.size.writes, [256])
        self.rate.update.assert_called_once()

    def test_empty_selection_updates_both(self):
        self.update([])
        self.assertEqual(self.size.writes, [256])
        self.rate.update.assert_called_once()

    def test_explicit_combined_selection_updates_both(self):
        self.update(["rate", "size"])
        self.assertEqual(self.size.writes, [256])
        self.rate.update.assert_called_once()

    def test_unchanged_rate_has_no_update(self):
        self.flow.rate.pps = 20000
        self.update(["rate"])
        self.rate.update.assert_not_called()
