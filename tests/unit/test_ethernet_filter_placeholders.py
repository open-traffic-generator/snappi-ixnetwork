import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import snappi
from snappi_ixnetwork.capture import Capture


class TestEthernetFilterPlaceholders(unittest.TestCase):
    def setUp(self):
        config = snappi.Config()
        capture = config.captures.capture(name="c1", port_names=["p1"])[-1]
        self.ethernet, self.ipv4 = capture.filters.ethernet().ipv4()
        self.ipv4.dst.value = "c6336401"
        self.ipv4.dst.mask = "00ffffff"
        self.translator = Capture(SimpleNamespace(warning=Mock()))
        self.palette, self.trigger, self.filter = {}, {}, {}

    def translate_ethernet(self):
        return self.translator._config_ethernet_pallette(
            self.ethernet, self.palette, self.trigger, self.filter, 0, ""
        )

    def test_absent_mac_fields_add_no_predicate(self):
        self.assertEqual(self.translate_ethernet(), "")
        self.assertIsNone(self.ethernet.get("src"))
        self.assertIsNone(self.ethernet.get("dst"))
        self.assertEqual(self.palette, {})

    def test_materialized_mac_defaults_add_no_predicate(self):
        self.assertEqual(self.ethernet.src.value, "00")
        self.assertEqual(self.ethernet.dst.value, "00")
        self.assertEqual(self.translate_ethernet(), "")
        self.assertEqual(self.palette, {})

    def test_ipv4_destination_keeps_frame_offset_30(self):
        expression = self.translate_ethernet()
        expression = self.translator._config_ipv4_pallete(
            self.ipv4, self.palette, self.trigger, self.filter, 14, expression
        )
        self.assertEqual(self.palette["patternOffset1"], 30)
        self.assertEqual(self.palette["pattern1"], "c6336401")
        self.assertEqual(self.palette["patternMask1"], "00ffffff")
        self.assertNotIn("SA1", self.palette)
        self.assertNotIn("DA1", self.palette)
        self.assertEqual(expression, "P1")

    def test_explicit_zero_mac_mask_and_negation_are_preserved(self):
        self.ethernet.src.value = "000000000000"
        self.ethernet.src.mask = "ffffffffffff"
        self.ethernet.src.negate = True
        self.ethernet.dst.value = "112233445566"
        self.ethernet.dst.mask = "ffffffffffff"
        self.assertEqual(self.translate_ethernet(), "!SA1 and DA1")
        self.assertEqual(self.palette["SA1"], "00 00 00 00 00 00")
        self.assertEqual(self.palette["SAMask1"], "ff ff ff ff ff ff")
        self.assertEqual(self.filter["captureFilterSA"], "notAddr1")
        self.assertEqual(self.palette["DA1"], "11 22 33 44 55 66")
