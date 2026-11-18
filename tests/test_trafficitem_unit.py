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


# ---------------------------------------------------------------------------
# transmit(start): only port/traffic stats must be cleared, never protocol
# stats (ClearStats hangs "Clear Stats <proto>" and blocks ApplyOnTheFly).
# ---------------------------------------------------------------------------


class _Cfg(dict):
    """dict + attribute access, like a snappi config for the used fields."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class _Flow:
    def __init__(self, name):
        self.name = name


class _Request:
    def __init__(self, state="start", flow_names=None):
        self.state = state
        self.flow_names = flow_names or []


class _RecordingIxnetwork:
    def __init__(self):
        self.calls = []

    def ClearStats(self, *args, **kwargs):
        self.calls.append(("ClearStats", args))

    def ClearPortsAndTrafficStats(self, *args, **kwargs):
        self.calls.append(("ClearPortsAndTrafficStats", args))


class _TrafficItems:
    """Stand-in for the restpy TrafficItem collection with find(State=)."""

    def __init__(self, states):
        self._states = states  # list of state strings
        self._current = list(states)
        self.generated = False

    def find(self, **kwargs):
        state = kwargs.get("State")
        if state is None:
            self._current = list(self._states)
        else:
            pattern = state.strip("^$")
            self._current = [s for s in self._states if s == pattern]
        return self

    def __len__(self):
        return len(self._current)

    def Generate(self):
        self.generated = True

    def StartStatelessTrafficBlocking(self):
        pass

    def PauseStatelessTraffic(self, value):
        pass


class _Capture:
    def _start_capture(self):
        pass


class _TransmitApi:
    def __init__(self, item_states):
        self._config = _Cfg(devices=[], flows=[_Flow("f1")])
        self._topology = _TrafficItems([])
        self._traffic_item = _TrafficItems(item_states)
        self._traffic = type("T", (), {"Apply": lambda self: None})()
        self._ixnetwork = _RecordingIxnetwork()
        self.capture = _Capture()

    def special_char(self, names):
        return names

    def info(self, msg):
        pass


def _transmit_start(item_states):
    api = _TransmitApi(item_states)
    TrafficItem(api).transmit(_Request("start"))
    return api._ixnetwork.calls


def test_transmit_start_clears_only_port_and_traffic_stats():
    calls = _transmit_start(["stopped"])
    assert [c[0] for c in calls] == ["ClearPortsAndTrafficStats"]
    assert calls[0][1] == (
        ["waitForPortStatsRefresh", "waitForTrafficStatsRefresh"],
    )


def test_transmit_start_never_calls_clear_stats():
    # ClearStats also clears protocol stats and can block ApplyOnTheFly
    calls = _transmit_start(["unapplied"])
    assert "ClearStats" not in [c[0] for c in calls]


def test_transmit_start_skips_clear_when_already_started():
    calls = _transmit_start(["started"])
    assert calls == []
