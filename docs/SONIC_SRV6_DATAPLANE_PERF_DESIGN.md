# SONiC SRv6 Dataplane Performance Test — Design Document

> **Status:** Design draft for review. No code has been written yet.
> Sibling document: [SRV6_SNAPPI_CONVERSION_PLAN.md](./SRV6_SNAPPI_CONVERSION_PLAN.md).

---

## Sources of truth (precedence order)

Unlike the four ISIS-SRv6 control-plane tests covered by
[SRV6_SNAPPI_CONVERSION_PLAN.md](./SRV6_SNAPPI_CONVERSION_PLAN.md), **this test
has no `ixncfg` and no P4/TCL source script** to convert from. Provenance is
therefore strictly:

| Rank | Source | Role | Use it for |
|---|---|---|---|
| 1 | [sonic-mgmt/docs/testplan/snappi/srv6_performance_test.md](../sonic-mgmt/docs/testplan/snappi/srv6_performance_test.md) | **The only normative truth.** Sole authority on requirements, topology rules, SID-path formulas, packet sizes, durations, and metrics. | Anything about *what* the test must do. If this design contradicts the spec, the spec wins. |
| 2 | snappi (OTG) Python model — `IsisSRv6*`, `flow.packet`, `flow.size.weight_pairs`, `flow.duration`, `flow.metrics`, etc. | **Implementation API surface.** Constrains how the test expresses the requirements. | Anything about *which attribute name / field path / choice value* to use. |
| 3 | `snappi_ixnetwork` translator — primarily [`trafficitem.py`](./snappi_ixnetwork/trafficitem.py) and [`device/isis_srv6.py`](./snappi_ixnetwork/device/isis_srv6.py) | **Behavioural reference.** Tells us which model fields actually reach the wire and which are silently ignored. | Anything about *whether* a chosen field will actually do what the spec asks. |
| 4 | [SRV6_SNAPPI_CONVERSION_PLAN.md](./SRV6_SNAPPI_CONVERSION_PLAN.md) (sections 1-18) | **Precedent reference.** Documents the proven SRH flow pattern (Test 5), known translator gaps, audit conventions (e.g. `valueType` on traffic-stack fields), and decision-history that informed Tests 1-4. | Anything about *patterns that already work* and *gotchas to avoid*. **Not normative** — if the spec disagrees, the spec wins. |

Anything in this design document that is not directly derived from one of the
four sources above is a judgement call and is flagged inline.

---

## 0. How this document relates to the existing conversion plan

The companion document [SRV6_SNAPPI_CONVERSION_PLAN.md](./SRV6_SNAPPI_CONVERSION_PLAN.md)
(2018 lines, sections 1–18) covers the conversion of **five** SRv6/IS-IS tests
into snappi tests within `snappi-ixnetwork/tests/isis/`:

| # | Test | Type |
|---|---|---|
| 1 | `test_isis_srv6_locator_algorithm.py` | Control plane (LSP capture) |
| 2 | `test_isis_srv6_h_encap_flags.py` | Control plane (LSP capture) |
| 3 | `test_isis_srv6_prefix_attr_flags.py` | Control plane (LSP capture) |
| 4 | `test_isis_srv6_multi_locator.py` | Control plane (LSP capture) |
| 5 | `test_tc001021141_isisipv6sr_rawtraffic.py` | **Data plane** (raw IPv6+SRH) |

Tests 1–4 advertise SRv6 locators / SIDs via emulated ISIS routers and verify
the LSP wire content via `dpkt` packet capture. Test 5 introduces the raw
IPv6+SRH flow pattern that this new test reuses.

**This new test is different in scope:**

- Lives in **sonic-mgmt**, not in snappi-ixnetwork.
- Has **no ixncfg** to convert from — driven entirely by the OTG spec at
  `sonic-mgmt/docs/testplan/snappi/srv6_performance_test.md`.
- No emulated ISIS adjacency on the TG. The DUT is pre-staged with static
  SRv6 MY_SIDs and static routes.
- No control-plane verification. Verification = TG flow_metrics
  (Tx / Rx / loss / latency) + DUT `show srv6 stats` per-MY_SID counters.
- Topology-agnostic: snake (single-DUT loopback) is the default; nut-2tiers
  (multi-DUT switch fabric) is selectable via CLI flag.

**What it inherits from the existing plan:**

- The IPv6+SRH flow build pattern is taken directly from
  [test_tc001021141_isisipv6sr_rawtraffic.py:289-335](./tests/isis/test_tc001021141_isisipv6sr_rawtraffic.py)
  (Test 5 in the plan above). That test is the canonical proof that the snappi
  model and the snappi-ixnetwork translator handle raw IPv6+SRH end-to-end.
