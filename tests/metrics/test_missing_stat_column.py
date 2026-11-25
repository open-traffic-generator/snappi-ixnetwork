"""Regression test for issue #683: a statistics column that is missing from
the IxNetwork view (e.g. 'Tx Bytes') must default to 0 for numeric metrics
without logging a warning. Needs no chassis."""
import pytest

from snappi_ixnetwork.trafficitem import TrafficItem


class _Row(object):
    """Mimics ixnetwork_restpy StatViewAssistant Row, which raises a bare
    IndexError for a column that is not in the view."""

    def __init__(self, cells):
        self._cells = cells

    def __getitem__(self, name):
        if name not in self._cells:
            raise IndexError()
        return self._cells[name]


def _traffic_item():
    item = TrafficItem.__new__(TrafficItem)
    item._column_names = []
    return item


def test_missing_numeric_column_defaults_to_zero():
    item = _traffic_item()
    flow_row = {}
    row = _Row({"Rx Bytes": "1500"})
    for external, internal, typ in TrafficItem._RESULT_COLUMNS:
        if external in ("bytes_tx", "bytes_rx"):
            item._set_result_value(
                flow_row, external, item._get_cell(row, internal, typ), typ
            )
    assert flow_row["bytes_tx"] == 0
    assert flow_row["bytes_rx"] == 1500


def test_missing_string_column_still_raises():
    item = _traffic_item()
    with pytest.raises(IndexError):
        item._get_cell(_Row({}), "Missing", str)
