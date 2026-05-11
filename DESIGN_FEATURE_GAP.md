# Design Document: snappi ↔ IxNetwork-RestPy Feature Gap Analysis

**Project:** snappi-ixnetwork
**Scope:** Catalog every feature exposed by the snappi API and assess whether the `snappi_ixnetwork` wrapper translates it into IxNetwork RestPy calls.
**Audience:** Maintainers planning the next set of wrapper enhancements; consumers who need to know what is safely usable today.
**Date:** 2026-05-11

---

## 1. Purpose

The `snappi_ixnetwork` package is a translator: it accepts a declarative snappi `Config` and turns it into imperative `ixnetwork_restpy` calls against an IxNetwork chassis or VM. Because snappi is a vendor-neutral specification (open-traffic-generator) and RestPy is Keysight's IxNetwork SDK, the two surfaces evolve independently. This document maps every snappi feature against the wrapper's current implementation so that:

- **Users** know which snappi features will work, error out, or be silently downgraded.
- **Maintainers** have a prioritized backlog of gaps to close.
- **Reviewers** can distinguish *wrapper gaps* (RestPy already supports it; we just have not translated it) from *platform gaps* (IxNetwork itself does not support it).

The analysis is anchored to snappi 1.x as represented by [snappi.py](snappi.py) (~206k LoC, auto-generated from the OpenAPI spec), the wrapper at [snappi_ixnetwork/](snappi_ixnetwork/), and the vendored RestPy SDK at [ixnetwork_restpy/](ixnetwork_restpy/).

---

## 2. Architecture Recap

```
       snappi user code
              │
              ▼
   ┌────────────────────┐
   │   snappi (model)   │   snappi.py  — pure data classes + validation
   └─────────┬──────────┘
             │  Config / ControlState / ControlAction / MetricsRequest
             ▼
   ┌────────────────────┐
   │  snappi_ixnetwork  │   Api subclass; translates snappi → RestPy
   │      (wrapper)     │     - vport.py, lag.py, capture.py, trafficitem.py
   │                    │     - device/*.py per-protocol mappers
   │                    │     - protocolmetrics.py, ping.py, events.py
   └─────────┬──────────┘
             │  REST calls (POST/PATCH/GET JSON)
             ▼
   ┌────────────────────┐
   │ ixnetwork_restpy   │   testplatform/sessions/ixnetwork/...
   │   (SDK to IxN)     │   topology, traffic, statistics, vport, lag
   └─────────┬──────────┘
             │  HTTPS
             ▼
        IxNetwork API server
```

Conceptually, each top-level snappi `Config` attribute (`ports`, `lags`, `layer1`, `captures`, `devices`, `flows`, `events`, `options`, `lldp`, `stateful_flows`, `egress_only_tracking`) is handled by a corresponding module or sub-module inside `snappi_ixnetwork/`.

---

## 3. Methodology

1. **Inventory snappi features** by enumerating top-level config sections, device-emulation protocols, flow header types, layer-1/port knobs, capture filters, control state/action variants, and metric request types in [snappi.py](snappi.py).
2. **Inventory wrapper coverage** by scanning each wrapper file for the snappi types it dispatches on, plus markers like `NotImplementedError`, `not supported`, `TODO`, `FIXME`.
3. **Inventory RestPy surface** under [ixnetwork_restpy/testplatform/sessions/ixnetwork/](ixnetwork_restpy/) to classify each gap as **wrapper gap** vs **platform gap**.

Gap classification used throughout this document:

| Status | Meaning |
|---|---|
| ✅ Supported | Wrapper translates the feature; tests exist in `snappi_ixnetwork/tests/` or upstream pytest suites. |
| 🟡 Partial | Translated for some sub-options but not all; or works but with known caveats. |
| ❌ Wrapper gap | snappi exposes it, RestPy supports it, but the wrapper does not translate it. |
| 🚫 Platform gap | snappi exposes it but IxNetwork/RestPy does not support it — feature is structurally unattainable today. |
| ⚠️ Runtime error | Wrapper raises `NotImplementedError` / `SnappiIxnException` when this option is used. |

---

## 4. Feature Coverage Matrix (Summary)

