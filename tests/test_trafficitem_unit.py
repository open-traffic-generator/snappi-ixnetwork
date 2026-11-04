"""Pure unit tests for snappi_ixnetwork.trafficitem.TrafficItem.

These tests use lightweight mocks instead of a real IxNetwork API
server/connection so they can run without hardware.
"""

from snappi_ixnetwork.trafficitem import TrafficItem


class StatRow(dict):
    """dict-backed stand-in for an ixnetwork_restpy StatViewAssistant row."""

    pass


class MockStatViewAssistant:
    def __init__(self, rows):
        self.Rows = rows


class MockView:
    def __init__(self):
        self.Page = MockPage()

    def find(self, Caption=None):
        return self


class MockPage:
    PageSize = 50


class MockStatistics:
    def __init__(self):
        self.View = MockView()


class MockIxnetwork:
    def __init__(self):
        self.Statistics = MockStatistics()


class MockApi:
    """Minimal stand-in for snappi_ixnetwork.snappi_api.Api."""

    def __init__(self, traffic_items, stat_rows):
        self._flow_tracking = False
        self._traffic_items = traffic_items
        self.assistant = MockAssistant(stat_rows)
        self._ixnetwork = MockIxnetwork()

    def special_char(self, names):
        return names

    def select_traffic_items(self, traffic_item_filters=None):
        return self._traffic_items


class MockAssistant:
    def __init__(self, stat_rows):
        self._stat_rows = stat_rows

    def StatViewAssistant(self, name):
        return MockStatViewAssistant(self._stat_rows)


def _make_traffic_item(name="f1"):
    return {
        "name": name,
        "state": "started",
        "tracking": [{"trackBy": ["trackingenabled0"]}],
        "highLevelStream": [
            {
                "txPortName": "p1",
                "rxPortNames": ["p2"],
            }
        ],
    }


def test_results_handles_non_numeric_stat_values():
    """IxNetwork can report "N/A" for rate/frame columns (e.g. before
    traffic has produced any stats). `results()` must not raise and
    should fall back to a "stopped" transmit state instead of crashing
    with `ValueError: could not convert string to float: 'N/A'`.
    """
    traffic_items = {"f1": _make_traffic_item("f1")}
    stat_rows = [
        StatRow(
            {
                "Traffic Item": "f1",
                "Tx Frame Rate": "N/A",
                "Tx Frames": "N/A",
                "Rx Frames": "N/A",
                "Rx Frame Rate": "N/A",
                "Tx Bytes": "N/A",
                "Rx Bytes": "N/A",
                "Loss %": "N/A",
                "Tx L1 Rate (bps)": "N/A",
                "Rx L1 Rate (bps)": "N/A",
                "Tx Rate (Bps)": "N/A",
                "Rx Rate (Bps)": "N/A",
                "Tx Rate (bps)": "N/A",
                "Rx Rate (bps)": "N/A",
                "Tx Rate (Kbps)": "N/A",
                "Rx Rate (Kbps)": "N/A",
                "Tx Rate (Mbps)": "N/A",
                "Rx Rate (Mbps)": "N/A",
            }
        )
    ]

    api = MockApi(traffic_items, stat_rows)
    traffic_item = TrafficItem(api)

    results = traffic_item.results({"flow_names": [], "metric_names": []})

    assert len(results) == 1
    assert results[0]["transmit"] == "stopped"
    assert results[0]["frames_tx_rate"] == 0
