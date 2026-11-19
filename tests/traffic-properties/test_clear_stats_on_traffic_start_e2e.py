"""

On flow transmit start (when no flow is already started) the extension must
clear only port/traffic stats via ``ClearPortsAndTrafficStats``. The older
``ClearStats`` call also cleared protocol stats (e.g. "Clear Stats LACP"),
which could hang and block later actions such as route withdraw.

Validates, against a live IxNetwork session:
1. Port and flow counters are reset when traffic is restarted, i.e. the
   second run reports N packets and not 2N.
2. ``ClearPortsAndTrafficStats`` is invoked and ``ClearStats`` is not.
"""

import pytest


PACKETS = 1000
SIZE = 128


class _IxnProxy:
    """Forwards everything to the real Ixnetwork object, recording calls to
    the named methods (the restpy object itself has read-only attributes)."""

    def __init__(self, real, calls, names):
        self._real = real
        self._calls = calls
        self._names = names

    def __getattr__(self, name):
        attr = getattr(self._real, name)
        if name in self._names:

            def wrapper(*args, **kwargs):
                self._calls.append(name)
                return attr(*args, **kwargs)

            return wrapper
        return attr


def _tx_rx_ok(api, utils, expected):
    port_results, flow_results = utils.get_all_stats(api)
    tx = sum(p.frames_tx for p in port_results if p.name == "tx")
    rx = sum(p.frames_rx for p in port_results if p.name == "rx")
    flow_tx = sum(f.frames_tx for f in flow_results)
    flow_rx = sum(f.frames_rx for f in flow_results)
    return tx == rx == flow_tx == flow_rx == expected


@pytest.mark.e2e
@pytest.mark.skip("Support Case: 02288300 - skip to reduce test runtime")
def test_clear_stats_on_traffic_start_e2e(api, b2b_raw_config, utils):
    config = b2b_raw_config
    # no capture needed for this test
    config.captures.clear()

    flow = config.flows[0]
    flow.packet.ethernet().ipv4()
    flow.packet[0].src.value = "00:CD:DC:CD:DC:CD"
    flow.packet[0].dst.value = "00:AB:BC:AB:BC:AB"
    flow.packet[1].src.value = "1.1.1.2"
    flow.packet[1].dst.value = "1.1.1.1"
    flow.duration.fixed_packets.packets = PACKETS
    flow.size.fixed = SIZE
    flow.rate.percentage = 10
    flow.metrics.enable = True

    api.set_config(config)

    calls = []
    real_ixn = api._ixnetwork
    api._ixnetwork = _IxnProxy(
        real_ixn, calls, ("ClearStats", "ClearPortsAndTrafficStats")
    )
    try:
        # run 1
        utils.start_traffic_only(api)
        utils.wait_for(
            lambda: _tx_rx_ok(api, utils, PACKETS),
            "first run to send/receive %d packets" % PACKETS,
            timeout_seconds=60,
        )
        utils.wait_for(
            lambda: utils.is_traffic_stopped(api),
            "flows to stop after first run",
            timeout_seconds=60,
        )

        # run 2: stats must be cleared on start, so counters are N, not 2N
        utils.start_traffic_only(api)
        utils.wait_for(
            lambda: _tx_rx_ok(api, utils, PACKETS),
            "second run counters to be %d (cleared, not %d)"
            % (PACKETS, 2 * PACKETS),
            timeout_seconds=60,
        )
    finally:
        api._ixnetwork = real_ixn

    assert "ClearStats" not in calls, (
        "ClearStats must not be used (clears protocol stats and can hang); "
        "calls: %s" % calls
    )
    assert "ClearPortsAndTrafficStats" in calls, (
        "ClearPortsAndTrafficStats was not invoked on traffic start; "
        "calls: %s" % calls
    )