| Area | Coverage | Detail § |
|---|---|---|
| Ports & Layer1 | ✅ Strong | §5.1 |
| LAG (LACP / Static) | ✅ Strong | §5.2 |
| Capture | 🟡 Good (PCAP→PCAPNG downgrade) | §5.3 |
| Flows — common headers (Eth/VLAN/IP/TCP/UDP/ICMP/ARP/MPLS/VXLAN/GRE/GTPv1) | ✅ Strong | §5.4 |
| Flows — newer headers (GTPv2, ICMPv6, IPv6 ext headers, IPv4 options) | 🟡 Mixed | §5.4 |
| Flow rate / size / duration / latency | ✅ Strong | §5.4 |
| Flow tx_rx (port / device endpoints) | ✅ Strong | §5.4 |
| BGPv4/v6 peer + routes | ✅ Strong | §5.5.1 |
| BGP EVPN, SR-TE, learned info | 🟡 Partial | §5.5.1 |
| ISIS (L1/L2, SR, SRv6) | 🟡 Partial — base solid, SRv6/SR-FRR partial | §5.5.2 |
| OSPFv2 / OSPFv3 | 🚫 Wrapper gap — no `device/ospf*.py` | §5.5.3 |
| RSVP-TE | 🚫 Wrapper gap — no `device/rsvp.py` | §5.5.4 |
| DHCPv4 / DHCPv6 client + server | 🚫 Wrapper gap | §5.5.5 |
| LLDP (emulation + metrics) | 🚫 Wrapper gap — `config.lldp` ignored | §5.5.6 |
| VXLAN (data plane) | ✅ Supported | §5.5.7 |
| MACsec | 🟡 No replay protection; no raw-traffic mode | §5.5.8 |
| MKA | ✅ Supported | §5.5.9 |
| RoCEv2 (v4/v6, QPs, CNP, DCQCN) | ✅ Supported | §5.5.10 |
| Control state — port link / capture | ✅ Supported | §5.6 |
| Control state — protocol start/stop, route-state | ✅ For BGP/ISIS; ❌ others | §5.6 |
| Control state — traffic start/stop/pause/resume | ✅ Supported | §5.6 |
| Control action — IPv4/IPv6 ping | ✅ Supported | §5.6 |
| Control action — others (BGP graceful-restart, ISIS LSP refresh, etc.) | ❌ Wrapper gap | §5.6 |
| Stateful flows | ❌ Wrapper gap | §5.7 |
| Egress-only tracking | 🟡 Partial | §5.7 |
| Events | 🟡 Surface-only — limited semantics | §5.8 |
| Metrics — port / flow / LAG / LACP | ✅ Supported | §5.9 |
| Metrics — BGPv4/v6, ISIS, MACsec, MKA, RoCEv2, convergence | ✅ Supported | §5.9 |
| Metrics — OSPFv2/v3, RSVP, DHCPv4/v6, LLDP, BMP server | ❌ Wrapper gap | §5.9 |

---

## 5. Detailed Gap Analysis

### 5.1 Ports & Layer1

Implemented in [snappi_ixnetwork/vport.py](snappi_ixnetwork/vport.py).

**Snappi surface used:** `Port`, `Layer1`, `Layer1AutoNegotiation`, `Layer1FlowControl`, `Layer1Ieee8021qbb`, `Layer1Ieee8023x`.

| Feature | Status | Notes |
|---|---|---|
| Port location (chassis/card/port assignment) | ✅ | `_assign_ports` via RestPy `vport.AssignPorts` |
| Speed (10M → 800G + VM-simulated steps) | ✅ | `vport.py` enumerates all snappi speed enums |
| Media (copper / fiber / SGMII) | ✅ | |
| MTU (64–14000) | ✅ | |
| Auto-negotiation (incl. RS-FEC negotiation) | ✅ | `Layer1AutoNegotiation` |
| IEEE 802.3x pause | ✅ | |
| IEEE 802.1Qbb PFC | ✅ | per-priority enable / dest MAC |
| Promiscuous mode | ✅ | |
| Dynamic speed change during a running test | ❌ | Speed is locked at `set_config()` — known wrapper behavior |
| Cable diagnostics, optics inventory | 🚫 | snappi does not model this; platform feature only |