- The audit conventions documented in §8 of the existing plan ("`valueType`
  on traffic-stack fields") apply here when reasoning about
  `flow.size.weight_pairs.custom` and segment-list increment patterns.
- The endpoint-behavior / SID-structure mappings in §9 are not relevant for
  this test (no SID emission via control plane), but the same translator
  code path is exercised by setting `flow.packet[].ipv6_extension_header.routing.
  segment_routing.segment_list[].segment.value`.

**Translator status:**

> ✅ All required snappi model fields and translator paths are already
> implemented and proven by Test 5. **No translator change is required for
> this new test.**

---

## 1. Source specification

[/home/ixia/nts-gitlab/ixnet_srv6/sonic-mgmt/docs/testplan/snappi/srv6_performance_test.md](../sonic-mgmt/docs/testplan/snappi/srv6_performance_test.md)

Headline requirements (the design follows these verbatim):

- Topology-agnostic. Recommended: nut-2tiers (multi-DUT) or snake (single-DUT
  loopback). Must work with N TG ports (N even, ≥ 2) split into two halves.
- TG port pairs send bidirectional raw IPv6 + (optional) SRH traffic.
- Each pair uses a SID path that does not share any link with any other pair
  (congestion-free by design). Spec gives explicit formulas for both
  topologies.
- DUT pre-staged with SRv6 MY_SIDs (`fcbb:bbbb::/48` family) and static routes.
- Test parameters (parametrised):
  - `test_duration` ∈ {1m, 5m, 15m, 60m, 1d, 2d}
  - `packet_size` ∈ {128, 256, 4096, "mix" — 128 fixed at 1 %, remainder split}
  - `collect_interval` — DUT counter / TG metric polling cadence
- Metrics (two pools):
  - **TG-side** — snappi `flow_metrics`: Tx/Rx, loss, latency min/avg/max
  - **DUT-side** — `show srv6 stats`:
    - Labels: `device.id` (switch hostname), `device.srv6.my_sid` (IPv6 prefix)
    - Metrics: `srv6.my_sid.rx.bytes`, `srv6.my_sid.rx.packets`

---

## 2. Decisions captured (from review)

| Decision | Choice | Rationale |
|---|---|---|
| Default topology | **Snake** (single-DUT). nut-2tiers via CLI flag. | Snake needs only one DUT; faster CI ramp-up. |
| Mix packet-size split | `[(128, 1), (256, 49.5), (4096, 49.5)]` | Symmetric remainder split; spec only fixes 128 at 1 %. |
| Initial duration scope | **1 min, 5 min, 15 min only** | All fit `flow.duration.fixed_seconds`; no continuous-mode/checkpointing complexity in this iteration. 60 m / 1 d / 2 d deferred. |
| Expected MY_SID source | **Computed from spec formula at test time** | Same formula drives TG SID lists and DUT precondition check — guaranteed self-consistent. |
| Loss tolerance | **0 % strict** | Durations ≤ 15 min on a congestion-free design — any loss is a real failure. |
| Latency assertions | **Record only** | Budget assertions deferred until production baselines are known. |
| DUT counterpoll | **Enabled by test fixture, restored on teardown** | Test owns its own pre-conditions; no implicit reliance on global DUT state. |

---

## 3. Architecture overview

```
sonic-mgmt/
└── tests/
    ├── common/snappi_tests/                   ← read-only reuse
    │   ├── snappi_fixtures.py                   - snappi_api, tgen_ports
    │   └── traffic_generation.py                - run_traffic (pattern reference)
    ├── srv6/                                  ← read-only reuse
    │   └── srv6_utils.py                        - validate_srv6_counters,
    │                                              clear_srv6_counters,
    │                                              enable_srv6_counterpoll,
    │                                              set_srv6_counterpoll_interval,
    │                                              get_srv6_mysid_entry_usage
    └── snappi_tests/
        ├── variables.py                       ← may add an SRv6 testbed entry
        └── srv6/                              ← NEW (this test)
            ├── __init__.py
            ├── conftest.py                    - pytest_addoption + fixtures
            ├── test_srv6_dataplane_performance.py   - the test
            └── files/
                ├── __init__.py
                ├── srv6_perf_constants.py     - LOCATOR_BLOCK, MIX_WEIGHTS, ...
                ├── srv6_perf_helper.py        - flow build, SID math, polling
                └── test_sid_paths.py          - pure-function unit tests
```

Layering follows the same convention used by `tests/snappi_tests/pfc/` and
other feature-folders under `snappi_tests/`.

---

## 4. Module-by-module design

### 4.1 `files/srv6_perf_constants.py`

```python
# Locator block per spec ("If using fcbb:bbbb:: as the locator block ...")
LOCATOR_BLOCK = "fcbb:bbbb"
PREFIX_LEN = 48

# Mix packet-size composition. Spec fixes 128 at 1 %; the rest is split evenly.
# Each tuple is (size_bytes, weight). Weights need not sum to 100 — IxN
# normalises them.
MIX_WEIGHTS = [(128, 1), (256, 49.5), (4096, 49.5)]

# Default rate per direction. 100 kpps × 256 B ≈ 200 Mbps — comfortable on
# 100 GbE links and well below DUT line-rate.
DEFAULT_RATE_PPS = 100_000

# Latency mode. store_forward is the snappi default and matches IxNetwork
# behaviour without forcing cut-through (which has port-speed restrictions).
DEFAULT_LATENCY_MODE = "store_forward"

# DUT counterpoll interval (ms). 1000 ms is the snappi-side polling floor;
# faster than that the DUT counters do not refresh meaningfully.
DEFAULT_COUNTERPOLL_INTERVAL_MS = 1000

# Polling-loop robustness.
MAX_CONSEC_FAIL = 5

# MTU prerequisite — 4096-byte frames need at least 4200 (4096 + headers + FCS).
MIN_MTU_BYTES = 4200
```

### 4.2 `files/srv6_perf_helper.py`

#### 4.2.1 Port pairing

```python
def pair_ports(snappi_ports):
    """Split N ports (N even ≥ 2) into N/2 (tx, rx) tuples (first half ↔ second).

    snappi_ports is the list returned by the `tgen_ports` fixture
    (each entry is a dict with at least 'name', 'location', 'peer_port',
    'duthost' — see tests/common/snappi_tests/snappi_fixtures.py:469).
    """
    n = len(snappi_ports)
    assert n >= 2 and n % 2 == 0, f"need even ≥ 2 ports, got {n}"
    half = n // 2
    return list(zip(snappi_ports[:half], snappi_ports[half:]))
```

#### 4.2.2 Snake SID-path generator (spec verbatim)

Spec quote:
> `fcbb:bbbb:i00:i:hex(N + i):hex(2N + i)...hex(MN + i):hex(N+i)00::`,
> note: `hex(N+i)00` refers to the SRv6 SID of the receiving traffic generator.

```python
def make_snake_sid_path(i, N, M):
    """Snake topology forward SID list for sender index i (1 ≤ i ≤ N).

    Expansion (per spec):
        anchor_tx     = fcbb:bbbb:i00:
        first_dut_sid = i
        chain         = hex(N + i), hex(2N + i), ..., hex(MN + i)
        anchor_rx     = hex(N + i)00
    Returns the full IPv6 segment list as a Python list of strings, with
    the rightmost segment being the receiver-anchor SID.
    """
    head_anchor = f"{LOCATOR_BLOCK}:{i:x}00::"
    first       = f"{LOCATOR_BLOCK}:{i:x}::"
    chain       = [f"{LOCATOR_BLOCK}:{(k * N + i):x}::" for k in range(1, M + 1)]
    tail_anchor = f"{LOCATOR_BLOCK}:{(N + i):x}00::"
    return [head_anchor, first, *chain, tail_anchor]
```

> ⚠ The exact tokenisation of the spec formula (`i00`, `hex(N+i)00`, `hex(MN+i)`)
> deserves a worked example sanity-check at unit-test time — see §6.

#### 4.2.3 nut-2tiers SID-path generator

Spec defines two formulas — first half `0 ≤ i < M/2` and second half
`M/2 ≤ i < M` — each yielding N segment-lists per TG. Implementation:

```python
def make_nut2tiers_sid_path(i, M, N, group):
    """nut-2tiers SID lists for TG i, all N ports.

    `group` ∈ {"first", "second"}; the spec provides two distinct formulas
    for the two halves. Returns a list of N segment lists (one per TG port).
    Each segment list has 5 anchor/middle SIDs:

        first half  (i in 0..M/2-1):
            fcbb:bbbb : hex(i)0p : hex(16M)0p : hex(M/2 + i)0p :
                        hex(M/2 + i)hex(N + p) ::                  # for p = 1..N

        second half (i in M/2..M-1):
            fcbb:bbbb : hex(i)0p : hex(16M)0p : hex(i - M/2)0p :
                        hex(i - M/2)hex(N + p) ::                  # for p = 1..N
    """
```

Same caveat — the spec is dense; unit tests with hand-computed values are
the only safe validator.

#### 4.2.4 Reverse for partner direction

```python
def reverse_sid_path(sids):
    """Return the SID list for the partner direction.

    For snake the spec rule is: the i-th port on the other side sends with
    the reversed SID list of its partner. Symmetry holds; we just reverse
    the Python list. The first element becomes the new IPv6 DA, and the
    last element is the new receiver-anchor.
    """
    return list(reversed(sids))
```

#### 4.2.5 Apply packet size

```python
def apply_packet_size(flow, packet_size):
    """int → flow.size.fixed; "mix" → flow.size.weight_pairs.custom."""
    if isinstance(packet_size, int):
        flow.size.fixed = packet_size
    elif packet_size == "mix":
        wp = flow.size.weight_pairs
        wp.choice = "custom"
        for size, weight in MIX_WEIGHTS:
            row = wp.custom.add()
            row.size = size
            row.weight = weight
    else:
        raise ValueError(f"unsupported packet_size: {packet_size!r}")
```

> Confirmed mapping: `flow.size.weight_pairs.custom` →
> `snappi_ixnetwork/trafficitem.py:1733`.

#### 4.2.6 Apply duration

```python
def apply_duration(flow, duration_s):
    """For this iteration we only support fixed_seconds (≤ 900 s).

    Continuous mode + Python timer is deferred to the long-run follow-up
    (see "Out of scope").
    """
    assert duration_s <= 900, "long-run durations not yet supported"
    flow.duration.fixed_seconds.seconds = duration_s
```

#### 4.2.7 Build the snappi config

```python
def build_srv6_perf_config(
    snappi_api, snappi_ports, duration_s, packet_size,
    sid_paths_per_pair, rate_pps=DEFAULT_RATE_PPS,
    latency_mode=DEFAULT_LATENCY_MODE,
):
    """Assemble a snappi.Config from the topology + per-pair SID paths.

    sid_paths_per_pair is a list of (forward_sids, reverse_sids) tuples,
    one per port pair.

    For each pair we emit two flows (a→b and b→a). Each flow has the
    layered packet headers:
        ethernet
        ipv6 (next_header=43)
        ipv6_extension_header.routing.choice="segment_routing"
            segments_left = len(sids) - 1
            last_entry    = len(sids) - 1
            segment_list  = [{segment.value = sid} for sid in sids]

    flow.metrics is enabled with loss=True and latency.{enable=True,mode=...}.

    Returns the assembled Config (caller calls api.set_config separately).
    """
    config = snappi_api.config()

    # --- ports ---
    for sp in snappi_ports:
        config.ports.port(name=sp["name"], location=sp["location"])

    # --- layer1 ---
    l1 = config.layer1.layer1()[-1]
    l1.name = "srv6_perf_l1"
    l1.port_names = [p.name for p in config.ports]
    l1.speed = sp_speed_from_inventory(snappi_ports)   # see §4.2.8
    l1.media = sp_media_from_inventory(snappi_ports)

    # --- flows ---
    pairs = pair_ports(snappi_ports)
    for idx, ((tx, rx), (fwd_sids, rev_sids)) in enumerate(zip(pairs, sid_paths_per_pair)):
        for direction, src, dst, sids in [
            ("fwd", tx, rx, fwd_sids),
            ("rev", rx, tx, rev_sids),
        ]:
            f = config.flows.flow(name=f"srv6_perf_pair{idx}_{direction}")[-1]
            f.tx_rx.port.tx_name = src["name"]
            f.tx_rx.port.rx_name = dst["name"]
            f.rate.pps = rate_pps
            apply_packet_size(f, packet_size)
            apply_duration(f, duration_s)

            f.metrics.enable = True
            f.metrics.loss = True
            f.metrics.latency.enable = True
            f.metrics.latency.mode = latency_mode

            eth = f.packet.ethernet()[-1]
            eth.src.value = src["mac"]      # falls back to peer-derived MAC
            eth.dst.value = dst["mac"]

            ip6 = f.packet.ipv6()[-1]
            ip6.src.value = src["ipv6"]
            ip6.dst.value = sids[0]         # first SID becomes outer DA
            ip6.next_header.value = 43      # Routing extension header
            ip6.hop_limit.value = 64

            ext = f.packet.ipv6_extension_header()[-1]
            ext.routing.choice = "segment_routing"
            sr = ext.routing.segment_routing
            sr.segments_left.value = len(sids) - 1
            sr.last_entry.value    = len(sids) - 1
            sr.tag.value           = 0
            for sid in sids:
                seg = sr.segment_list.segment()[-1]
                seg.segment.value = sid

    return config
```

> ⚠ The exact field names (`config.ports.port(...).port(...)`,
> `config.layer1.layer1()[-1]`, `f.packet.ethernet()[-1]`) follow the
> chained-builder style used by both
> [snappi-ixnetwork conftest.py:74-101](./tests/conftest.py) and
> [test_tc001021141_isisipv6sr_rawtraffic.py:289-335](./tests/isis/test_tc001021141_isisipv6sr_rawtraffic.py).
> If sonic-mgmt's `snappi_testbed_config` already produces a partially built
> config, we wrap rather than rebuild.

#### 4.2.8 MY_SID computation + DUT precondition

```python
def compute_expected_mysids(topology, M, N):
    """Reuse the SID-path formula to derive the set of DUT-owned MY_SIDs.

    For snake: any segment fcbb:bbbb:hex(k)::/48 with 1 ≤ k ≤ MN must exist
    on the DUT (because the DUT is the only switching node).

    For nut-2tiers: the middle segments (hex(16M)0p, hex(M/2 ± i)0p) belong
    to the spine DUT(s); first/last anchors belong to the leaf DUTs. We
    return a dict keyed by DUT hostname and require the caller to pass a
    DUT-index map (which DUT terminates which SID).

    Returns: dict[hostname, list[mysid_with_prefix]]
    """

def precheck_dut_my_sids_present(duthosts, expected):
    """One-shot sanity check before traffic.

    For each (host, mysid) in `expected`:
        stats = duthost.show_and_parse('show srv6 stats')
        if mysid not in {row['mysid'] for row in stats}:
            pytest.skip(f"DUT {host} missing required MY_SID {mysid}")
    """
```

#### 4.2.9 Periodic metric collection

```python
def collect_periodic_metrics(api, duthosts_by_host, mysids_per_host,
                             flow_names, total_s, interval_s, artifacts_dir):
    """Wall-clock-aligned polling loop. Writes JSONL incrementally.

    Tick body:
        1. req = api.metrics_request()
           req.flow.flow_names = flow_names
           rows = api.get_metrics(req).flow_metrics
           per-flow: frames_tx, frames_rx, frames_tx_rate, frames_rx_rate,
                     bytes_tx, bytes_rx, loss, latency.{minimum,average,maximum}_ns
        2. For each host in duthosts_by_host:
           stats = duthost.show_and_parse('show srv6 stats')
           filter rows where row['mysid'] in mysids_per_host[host]
        3. Append snapshot {ts, flows: [...], duts: {host: [...]}} to
           <artifacts_dir>/snapshots.jsonl.

    Robustness: each fetch wrapped in try/except + log; abort with
    descriptive failure after MAX_CONSEC_FAIL consecutive failures (per source).

    Schedule: next_tick = start + k*interval; sleep max(0, next_tick - now).

    Returns the list of all snapshots (also persisted on disk).
    """
```

#### 4.2.10 Aggregation + assertions

```python
def summarise(snapshots):
    """Aggregate JSONL into <artifacts_dir>/summary.json.

    Per flow (last snapshot wins):
        last_frames_tx, last_frames_rx, computed_loss_pct,
        last_frames_tx_rate, last_frames_rx_rate,
        latency_min_ns (min over snapshots), latency_avg_ns (mean),
        latency_max_ns (max).

    Per (host, mysid):
        first_packets, last_packets, delta_packets,
        first_bytes,   last_bytes,   delta_bytes.
    """

def assert_no_loss(summary, tolerance_pct=0.0):
    for flow_name, row in summary["flows"].items():
        assert row["loss_pct"] <= tolerance_pct, (
            f"{flow_name}: loss {row['loss_pct']} > tolerance {tolerance_pct}"
        )

def assert_dut_counters_increase(summary, expected_per_pair_tx, min_ratio=0.9):
    """For each (host, mysid): delta_packets > 0 AND
    delta_packets ≥ min_ratio × expected_per_pair_tx[(host, mysid)] (when known)."""
```

### 4.3 `conftest.py`

```python
def pytest_addoption(parser):
    g = parser.getgroup("srv6_perf")
    g.addoption("--srv6-topology", choices=["snake", "nut2tiers"], default=None,
                help="Override topology selection (default: snake unless testbed says otherwise).")
    g.addoption("--srv6-m", type=int, default=1,
                help="Topology M dimension (DUT layers for nut-2tiers; otherwise 1).")
    g.addoption("--srv6-n", type=int, default=None,
                help="Topology N dimension (TG ports per group). Default: derived from tgen_ports.")
    g.addoption("--srv6-collect-interval", type=int, default=5,
                help="Seconds between metric polls (default 5).")
    g.addoption("--srv6-rate-pps", type=int, default=DEFAULT_RATE_PPS)
    g.addoption("--srv6-loss-tolerance-pct", type=float, default=0.0)


@pytest.fixture(scope="module")
def srv6_perf_ports(tgen_ports):
    n = len(tgen_ports)
    if n < 2 or n % 2 != 0:
        pytest.skip(f"srv6_perf needs even ≥ 2 TG ports; got {n}")
    return tgen_ports


@pytest.fixture(scope="module")
def srv6_topology_mode(request, tbinfo):
    cli  = request.config.getoption("--srv6-topology")
    env  = os.environ.get("SRV6_TOPOLOGY")
    var  = (variables.SRV6_PORT_INFO.get(tbinfo["conf-name"], {}).get("topology")
            if hasattr(variables, "SRV6_PORT_INFO") else None)
    return cli or env or var or "snake"


@pytest.fixture(scope="function")
def srv6_perf_artifacts_dir(tmp_path_factory, request):
    d = tmp_path_factory.mktemp(f"srv6_perf_{request.node.name}")
    return d


@pytest.fixture(scope="module")
def srv6_counterpoll_setup(duthosts):
    saved = {}
    for d in duthosts:
        saved[d.hostname] = srv6_utils.get_srv6_counterpoll_status(d)
        srv6_utils.enable_srv6_counterpoll(d)
        srv6_utils.set_srv6_counterpoll_interval(
            d, DEFAULT_COUNTERPOLL_INTERVAL_MS,
        )
    yield
    for d in duthosts:
        # Restore prior status (best-effort).
        ...


@pytest.fixture(scope="function")
def srv6_clear_counters_setup(duthosts):
    for d in duthosts:
        srv6_utils.clear_srv6_counters(d)
    yield
```

### 4.4 `test_srv6_dataplane_performance.py`

```python
@pytest.mark.topology("snappi", "tgen")
@pytest.mark.parametrize("packet_size", [128, 256, 4096, "mix"])
@pytest.mark.parametrize(
    "test_duration_s",
    [pytest.param(60,  id="1min"),
     pytest.param(300, id="5min"),
     pytest.param(900, id="15min")],
)
def test_srv6_dataplane_performance(
    snappi_api, duthosts,
    srv6_perf_ports, srv6_topology_mode,
    srv6_perf_artifacts_dir,
    srv6_counterpoll_setup, srv6_clear_counters_setup,
    test_duration_s, packet_size, request,
):
    M = request.config.getoption("--srv6-m")
    N = request.config.getoption("--srv6-n") or (len(srv6_perf_ports) // 2)
    rate_pps          = request.config.getoption("--srv6-rate-pps")
    interval_s        = request.config.getoption("--srv6-collect-interval")
    loss_tolerance    = request.config.getoption("--srv6-loss-tolerance-pct")

    # 1. SID-path generation
    if srv6_topology_mode == "snake":
        sid_paths_per_pair = [
            (make_snake_sid_path(i + 1, N, M),
             reverse_sid_path(make_snake_sid_path(i + 1, N, M)))
            for i in range(N)
        ]
    else:
        sid_paths_per_pair = build_nut2tiers_pairings(M, N)   # in helper

    # 2. DUT precondition
    expected = compute_expected_mysids(srv6_topology_mode, M, N)
    precheck_dut_my_sids_present(duthosts, expected)

    # 3. Snappi config + push
    config = build_srv6_perf_config(
        snappi_api, srv6_perf_ports, test_duration_s, packet_size,
        sid_paths_per_pair, rate_pps=rate_pps,
    )
    snappi_api.set_config(config)

    # 4. Baseline DUT counters
    dut_before = collect_dut_my_sid_stats(duthosts, expected)

    # 5. Start traffic
    cs = snappi_api.control_state()
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    snappi_api.set_control_state(cs)

    # 6. Periodic poll
    flow_names = [f.name for f in config.flows]
    snapshots = collect_periodic_metrics(
        snappi_api, duthosts, expected, flow_names,
        total_s=test_duration_s, interval_s=interval_s,
        artifacts_dir=srv6_perf_artifacts_dir,
    )

    # 7. Stop + drain
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
    snappi_api.set_control_state(cs)
    time.sleep(2)

    # 8. Final samples + summary
    final = collect_one_snapshot(snappi_api, duthosts, expected, flow_names)
    summary = summarise(snapshots + [final])
    (srv6_perf_artifacts_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    # 9. Assertions
    assert_no_loss(summary, tolerance_pct=loss_tolerance)
    for fname, row in summary["flows"].items():
        assert row["last_frames_rx"] > 0, f"{fname} received no frames"
    assert_dut_counters_increase(summary, expected_per_pair_tx=...)
```

---

## 5. Data structures

### 5.1 Snapshot (one JSONL line)

```json
{
  "ts": "2026-05-12T14:23:01.512Z",
  "ts_monotonic_s": 12.451,
  "flows": [
    {"name": "srv6_perf_pair0_fwd",
     "frames_tx": 12345, "frames_rx": 12345,
     "frames_tx_rate": 100000.0, "frames_rx_rate": 100000.0,
     "bytes_tx": 3160320, "bytes_rx": 3160320,
     "loss": 0.0,
     "latency_min_ns": 412, "latency_avg_ns": 1024, "latency_max_ns": 2890}
  ],
  "duts": {
    "sonic-dut1": [
      {"mysid": "fcbb:bbbb:1::/48", "packets": 6172, "bytes": 1580160},
      {"mysid": "fcbb:bbbb:2::/48", "packets": 6173, "bytes": 1580416}
    ]
  }
}
```

### 5.2 Summary

```json
{
  "flows": {
    "srv6_perf_pair0_fwd": {
      "last_frames_tx": 6000000, "last_frames_rx": 6000000,
      "loss_pct": 0.0,
      "last_frames_tx_rate": 100000.0, "last_frames_rx_rate": 100000.0,
      "latency_min_ns": 401, "latency_avg_ns": 1018, "latency_max_ns": 3142
    }
  },
  "duts": {
    "sonic-dut1": {
      "fcbb:bbbb:1::/48": {
        "first_packets": 0,    "last_packets": 3000000, "delta_packets": 3000000,
        "first_bytes":   0,    "last_bytes":   768000000, "delta_bytes": 768000000
      }
    }
  },
  "params": {
    "topology": "snake", "M": 1, "N": 2,
    "duration_s": 60, "packet_size": 128, "rate_pps": 100000
  }
}
```

---

## 6. SID-path math — worked examples

### 6.1 Snake, M=1, N=2

For sender index i = 1:
- `head_anchor = fcbb:bbbb:100::`     ← `i00` = `100` (hex)
- `first       = fcbb:bbbb:1::`        ← `i` = `1`
- `chain       = [fcbb:bbbb:3::]`      ← `1*N + i = 1*2 + 1 = 3`
- `tail_anchor = fcbb:bbbb:300::`      ← `(N + i)00 = 3*0x100 = 300`

→ Full list: `[fcbb:bbbb:100::, fcbb:bbbb:1::, fcbb:bbbb:3::, fcbb:bbbb:300::]`.

For sender index i = 2:
- `head = fcbb:bbbb:200::`, `first = fcbb:bbbb:2::`,
- `chain = [fcbb:bbbb:4::]`, `tail = fcbb:bbbb:400::`.

The receiver-side (i = 1 partner) sends with `reverse(...)` of the sender's
list — i.e. `[fcbb:bbbb:300::, fcbb:bbbb:3::, fcbb:bbbb:1::, fcbb:bbbb:100::]`.

> These hand-derivations become the unit test fixtures in
> `files/test_sid_paths.py`.

### 6.2 nut-2tiers, M=2, N=2 (first half, i=0)

> Spec excerpt:
> ```
> fcbb:bbbb:hex(i)01:hex(16M)01:hex(M/2 + i)01:hex(M/2 + i)hex(N + 1)::
> fcbb:bbbb:hex(i)02:hex(16M)02:hex(M/2 + i)02:hex(M/2 + i)hex(N + 2)::
> ```

For M=2, N=2, i=0:
- 16M = 32 → hex = `20`
- M/2 + i = 1
- N + p = 3 (p=1) or 4 (p=2)

Port p=1: `fcbb:bbbb:001:2001:101:103::`
Port p=2: `fcbb:bbbb:002:2002:102:104::`

Walk through this carefully in unit tests; the `hex(i)0p` token is
tricky because the spec uses concatenation of `hex(i)` + `0` + `p` not
arithmetic.

---

## 7. Verification

1. **Static collection** —
   ```
   pytest --collect-only -q tests/snappi_tests/srv6/
   ```
   Must list exactly **12** test ids (`{1min, 5min, 15min} × {128, 256, 4096, mix}`).
   No `long_run` marker.

2. **Pure-function unit tests** —
   `tests/snappi_tests/srv6/files/test_sid_paths.py` (no TG, no DUT).
   Hand-computed expected SID lists from §6 are asserted against
   `make_snake_sid_path` and `make_nut2tiers_sid_path`. These tests run
   in any environment (no fixtures, no hardware).

3. **Smoke run on hardware** —
   ```
   cd sonic-mgmt
   pytest tests/snappi_tests/srv6/test_srv6_dataplane_performance.py \
          -k "1min and 128" \
          --inventory <inv> --testbed <tb> --testbed_file <tb_file> \
          --srv6-topology=snake --srv6-m=1
   ```
   Expectations: 60 s duration; `summary.json` shows `loss_pct == 0`,
   `frames_rx > 0` per flow, every expected MY_SID counter incremented.

4. **Mix-size run** —
   ```
   pytest -k "5min and mix" ...
   ```
   Validate `weight_pairs.custom` was honored on the wire by checking
   IxN per-stream stats via `api._traffic.Statistics` (no capture needed).

5. **Regression** — Re-run [test_tc001021141_isisipv6sr_rawtraffic.py](./tests/isis/test_tc001021141_isisipv6sr_rawtraffic.py)
   afterwards to confirm the shared SRH translator path was not disturbed.

---

## 8. Open implementation questions

| Q | Status |
|---|---|
| Where in `tgen_ports` dict does the **MAC** for `eth.src.value` come from? Is it pre-populated by sonic-mgmt or do we synthesise from a deterministic generator? | Read once during scaffolding; if synthetic, document the rule. |
| Do snake-mode partner SIDs really "reverse" 1:1, or is there a tail/head swap rule we are missing? Spec is brief on this. | Cover via unit tests with hand-derivation for M ∈ {1, 2}. |
| Per-DUT MY_SID ownership for nut-2tiers — does the spec implicitly tell us which DUT owns each segment? | Likely yes via the i / M/2 +i convention; document precisely in `compute_expected_mysids`. |
| `tgen_ports` provides `peer_port` and `duthost`. Confirm these survive in the snappi config so `flow.tx_rx.port.tx_name` resolves to the right snappi port. | Verify against an existing snappi-test (e.g. PFC) at scaffolding time. |
| `pytest.mark.topology` allowed values — can we use `"snappi"` and `"tgen"` together? | Mirror what `test_pfc_*.py` uses. |

---

## 9. Out of scope (deferred follow-ups)

- 60 min / 1 day / 2 day durations (need `flow.duration.continuous` +
  Python timer + JSONL checkpointing on top of polling).
- `long_run` pytest marker.
- nut-2tiers integration tested on real multi-DUT hardware (formula and
  resolver are in place; CI smoke run targets snake).
- Latency budget assertions.
- Per-DUT MY_SID counter validation across multiple DUTs in a single run.
- Reboot-during-traffic variants (covered separately under `tests/snappi_tests/reboot/`).

---

## 10. Appendix — reference SRH flow snippet

From the canonical proof of life
[test_tc001021141_isisipv6sr_rawtraffic.py:289-335](./tests/isis/test_tc001021141_isisipv6sr_rawtraffic.py):

```python
ip6 = f.packet.add()
ip6.choice = "ipv6"
ip6.ipv6.src.value = IPV6_SRC
ip6.ipv6.dst.value = IPV6_DST
ip6.ipv6.next_header.value = 43       # routing extension header

ext = f.packet.add()
ext.choice = "ipv6_extension_header"
ext.ipv6_extension_header.routing.choice = "segment_routing"
sr = ext.ipv6_extension_header.routing.segment_routing
sr.segments_left.value = SEGMENTS_LEFT
sr.last_entry.value    = LAST_ENTRY
sr.flags.protected.value = FLAG_PROTECTED
sr.flags.alert.value     = FLAG_ALERT
sr.tag.value             = TAG
for addr in SEGMENTS:
    seg_entry = sr.segment_list.segment()[-1]
    seg_entry.segment.value = addr
```

This is the exact pattern we mirror in `build_srv6_perf_config`.

---

## 11. Sign-off checklist

- [ ] Topology default & override mechanism agreed.
- [ ] Mix split agreed (`128:1, 256:49.5, 4096:49.5`).
- [ ] Duration scope agreed (1 min / 5 min / 15 min only for this iteration).
- [ ] MY_SID source agreed (computed from spec formula).
- [ ] Loss tolerance agreed (0 % strict).
- [ ] Latency = record-only agreed.
- [ ] File tree under `tests/snappi_tests/srv6/` agreed.
- [ ] Open questions in §8 reviewed (acceptable to resolve at scaffolding time).
- [ ] Sign-off to proceed to **Step C (pure-function unit tests + SID-path
       implementations)** then **Step B (full scaffolding + helpers + test)**.
