import re
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from snappi_ixnetwork.trafficitem import TrafficItem


class TestExactFlowName(unittest.TestCase):
    def test_other_matching_names_receive_no_size_write(self):
        cases = [
            ("f1", "f10"),
            ("flow.1", "flowx1"),
            ("flow|backup", "backup"),
            ("flow$", "flow"),
        ]
        for target, other in cases:
            with self.subTest(target=target):
                values = {target: 128, other: 128}
                writes = {target: [], other: []}

                class SelectedSize:
                    def __init__(self, selected):
                        self.selected = selected

                    @property
                    def FixedSize(self):
                        return values[self.selected[0]]

                    @FixedSize.setter
                    def FixedSize(self, value):
                        for name in self.selected:
                            values[name] = value
                            writes[name].append(value)

                def find(Name):
                    selected = [n for n in values if re.search(Name, n)]
                    stream = SimpleNamespace(FrameSize=SelectedSize(selected))
                    return SimpleNamespace(
                        HighLevelStream=SimpleNamespace(find=lambda: stream)
                    )

                driver = object.__new__(TrafficItem)
                driver._api = SimpleNamespace(
                    _ixnetwork=SimpleNamespace(
                        Traffic=SimpleNamespace(
                            TrafficItem=SimpleNamespace(find=find)
                        )
                    )
                )
                driver._validate_update_flows_config = Mock()
                flow = SimpleNamespace(
                    name=target,
                    size=SimpleNamespace(choice="fixed", fixed=256),
                    rate=SimpleNamespace(choice=None),
                )
                driver.update_flows(
                    SimpleNamespace(property_names=["size"], flows=[flow])
                )
                self.assertEqual(writes[target], [256])
                self.assertEqual(writes[other], [])