**Minor:** [vport.py:881](snappi_ixnetwork/vport.py#L881) has a `TODO` for a warning log; cosmetic only.

### 5.2 LAG (Link Aggregation)

Implemented in [snappi_ixnetwork/lag.py](snappi_ixnetwork/lag.py).

| Feature | Status |
|---|---|
| `LagProtocolLacp` actor key / system ID / system priority / port priority | ✅ |
| LACP active/passive | ✅ |
| LACPDU periodic time / timeout | ✅ |
| `LagProtocolStatic` (LAG ID) | ✅ |
| Ethernet MAC / MTU per LAG port | ✅ |
| LAG-level VLAN tag (priority, VLAN ID) | ✅ |
| `LagMetricsRequest` / `LacpMetricsRequest` | ✅ |

No major snappi-surface gaps in LAG.

### 5.3 Capture

Implemented in [snappi_ixnetwork/capture.py](snappi_ixnetwork/capture.py).

| Feature | Status | Notes |
|---|---|---|
| `Capture.format = pcapng` | ✅ | |
| `Capture.format = pcap` | 🟡 | [capture.py:68-70](snappi_ixnetwork/capture.py#L68-L70) auto-converts to PCAPNG and warns. Acceptable trade-off, but worth documenting in user-facing release notes. |
| Hardware + software capture enable | ✅ | |
| Overwrite buffer mode | ✅ | |
| Capture filters: `CaptureEthernet`, `CaptureVlan`, `CaptureIpv4`, `CaptureIpv6`, `CaptureCustom`, `CaptureField` | ✅ | All five filter classes are translated. |
| Trigger by frame-size threshold | ✅ | |
| Trigger on CRC / checksum errors | ❌ Wrapper gap | RestPy `vport/capture/Trigger` exposes more conditions than the wrapper sets. |
| `get_capture()` retrieval to PCAP/PCAPNG | ✅ | |

### 5.4 Flows / Traffic

Implemented in [snappi_ixnetwork/trafficitem.py](snappi_ixnetwork/trafficitem.py) (~106 KB, the largest module).

#### 5.4.1 Header type coverage

The wrapper holds an explicit `_TYPE_TO_HEADER` ↔ `_HEADER_TO_TYPE` mapping. Any snappi header `choice` outside this map raises `NotImplementedError` at [trafficitem.py:1202-1203](snappi_ixnetwork/trafficitem.py#L1202-L1203).

| Header (snappi class) | Status |
|---|---|
| `FlowEthernet` | ✅ |
| `FlowVlan` (priority, CFI, TPID) | ✅ |
| `FlowIpv4`, `FlowIpv4Priority`, `FlowIpv4Tos`, `FlowIpv4Dscp` | ✅ |
| `FlowIpv4Options`, `FlowIpv4OptionsCustom` | ❌ Wrapper gap |
| `FlowIpv4Auto` (auto src/dst from devices) | 🟡 Partial — works for some endpoint combos |
| `FlowIpv6` | ✅ |
| `FlowIpv6ExtHeader` | ❌ Wrapper gap |
| `FlowTcp`, `FlowUdp` | ✅ |
| `FlowIcmp.echo`, `FlowIcmpEcho` | ✅ |
| `FlowIcmpv6`, `FlowIcmpv6Echo` | 🟡 echo only |
| `FlowArp` | ✅ |
| `FlowGre` | ✅ |
| `FlowMpls` (stacked labels, EXP, BoS, TTL) | ✅ |
| `FlowVxlan` (VNI) | ✅ — see VXLAN flow-group TODO note below |
| `FlowGtpv1`, `FlowGtpv1Option` | ✅ |
| `FlowGtpv2` | ❌ Wrapper gap |
| `FlowPfcPause` | ✅ |
| `FlowEthernetPause` | ✅ |
| `FlowCustom`, `FlowCustomMetricTag` | ✅ |
| MACsec header in raw flow | ⚠️ Runtime error at [trafficitem.py:928-930](snappi_ixnetwork/trafficitem.py#L928-L930) — only works via device-emulated endpoints. |
| `FlowSnmp`, `FlowGeneve`, `FlowSrh`, `FlowPpp` (if present in newer snappi versions) | ❌ Wrapper gap |

**Known TODOs** in flow translation:
- [trafficitem.py:521](snappi_ixnetwork/trafficitem.py#L521) — REST API timeout on very large flow configs.
- [trafficitem.py:1020, 1044, 2416, 2450](snappi_ixnetwork/trafficitem.py#L1020) — VXLAN flow-group workaround ("ixNetwork is not creating flow groups for vxlan").

#### 5.4.2 Rate / size / duration / tx_rx

| Feature | Status |
|---|---|
| `FlowRate` (bps / fps / kbps / mbps / gbps / pps / % line) | ✅ |
| `FlowSize.fixed / .increment / .random / .weight_pairs` | ✅ |
| `FlowDuration.continuous / .fixed_packets / .fixed_seconds / .burst` | ✅ |
| `FlowDurationInterBurstGap` (µs / auto) | ✅ |
| `FlowLatencyMetrics` (store-forward, cut-through) | ✅ |
| Latency histograms / percentiles | ❌ Wrapper gap — RestPy stat view supports it but wrapper does not expose. |
| `FlowTxRx` port-to-port (mesh, 1:1, 1:N) | ✅ |
| `FlowTxRx` device-to-device (`FlowRouter`) | ✅ |
| Update flow size/rate mid-test | 🟡 — frame-size update blocked for some header types. |
| Append flows dynamically | ✅ |

### 5.5 Device Emulation

Each snappi `Device` has child sub-objects for emulated protocols. The wrapper has a file per supported protocol under [snappi_ixnetwork/device/](snappi_ixnetwork/device/). Anything not listed there is a wrapper gap.

#### 5.5.1 BGPv4 / BGPv6 — [device/bgp.py](snappi_ixnetwork/device/bgp.py), [device/bgpevpn.py](snappi_ixnetwork/device/bgpevpn.py)

| snappi feature | Status |
|---|---|
| `BgpV4Peer` / `BgpV6Peer` (AS, hold/keepalive, MD5) | ✅ |
| `BgpV4Interface` / `BgpV6Interface` | ✅ |
| `BgpV4RouteRange` / `BgpV6RouteRange` | ✅ |
| `BgpAsPath`, `BgpAsPathSegment` | ✅ |
| `BgpCommunity`, `BgpExtCommunity` | ✅ |
| `BgpExtendedCommunity` (newer typed structure) | 🟡 partial |
| `BgpAddPath` capability | ✅ |
| `BgpCapability` (negotiation flags) | ✅ |
| `BgpAdvanced` | ✅ |
| `BgpGracefulRestart` | 🟡 — config supported, restart-as-action not exposed in control-action |
| `BgpUpdateReplay` | ❌ Wrapper gap |
| `BgpMplsLabelBindings` | 🟡 partial |
| `BgpV4EthernetSegment` / `BgpV6EthernetSegment` | ✅ |
| `BgpV4EvpnEvis` / `BgpV6EvpnEvis` (Type-1/2/3/5) | ✅ |
| `BgpV4EviVxlan` / `BgpV6EviVxlan` | ✅ |
| `BgpCMacIpRange` | ✅ |
| `BgpSrteV4Policy` / `BgpSrteV6Policy` segment-list | 🟡 partial |
| `BgpLearnedInformationFilter` + `get_metrics(choice=bgpv4)` learned routes | 🟡 partial — sessions/route counts yes; per-route attributes via separate query not surfaced. |
| `BgpAttributes` (programmatic per-prefix attributes) | ❌ Wrapper gap |

RestPy has 25+ BGP types under topology — wrapper covers the most-used ~70%.

#### 5.5.2 ISIS — [device/isis.py](snappi_ixnetwork/device/isis.py)

| snappi feature | Status |
|---|---|
| `IsisInterface` (L1/L2, broadcast / p2p, hello / hold) | ✅ |
| `IsisBasic` / `IsisAdvanced` | ✅ |
| `IsisAuthentication` (MD5, plain) | ✅ |
| `IsisV4RouteRange` / `IsisV6RouteRange` | ✅ |
| `IsisSegmentRouting`, `IsisSRCapability`, `IsisSRSrgb`, `IsisSRSrlb` | 🟡 — base SR yes; some advanced SR caps partial |
| `IsisSRv6Locator`, `IsisSRv6EndSid` | 🟡 partial — RestPy supports `isissrv6locator` etc.; mapping incomplete |
| `IsisGracefulRestart` | ❌ Wrapper gap |
| `IsisMT` (multi-topology) | ❌ Wrapper gap |
| `IsisInterfaceLinkProtection` (FRR) | ❌ Wrapper gap |
| `IsisInterfaceAdjacencySid` | 🟡 partial |
| `DeviceIsisMultiInstance` | ❌ Wrapper gap |

#### 5.5.3 OSPFv2 / OSPFv3 — **No wrapper file**

Snappi defines a full OSPFv2/OSPFv3 surface (`DeviceOspfv2Router`, `DeviceOspfv3Router`, `Ospfv2Interface`, `Ospfv3Interface`, `Ospfv2V4RouteRange`, `Ospfv3V6RouteRange`, `Ospfv2GracefulRestart`, `Ospfv3Capabilities`, `Ospfv3RouterInstance`, etc.). RestPy fully supports OSPF (`ospfv2router`, `ospfv3router`, `ospfv2pseudorouter`, `ospfv3pseudorouter` and friends).

**Status: ❌ Wrapper gap — entire OSPF family.** Adding `device/ospfv2.py` and `device/ospfv3.py` plus extending `ngpf.py` dispatch would unlock this. **Highest-impact single gap** in routing-protocol coverage.

#### 5.5.4 RSVP-TE — **No wrapper file**

Snappi exposes `DeviceRsvp`, `RsvpIpv4Interface`, `RsvpLspIpv4Interface`, ingress/egress P2P LSPs, `RsvpSessionAttribute`, `RsvpTspec`, `RsvpResourceAffinities`, `RsvpFastReroute`, `RsvpEro`/`RsvpEroSubobject`. RestPy has `rsvpteLsps`, `rsvpteif`, `rsvpp2pingresslsps`, `rsvpp2pegresslsps`.

**Status: ❌ Wrapper gap.** Similar lift to OSPF. Also unlocks the `RsvpMetricsRequest` flow.

#### 5.5.5 DHCP — **No wrapper file**

Snappi: `DeviceDhcpv4client`, `Dhcpv4ClientParams`, `DeviceDhcpv6client`, `DeviceDhcpv6ClientOptions`, `DeviceDhcpServer`. RestPy: `dhcpv4client`, `dhcpv6client`, `dhcpv6pdclient`, `dhcp4relayagenttlvprofile`, IANA/IAPD options.

**Status: ❌ Wrapper gap.** Pure wrapper work; no platform blockers.

#### 5.5.6 LLDP — **`config.lldp` ignored**

`Config.lldp`, `LldpConnection`, `LldpChassisId`, `LldpPortId`, `LldpSystemName`, `LldpOrgInfo` and `LldpMetricsRequest` are defined in snappi but the wrapper has no LLDP handler.

**Status: ❌ Wrapper gap.** Low complexity; RestPy supports LLDP via per-port LLDP settings.

#### 5.5.7 VXLAN — [device/vxlan.py](snappi_ixnetwork/device/vxlan.py)

`DeviceVxlan` is supported, including IPv4/IPv6 tunnels, unicast/multicast destinations, VNI, static VTEP info, ARP suppression. ✅ — but see flow-group TODOs called out in §5.4.

#### 5.5.8 MACsec — [device/macsec.py](snappi_ixnetwork/device/macsec.py)

| snappi feature | Status |
|---|---|
| `DeviceMacsec` static config (CA, cipher suite, offset) | ✅ |
| Cipher suites GCM-AES-128 / 256 / XPN-128 / 256 | ✅ |
| Replay protection / replay window | ⚠️ [macsec.py:207](snappi_ixnetwork/device/macsec.py#L207) — TODO, not implemented |
| MACsec in raw flow header (`FlowEthernet` + MACsec) | ⚠️ Runtime error in `trafficitem.py` — must use device endpoints |

#### 5.5.9 MKA — [device/mka.py](snappi_ixnetwork/device/mka.py)

Full snappi MKA surface (`Mka`, `MkaBasic`, `MkaKeyServer`, `MkaSupportedCipherSuites`, `MkaRekeyMode`, `MkaTx`, `MkaTxSc`) is supported. ✅

#### 5.5.10 RoCEv2 — [device/rocev2.py](snappi_ixnetwork/device/rocev2.py)

`Rocev2V4Interface`, `Rocev2V4Peer`, `Rocev2V6Interface`, `Rocev2V6Peer`, `Rocev2QPs`, `Rocev2QPParameters`, `Rocev2ConnectionType`, `Rocev2PerPortSettings`, `Rocev2CNP`, `Rocev2DCQCN`, `Rocev2Flows` are all supported. ✅

### 5.6 Control State & Control Action

Dispatched in [snappi_ixnetwork/snappi_api.py](snappi_ixnetwork/snappi_api.py).

| `ControlState.choice` → sub-choice | Status |
|---|---|
| `port.link` (up/down) | ✅ |
| `port.capture` (start/stop) | ✅ |
| `protocol.all` (start/stop all device groups) | ✅ |
| `protocol.route` (advertise/withdraw) — BGP, ISIS | ✅ |
| `protocol.route` — OSPF, RSVP, LDP | ❌ Wrapper gap (no protocol support upstream) |
| `protocol.lacp` (member admin state) | ✅ |
| `protocol.bgp` (graceful-restart, update-replay) | 🟡 partial |
| `protocol.isis` (LSP refresh, route range admin) | 🟡 partial |
| `traffic` (start / stop / pause / resume) | ✅ |

| `ControlAction.choice` → sub-choice | Status |
|---|---|
| `protocol.ipv4.ping` | ✅ via [ping.py](snappi_ixnetwork/ping.py) |
| `protocol.ipv6.ping` | ✅ via [ping.py](snappi_ixnetwork/ping.py) |
| `protocol.bgp.notification` (send NOTIFICATION) | ❌ Wrapper gap |
| `protocol.bgp.initiate_graceful_restart` | ❌ Wrapper gap |
| `protocol.isis.initiate_restart` | ❌ Wrapper gap |
| Any other action variant | ⚠️ Unknown-option error at [snappi_api.py:479-482](snappi_ixnetwork/snappi_api.py#L479-L482) |

### 5.7 Stateful Flows & Egress-Only Tracking

| Feature | Status | Notes |
|---|---|---|
| `Config.stateful_flows` | ❌ Wrapper gap | snappi defines stateful (typically TCP-app-emulation) flows; the wrapper does not map them to RestPy's `applib`/`AppLibrary` traffic surface. RestPy supports L4-7 app traffic via `layer47AppLibraryTraffic` — this is a wrapper gap, not a platform gap. |
| `Config.egress_only_tracking` + `EgressOnlyTrackingMetricsRequest` | 🟡 Partial | Some egress-tracking metric paths exist in `trafficitem.py` but the standalone `Config.egress_only_tracking` list is not fully wired to RestPy egress tracking views. |

### 5.8 Events

[snappi_ixnetwork/events.py](snappi_ixnetwork/events.py) is small (~1.4 KB).

- `Event.cp_events` (control-plane events) — surface emitted, but snappi expects a rich `EventCPEvents` schema (BGP state changes, ISIS adjacency changes). Coverage is shallow.
- `Event.dp_events` (data-plane events) — likewise shallow.
- No event filtering / subscription / async stream — snappi spec is ambivalent here; treat as **🟡 Partial**.

### 5.9 Metrics

Implemented in [snappi_ixnetwork/protocolmetrics.py](snappi_ixnetwork/protocolmetrics.py) and the results section of [trafficitem.py](snappi_ixnetwork/trafficitem.py).

| `MetricsRequest.choice` | Status |
|---|---|
| `port` | ✅ |
| `flow` | ✅ — includes latency (min/max/avg) and timestamps |
| `bgpv4`, `bgpv6` | ✅ |
| `isis` | ✅ |
| `lag`, `lacp` | ✅ |
| `macsec` | ✅ |
| `mka` | ✅ |
| `rocev2_ipv4`, `rocev2_ipv6`, `rocev2_flow` | ✅ |
| `convergence` | ✅ |
| `egress_only_tracking` | 🟡 partial |
| `ospfv2`, `ospfv3` | ❌ Wrapper gap |
| `rsvp` | ❌ Wrapper gap |
| `dhcpv4_client`, `dhcpv4_server`, `dhcpv6_client`, `dhcpv6_server` | ❌ Wrapper gap |
| `lldp` | ❌ Wrapper gap |
| `bmp_server` | ❌ Wrapper gap |
| Unknown / unmapped | ⚠️ `NotImplementedError` at [protocolmetrics.py:300](snappi_ixnetwork/protocolmetrics.py#L300) |

**Cross-cutting issue:** [protocolmetrics.py:6-8](snappi_ixnetwork/protocolmetrics.py#L6-L8) — TODO that pagination of the RestPy stat view is not handled. Large device-group counts will silently truncate at one page. This is a correctness risk for high-scale tests, independent of which metric type the user requests.

---

## 6. Cross-Cutting Concerns

### 6.1 Pagination of statistics views
Single biggest correctness risk: any large topology that overflows the IxNetwork stats-view page will return partial results. Fix is purely on the wrapper side — iterate the view with `StatViewAssistant` pagination.

### 6.2 Large-config REST timeouts
[trafficitem.py:521](snappi_ixnetwork/trafficitem.py#L521) TODO. Likely needs batching via RestPy `ResourceManager` import-config, similar to what [ixnetworkconfig.py](snappi_ixnetwork/ixnetworkconfig.py) already does for some paths. Currently per-flow REST calls dominate runtime for very large configs.

### 6.3 Mid-test updates
`set_config()` after `start_traffic()` is partially supported; certain header types disallow frame-size changes mid-run. This is undocumented in user-facing error messages.

### 6.4 Validation surface
[validation.py](snappi_ixnetwork/validation.py) is ~2.5 KB. Most user errors surface as RestPy-level exceptions rather than friendly snappi-level errors. Investing here would reduce support burden disproportionately.

### 6.5 Unknown-choice fallthrough
Several dispatchers (`trafficitem.py:1202`, `snappi_api.py:479-482`, `protocolmetrics.py:300`) raise on unmapped enum values. As snappi adds new enum members upstream, the wrapper will *break loudly* rather than no-op — this is the right default but means version drift between snappi and the wrapper is operationally visible.

---

## 7. Wrapper Gap vs Platform Gap

Of the gaps inventoried above, **all are wrapper gaps** with the following two exceptions, which are likely platform-level constraints worth confirming with IxNetwork product:

1. **MACsec in raw flow stack** — RestPy traffic stack templates may not expose MACsec at the packet-stack level; current model requires MACsec via emulated endpoints.
2. **Some latency histograms / percentile bins** — exposed in IxNetwork GUI but historically limited in RestPy programmatic access.

Everything else (OSPF, RSVP, DHCP, LLDP, stateful flows, LLDP metrics, OSPF/RSVP/DHCP metrics, GTPv2 flow header, IPv6 extension headers, advanced BGP/ISIS controls, statistics pagination) is **wrapper work** that does not require new IxNetwork capability.

---

## 8. Recommended Roadmap (prioritized)

1. **Stats-view pagination** — correctness risk at scale; small change, high impact. (§6.1)
2. **OSPFv2 / OSPFv3 emulation + metrics** — largest single missing protocol; both `device/ospf*.py` and `protocolmetrics.py` extension. (§5.5.3, §5.9)
3. **RSVP-TE emulation + metrics** — frequently requested for MPLS test setups. (§5.5.4, §5.9)
4. **DHCPv4 / DHCPv6 client emulation + metrics** — unblocks subscriber-scale tests. (§5.5.5, §5.9)
5. **LLDP emulation + metrics** — small effort, completes a top-level snappi config attribute that is currently silently ignored. (§5.5.6, §5.9)
6. **Flow header gaps: GTPv2, IPv6 extension headers, IPv4 options** — small, isolated additions to `_TYPE_TO_HEADER`. (§5.4.1)
7. **MACsec replay protection** — close out the [macsec.py:207](snappi_ixnetwork/device/macsec.py#L207) TODO. (§5.5.8)
8. **Stateful flows → RestPy AppLibrary mapping** — opens a whole feature category. (§5.7)
9. **Control-action expansion** — BGP NOTIFICATION, BGP graceful-restart initiation, ISIS LSP refresh. (§5.6)
10. **Large-config import-batching** — address [trafficitem.py:521](snappi_ixnetwork/trafficitem.py#L521) TODO via ResourceManager-style bulk push. (§6.2)
11. **Validation enrichment** — translate the most common RestPy errors into snappi-level diagnostics. (§6.4)

---

## 9. Glossary & References

- **snappi** — open-traffic-generator Python SDK (vendor-neutral). Surface lives in [snappi.py](snappi.py).
- **NGPF** — IxNetwork's "Next-Generation Protocol Framework". Snappi `Device` maps to NGPF DeviceGroups.
- **RestPy** — Keysight's REST-API Python SDK for IxNetwork. Surface lives in [ixnetwork_restpy/](ixnetwork_restpy/).
- **AppLibrary / L4-7 traffic** — RestPy stateful-flow surface, unused by the wrapper today.
- **`_TYPE_TO_HEADER` / `_HEADER_TO_TYPE`** — the dispatch tables in [trafficitem.py](snappi_ixnetwork/trafficitem.py) that gate header-type support.

For runtime markers cited throughout this document, search the repo for `NotImplementedError`, `not supported`, `TODO`, `FIXME`.
