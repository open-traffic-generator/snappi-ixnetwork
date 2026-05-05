# ISIS-SRv6 Implementation Design Document

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Snappi API Model](#snappi-api-model)
4. [IxNetwork RestPy to Snappi API Mapping](#ixnetwork-restpy-to-snappi-api-mapping)
5. [Implementation](#implementation)
6. [Back-to-Back SRv6 Test Case](#back-to-back-srv6-test-case)
7. [My Local SID Lifecycle Actions](#my-local-sid-lifecycle-actions)

---

## 1. Overview

### 1.1 What is ISIS-SRv6?

Segment Routing over IPv6 (SRv6) using IS-IS as the control plane is defined in:

- **RFC 8986** — SRv6 Network Programming
- **RFC 9252** — BGP Overlay Services Based on Segment Routing over IPv6 (SRv6)
- **RFC 9800** — SRv6 Micro-SID (uSID) Compressed Encoding
- **draft-ietf-lsr-isis-srv6-extensions** — IS-IS Extensions to Support Segment Routing over IPv6

In ISIS-SRv6, the router advertises:

- **SRv6 Capability** — signals that the router supports SRv6 (advertised in TLV 242, sub-TLV 25)
- **SRv6 Locator** — an IPv6 prefix that acts as a routing locator for the node (advertised in TLV 27)
- **SRv6 End SIDs** — SRv6 Segment Identifiers tied to a locator with specific endpoint behaviors
- **SRv6 Adjacency SIDs** — SRv6 SIDs bound to a specific adjacency (advertised in IS Reachability TLV 22 sub-TLVs)
- **My Local SID Table** — runtime table of locally instantiated SIDs (RFC 8986 Section 3.3)

### 1.2 SRv6 SID Structure

An SRv6 SID is a 128-bit IPv6 address structured as:

```
| Locator Block | Locator Node | Function | Argument |
|<-- B bits -->|<-- N bits -->|<-- F bits -->|<-- A bits -->|
```

Typical sizes: B=48, N=16, F=16, A=0

The translator computes the full SID from the locator prefix and function hex string:

```
network_address(locator / (B+N)) | (function_int << (128 - B - N - F))
```

### 1.3 Endpoint Behaviors

IxNetwork NGPF requires the **IANA SRv6 Endpoint Behavior code point** (integer) for the `endPointFunction` multivalue field — string names like `"End"` are rejected with `"Value End is not number"`.

| Snappi value | IANA code | Description |
|---|---|---|
| `end` | `1` | End (no PSP, no USP) |
| `end_with_psp` | `2` | End with PSP |
| `end_with_usp` | `3` | End with USP |
| `end_with_psp_usp` | `4` | End with PSP and USP |
| `end_with_usd` | `27` | End with USD |
| `end_with_psp_usd` | `28` | End with PSP and USD |
| `end_with_usp_usd` | `29` | End with USP and USD |
| `end_with_psp_usp_usd` | `30` | End with PSP, USP, USD |
| `end_dt4` | `18` | Endpoint with IPv4 table lookup |
| `end_dt6` | `17` | Endpoint with IPv6 table lookup |
| `end_dt46` | `19` | Endpoint with IPv4/IPv6 table lookup |
| `end_x` | `5` | End.X (no PSP, no USP) |
| `end_x_with_psp` | `6` | End.X with PSP |
| `end_x_with_usp` | `7` | End.X with USP |
| `end_x_with_psp_usp` | `8` | End.X with PSP and USP |
| `end_x_with_usd` | `31` | End.X with USD |
| `end_x_with_psp_usd` | `32` | End.X with PSP and USD |
| `end_x_with_usp_usd` | `33` | End.X with USP and USD |
| `end_x_with_psp_usp_usd` | `34` | End.X with PSP, USP, USD |
| `end_dx4` | `16` | End.DX4 |
| `end_dx6` | `15` | End.DX6 |

---

## 2. Architecture

### 2.1 Object Hierarchy in IxNetwork

```
Topology
  └── DeviceGroup
        ├── bridgeData              ← systemId
        ├── isisL3Router            ← router-level config + SRv6 caps
        │     ├── enableSR          ← set True when locators present
        │     ├── locatorCount      ← number of SRv6 locators
        │     ├── cFlagOfSRv6Cap    ← from srv6_capability.c_flag
        │     ├── oFlagOfSRv6CapTlv ← from srv6_capability.o_flag
        │     └── isisSRv6LocatorEntryList   (count = locatorCount)
        │           ├── locatorName, locator, prefixLength, locatorSize
        │           ├── metric, algorithm, dBit, mtId
        │           ├── redistribution, routeOrigin, routeMetric
        │           ├── advertiseLocatorAsPrefix, enableNFlag/RFlag/XFlag
        │           └── isisSRv6EndSIDList    (count = sidCount)
        │                 └── sid, endPointFunction, cFlag, lengths
        └── ethernet
              └── isisL3              ← interface-level config
                    ├── enableIPv6SID ← set True when adj SIDs present
                    └── isisSRv6AdjSIDList
                          └── ipv6AdjSid, endPointFunction, flags, lengths
```

### 2.2 Actual Snappi Object Model

The following reflects the **installed snappi package** API as used in the implementation.

```
Device
  └── isis (IsisRouter)
        ├── name
        ├── system_id
        └── segment_routing
              ├── router_capability
              │     └── srv6_capability
              │           ├── c_flag               # → cFlagOfSRv6Cap
              │           └── o_flag               # → oFlagOfSRv6CapTlv
              └── srv6_locators (list)
                    ├── locator_name               # → locatorName
                    ├── locator                    # → locator (IPv6 prefix)
                    ├── prefix_length              # → prefixLength
                    ├── algorithm                  # → algorithm
                    ├── metric                     # → metric
                    ├── d_flag                     # → dBit
                    ├── mt_id (list)               # → mtId[0]
                    ├── sid_structure
                    │     ├── locator_block_length # → locatorSize (B part)
                    │     ├── locator_node_length  # → locatorSize (N part)
                    │     ├── function_length      # → functionLength in end SIDs
                    │     └── argument_length      # → argumentLength in end SIDs
                    ├── advertise_locator_as_prefix
                    │     ├── redistribution_type  # → redistribution
                    │     ├── route_origin         # → routeOrigin
                    │     ├── route_metric         # → routeMetric
                    │     └── prefix_attributes
                    │           ├── n_flag         # → enableNFlag
                    │           ├── r_flag         # → enableRFlag
                    │           └── x_flag         # → enableXFlag
                    └── end_sids (list)
                          ├── function             # hex string → computed sid
                          ├── endpoint_behavior    # → endPointFunction (enum)
                          ├── argument             # hex string (optional)
                          └── c_flag               # → cFlag (uSID flag)

IsisInterface
  └── srv6_adjacency_sids (list)
        ├── locator                  # "auto" or "custom_locator_reference"
        ├── custom_locator_reference # locator name for custom ref
        ├── function                 # hex string → computed ipv6AdjSid
        ├── endpoint_behavior        # → endPointFunction (enum)
        ├── algorithm                # → algorithm
        ├── weight                   # → weight
        ├── b_flag                   # → bFlag
        ├── s_flag                   # → sFlag
        ├── p_flag                   # → pFlag
        ├── c_flag                   # → cFlag
        └── sid_structure
              ├── locator_block_length  # → locatorBlockLength
              ├── locator_node_length   # → locatorNodeLength
              ├── function_length       # → functionLength
              └── argument_length       # → argumentLength
```

> **SID computation**: Snappi does not carry a pre-built `sid` field. The translator constructs
> the full 128-bit IPv6 SID from the locator prefix + function hex:
>
> ```python
> net = ipaddress.IPv6Network(f"{locator}/{B+N}", strict=False)
> sid = str(IPv6Address(int(net.network_address) | (int(func_hex, 16) << (128 - B - N - F))))
> ```

---

## 3. Snappi API Model

### 3.1 `segment_routing.router_capability.srv6_capability`

| Field | Type | Description |
|---|---|---|
| `c_flag` | bool | C-Flag in SRv6 Capability sub-TLV |
| `o_flag` | bool | O-Flag in SRv6 Capability sub-TLV |

### 3.2 `segment_routing.srv6_locators` item

| Field | Type | Description |
|---|---|---|
| `locator_name` | str | Locator name string |
| `locator` | str | IPv6 locator prefix (e.g. `fc00:0:1::`) |
| `prefix_length` | int | Locator prefix length (bits) |
| `algorithm` | int | Algorithm (0=SPF, 128+=Flex-Algo) |
| `metric` | int | Locator metric |
| `d_flag` | bool | D-Bit in locator TLV |
| `mt_id` | list[int] | Multi-Topology IDs |
| `sid_structure.locator_block_length` | int | Locator block length (bits) |
| `sid_structure.locator_node_length` | int | Locator node length (bits) |
| `sid_structure.function_length` | int | Function field length (bits) |
| `sid_structure.argument_length` | int | Argument field length (bits) |
| `advertise_locator_as_prefix.redistribution_type` | str | `up` or `down` |
| `advertise_locator_as_prefix.route_origin` | str | `internal` or `external` |
| `advertise_locator_as_prefix.route_metric` | int | Route metric |
| `advertise_locator_as_prefix.prefix_attributes.n_flag` | bool | N-Flag |
| `advertise_locator_as_prefix.prefix_attributes.r_flag` | bool | R-Flag |
| `advertise_locator_as_prefix.prefix_attributes.x_flag` | bool | X-Flag |
| `end_sids` | list | End SIDs under this locator |

### 3.3 `end_sids` item

| Field | Type | Description |
|---|---|---|
| `function` | str | Hex function value (e.g. `"0001"`) |
| `endpoint_behavior` | str | Endpoint behavior (see Section 1.3) |
| `argument` | str | Hex argument value (optional, default `"0000"`) |
| `c_flag` | bool | Compression (uSID) flag (RFC 9800) |

> **Note**: The `locator` field was removed from `IsisSRv6.EndSid` in the P0 model
> update. End SIDs always inherit the locator prefix from their parent
> `IsisSRv6.Locator` object.

### 3.4 `interface.srv6_adjacency_sids` item

| Field | Type | Description |
|---|---|---|
| `locator` | str | `"auto"` or `"custom_locator_reference"` |
| `custom_locator_reference` | str | Locator name (when `locator="custom_locator_reference"`) |
| `function` | str | Hex function value (e.g. `"e001"`) |
| `endpoint_behavior` | str | Endpoint behavior (typically `end_x`) |
| `algorithm` | int | Algorithm |
| `weight` | int | Weight |
| `b_flag` | bool | B-Flag |
| `s_flag` | bool | S-Flag |
| `p_flag` | bool | P-Flag |
| `c_flag` | bool | C-Flag |
| `sid_structure.locator_block_length` | int | Locator block length (bits) |
| `sid_structure.locator_node_length` | int | Locator node length (bits) |
| `sid_structure.function_length` | int | Function length (bits) |
| `sid_structure.argument_length` | int | Argument length (bits) |

---

## 4. IxNetwork RestPy to Snappi API Mapping

### 4.1 `isisL3Router` — SRv6 Global Fields

| Snappi API Path | IxNetwork JSON key | Notes |
|---|---|---|
| `segment_routing.router_capability.srv6_capability.c_flag` | `cFlagOfSRv6Cap` | Bool multivalue |
| `segment_routing.router_capability.srv6_capability.o_flag` | `oFlagOfSRv6CapTlv` | Bool multivalue |
| *(set True when srv6_locators non-empty)* | `enableSR` | Bool multivalue |
| `len(srv6_locators)` | `locatorCount` | Int scalar |

### 4.2 `isisSRv6LocatorEntryList` — SRv6 Locator

| Snappi API Path | IxNetwork JSON key | Notes |
|---|---|---|
| `locator_name` | `locatorName` | String list `[name]` |
| `locator` | `locator` | IPv6 multivalue |
| `prefix_length` | `prefixLength` | Int multivalue |
| `metric` | `metric` | Int multivalue |
| `algorithm` | `algorithm` | Int multivalue |
| `d_flag` | `dBit` | Bool multivalue |
| `mt_id[0]` | `mtId` | Int multivalue |
| `sid_structure.locator_block_length + locator_node_length` | `locatorSize` | Int multivalue |
| `advertise_locator_as_prefix` present | `advertiseLocatorAsPrefix` | Bool multivalue |
| `advertise_locator_as_prefix.redistribution_type` | `redistribution` | Enum multivalue |
| `advertise_locator_as_prefix.route_origin` | `routeOrigin` | Enum multivalue |
| `advertise_locator_as_prefix.route_metric` | `routeMetric` | Int multivalue |
| ~~`advertise_locator_as_prefix.prefix_attributes.n_flag`~~ | ~~`enableNFlag`~~ | Not sent — `invalidJsonProperty` on this IxN server version |
| ~~`advertise_locator_as_prefix.prefix_attributes.r_flag`~~ | ~~`enableRFlag`~~ | Not sent — `invalidJsonProperty` on this IxN server version |
| ~~`advertise_locator_as_prefix.prefix_attributes.x_flag`~~ | ~~`enableXFlag`~~ | Not sent — `invalidJsonProperty` on this IxN server version |
| `len(end_sids)` | `sidCount` | Int scalar |

### 4.3 `isisSRv6EndSIDList` — End SID

| Snappi API Path | IxNetwork JSON key | Notes |
|---|---|---|
| *(computed: locator prefix + function hex)* | `sid` | IPv6 multivalue |
| `endpoint_behavior` | `endPointFunction` | **Integer** multivalue (IANA code, see Section 1.3) |
| `c_flag` | `cFlag` | Bool multivalue |
| *(from parent locator sid_structure)* | `locatorBlockLength` | Int multivalue |
| *(from parent locator sid_structure)* | `locatorNodeLength` | Int multivalue |
| *(from parent locator sid_structure)* | `functionLength` | Int multivalue |
| *(from parent locator sid_structure)* | `argumentLength` | Int multivalue |

### 4.4 `isisL3` Interface — SRv6 Adjacency SID

| Snappi API Path | IxNetwork JSON key | Notes |
|---|---|---|
| *(set True when srv6_adjacency_sids present)* | `enableIPv6SID` | Bool multivalue |
| *(computed: locator ref + function hex)* | `ipv6AdjSid` | IPv6 multivalue |
| `endpoint_behavior` | `endPointFunction` | **Integer** multivalue (IANA code, see Section 1.3) |
| `algorithm` | `algorithm` | Int multivalue |
| `weight` | `weight` | Int multivalue |
| `b_flag` | `bFlag` | Bool multivalue |
| `s_flag` | `sFlag` | Bool multivalue |
| `p_flag` | `pFlag` | Bool multivalue |
| `c_flag` | `cFlag` | Bool multivalue |
| `sid_structure.locator_block_length` | `locatorBlockLength` | Int multivalue |
| `sid_structure.locator_node_length` | `locatorNodeLength` | Int multivalue |
| `sid_structure.function_length` | `functionLength` | Int multivalue |
| `sid_structure.argument_length` | `argumentLength` | Int multivalue |

---

## 5. Implementation

### 5.1 Files Modified

| File | Change |
|---|---|
| `snappi_ixnetwork/device/isis.py` | Added `_configure_srv6`, `_configure_srv6_router_capability`, `_configure_srv6_locator_list`, `_configure_srv6_end_sid_list`, `_configure_adjacency_sids`, `_resolve_adj_sid`, `_construct_srv6_sid`. Added `import ipaddress`. Fixed three IxNetwork compatibility issues (see Section 5.4). |
| `snappi_ixnetwork/device/isis_srv6_actions.py` | New file: `IsisSRv6Actions` class implementing My Local SID lifecycle (add/modify/delete) via IxNetwork on-the-fly updates. |
| `snappi_ixnetwork/device/ngpf.py` | Added four SRv6 class names to `_DEVICE_ENCAP_MAP`. |
| `snappi_ixnetwork/snappi_api.py` | Added ISIS SRv6 control action handling in `set_control_action`. |

### 5.2 Key Methods in `Isis` class

#### `_configure_srv6(isis, ixn_isis_router)`

Entry point called from `_config_isis_router`. Reads `isis.get("segment_routing")`, delegates to capability and locator methods, sets `enableSR=True` and `locatorCount` when locators are present.

#### `_configure_srv6_router_capability(rc, ixn_isis_router)`

Maps `c_flag` → `cFlagOfSRv6Cap` and `o_flag` → `oFlagOfSRv6CapTlv`.

#### `_configure_srv6_locator_list(srv6_locators, ixn_isis_router)`

Builds `isisSRv6LocatorEntryList`. For each locator:

- Sets `locatorName` as list `[name]`
- Computes `locatorSize = block_len + node_len` from `sid_structure`
- Handles `advertise_locator_as_prefix` block
- Caches locator info in `_srv6_locator_map` for adj SID resolution
- Calls `_configure_srv6_end_sid_list` for the locator's `end_sids`

#### `_configure_srv6_end_sid_list(end_sids, ixn_locator, locator_prefix, block_len, node_len, func_len, arg_len)`

Builds `isisSRv6EndSIDList`. Computes each SID via `_construct_srv6_sid` and sets all length fields from the parent locator's `sid_structure`.

#### `_configure_adjacency_sids(interface, ixn_isis)`

Called from `_config_isis_interface`. Sets `enableIPv6SID=True`, builds `isisSRv6AdjSIDList`. Resolves each adj SID via `_resolve_adj_sid`.

#### `_resolve_adj_sid(locator_choice, custom_locator_ref, function_hex)`

Resolves the full IPv6 adj SID using `_srv6_locator_map`. When `locator="auto"` uses the first cached locator; when `locator="custom_locator_reference"` looks up by name.

#### `_construct_srv6_sid(locator_prefix, block_len, node_len, function_hex, func_len, argument_hex, arg_len)`

```python
net = ipaddress.IPv6Network(f"{locator_prefix}/{block_len+node_len}", strict=False)
sid_int = int(net.network_address) | (int(function_hex, 16) << (128 - block_len - node_len - func_len))
return str(ipaddress.IPv6Address(sid_int))
```

### 5.4 IxNetwork Compatibility Notes

Three issues were discovered and fixed during test execution:

| Issue | Symptom | Fix |
|---|---|---|
| `enableSR` is a scalar bool on `isisL3Router`, not a multivalue | `type kBool is not kMultivalue` | Set `ixn_isis_router["enableSR"] = True` directly (no `self.multivalue()` wrapper) |
| `enableNFlag/enableRFlag/enableXFlag` not valid on this IxN server version | `invalidJsonProperty enableNFlag` | Omit these attributes entirely |
| `endPointFunction` expects IANA integer codes, not string names | `Value End is not number` | Map endpoint behaviors to their IANA code point integers (e.g. `"end"` → `1`, `"end_x"` → `5`) |

### 5.3 `ngpf.py` additions

```python
"IsisRouterSRv6Capability": "ethernetVlan",
"IsisRouterSRv6Locator":    "ethernetVlan",
"IsisRouterSRv6EndSid":     "ethernetVlan",
"IsisInterfaceSRv6AdjSid":  "ethernetVlan",
```

---

## 6. Back-to-Back SRv6 Test Case

### 6.1 Topology

```
+------------------+              +------------------+
|   Port 1 (P1)    |   b2b link   |   Port 2 (P2)    |
|  Device: p1d1    +--------------+  Device: p2d1    |
|  MAC: 00:00:00:01:01:01        |  MAC: 00:00:00:02:02:02 |
|  IPv4: 1.1.1.2/24              |  IPv4: 1.1.1.1/24       |
|                  |              |                  |
|  ISIS L2 P2P     |              |  ISIS L2 P2P     |
|  SystemID:       |              |  SystemID:       |
|  670000000001    |              |  680000000001    |
|                  |              |                  |
|  Locator:        |              |  Locator:        |
|  fc00:0:1::/48   |              |  fc00:0:2::/48   |
|  End SID func=1  |              |  End SID func=1  |
|  → fc00:0:1:0:1::|              |  → fc00:0:2:0:1::|
|                  |              |                  |
|  Adj SID func=e001              |  Adj SID func=e001      |
|  →fc00:0:1:0:e001::             |  →fc00:0:2:0:e001::     |
+------------------+              +------------------+
```

### 6.2 SID Structure

| Parameter | Value |
|---|---|
| Locator block length (B) | 48 bits |
| Locator node length (N) | 16 bits |
| Function length (F) | 16 bits |
| Argument length (A) | 0 bits |
| `locatorSize` (B+N) | 64 bits |

### 6.3 Expected SID Values

| Router | Locator | Function hex | Computed SID |
|---|---|---|---|
| p1d1 End SID | `fc00:0:1::/48` | `1` | `fc00:0:1:0:1::` |
| p1d1 Adj SID | `fc00:0:1::/48` | `e001` | `fc00:0:1:0:e001::` |
| p2d1 End SID | `fc00:0:2::/48` | `1` | `fc00:0:2:0:1::` |
| p2d1 Adj SID | `fc00:0:2::/48` | `e001` | `fc00:0:2:0:e001::` |

### 6.4 Test Code

See `tests/isis/test_isis_srv6.py` for the full test. Key snippet:

```python
# SRv6 capability
p1d1_srv6_cap = p1d1_isis.segment_routing.router_capability.srv6_capability
p1d1_srv6_cap.c_flag = False
p1d1_srv6_cap.o_flag = False

# SRv6 locator
p1d1_loc = p1d1_isis.segment_routing.srv6_locators.add()
p1d1_loc.locator_name = "loc1"
p1d1_loc.locator = "fc00:0:1::"
p1d1_loc.prefix_length = 48
p1d1_loc.sid_structure.locator_block_length = 48
p1d1_loc.sid_structure.locator_node_length = 16
p1d1_loc.sid_structure.function_length = 16
p1d1_loc.sid_structure.argument_length = 0
p1d1_loc.advertise_locator_as_prefix.redistribution_type = "up"
p1d1_loc.advertise_locator_as_prefix.route_origin = "internal"
p1d1_loc.advertise_locator_as_prefix.prefix_attributes.n_flag = True

# End SID: function=0x0001 → fc00:0:1:0:1::
p1d1_end_sid = p1d1_loc.end_sids.add()
p1d1_end_sid.function = "1"
p1d1_end_sid.endpoint_behavior = "end"
p1d1_end_sid.c_flag = False

# Adj SID: function=0xe001 → fc00:0:1:0:e001::
p1d1_adj_sid = p1d1_isis_intf.srv6_adjacency_sids.add()
p1d1_adj_sid.locator = "custom_locator_reference"
p1d1_adj_sid.custom_locator_reference = "loc1"
p1d1_adj_sid.function = "e001"
p1d1_adj_sid.endpoint_behavior = "end_x"

# Verify ISIS metrics
req = api.metrics_request()
req.isis.router_names = []
req.isis.column_names = ["l2_sessions_up"]
results = api.get_metrics(req)
assert len(results.isis_metrics) == 2
for metric in results.isis_metrics:
    assert metric.l2_sessions_up >= 1
```

### 6.5 Test Result

`1 passed in 66.25s` — ISIS L2 sessions come up on both routers confirming SRv6 capability, locator, End SID, and Adj SID configuration is correctly translated to IxNetwork.

---

## 7. My Local SID Lifecycle Actions

### 7.1 Overview

The My Local SID lifecycle allows runtime add/modify/delete of SRv6 End SID entries
without a full config push. This maps to RFC 8986 Section 3.3 (MY_LOCAL_SID table)
and Section 4 (Instantiation, Re-instantiation, Un-instantiation).

The snappi API exposes this via `ControlAction → protocol → isis → srv6 → my_local_sid`.

### 7.2 Snappi API Model

```
ControlAction
  └── protocol (ActionProtocol)
        └── isis (ActionProtocolIsis)
              └── srv6 (ActionProtocolIsisSrv6)
                    └── my_local_sid (ActionProtocolIsisSrv6MyLocalSid)
                          ├── router_names         # target ISIS routers
                          ├── choice: "add" | "modify" | "delete"
                          ├── add
                          │     └── entries (list of Entry)
                          ├── modify
                          │     └── entries (list of Entry)
                          └── delete
                                └── sid_refs (list of SidRef)
```

#### Entry fields

| Field | Type | Required | Description |
|---|---|---|---|
| `sid_prefix` | str (IPv6) | Yes | Full SID IPv6 address |
| `prefix_length` | int | No (default 48) | Prefix length in bits |
| `behavior` | enum | No (default `u_n`) | SRv6 endpoint behavior |
| `vrf_name` | str | No | VRF for decap behaviors |
| `next_hop` | str | No | Next-hop for cross-connect behaviors |

#### Behavior enum

| Value | IANA Code | Description |
|---|---|---|
| `u_n` | 1 | Micro-SID node (uN) |
| `u_dt4` | 18 | uDT4 (decap IPv4 table lookup) |
| `u_dt6` | 17 | uDT6 (decap IPv6 table lookup) |
| `u_dt46` | 19 | uDT46 (decap dual-stack) |
| `u_dx4` | 16 | uDX4 (cross-connect IPv4) |
| `u_dx6` | 15 | uDX6 (cross-connect IPv6) |
| `end` | 1 | End (full-SID) |
| `end_dt4` | 18 | End.DT4 |
| `end_dt6` | 17 | End.DT6 |
| `end_dt46` | 19 | End.DT46 |

#### SidRef fields (for delete)

| Field | Type | Required | Description |
|---|---|---|---|
| `sid_prefix` | str (IPv6) | Yes | SID to delete |
| `prefix_length` | int | Yes | Prefix length |

### 7.3 IxNetwork Mapping

| Operation | IxNetwork Action |
|---|---|
| Add | Increase `SidCount` on `isisSRv6LocatorEntryList`, populate new entries in `isisSRv6EndSIDList` with `Sid`, `EndPointFunction`, `CFlag` multivalues |
| Modify | Update `EndPointFunction` multivalue on matching `Sid` entry in `isisSRv6EndSIDList` |
| Delete | Decrease `SidCount`, filter out matching entries from `Sid`/`EndPointFunction`/`CFlag` value lists |
| All | Call `Globals.Topology.ApplyOnTheFly()` to trigger ISIS LSP re-advertisement |

### 7.4 Implementation

| File | Change |
|---|---|
| `snappi_ixnetwork/device/isis_srv6_actions.py` | New file: `IsisSRv6Actions` class with `handle_my_local_sid`, `_add_my_local_sids`, `_modify_my_local_sids`, `_delete_my_local_sids` |
| `snappi_ixnetwork/snappi_api.py` | Added `isis` handling in `set_control_action` with SRv6 My Local SID dispatch |

### 7.5 Test Code

```python
# ADD - Program a new uN SID on the router
action = api.control_action()
action.protocol.isis.choice = "srv6"
my_local_sid = action.protocol.isis.srv6.my_local_sid
my_local_sid.router_names = ["p1d1_isis"]
my_local_sid.choice = "add"
my_local_sid.add.entries.add(
    sid_prefix="fc00:0:1:0:2::",
    prefix_length=64,
    behavior="u_n",
)
api.set_control_action(action)

# MODIFY - Change behavior of existing SID
action2 = api.control_action()
action2.protocol.isis.choice = "srv6"
my_local_sid2 = action2.protocol.isis.srv6.my_local_sid
my_local_sid2.router_names = ["p1d1_isis"]
my_local_sid2.choice = "modify"
my_local_sid2.modify.entries.add(
    sid_prefix="fc00:0:1:0:2::",
    prefix_length=64,
    behavior="end_dt6",
)
api.set_control_action(action2)

# DELETE - Remove the SID
action3 = api.control_action()
action3.protocol.isis.choice = "srv6"
my_local_sid3 = action3.protocol.isis.srv6.my_local_sid
my_local_sid3.router_names = ["p1d1_isis"]
my_local_sid3.choice = "delete"
my_local_sid3.delete.sid_refs.add(
    sid_prefix="fc00:0:1:0:2::",
    prefix_length=64,
)
api.set_control_action(action3)
```

### 7.6 Model Changes (P0 Update)

The following changes from commit `f6d8994` are reflected in this implementation:

1. **EndSid `locator` field removed** — End SIDs now always inherit the parent
   `IsisSRv6.Locator` prefix. No `locator`/`custom_locator_reference` choice exists.
   The implementation already used the parent locator directly.

2. **`c_flag` on EndSid updated** — Now signals uSID (Micro-SID) per RFC 9800.
   When set, the End SID can be packed into a 128-bit uSID container by the headend.

3. **`c_flag` on Node Capability** — Prerequisite flag for advertising uSID support.
   Must be set before individual End/Adj SIDs are marked as uSIDs.

4. **My Local SID lifecycle** — New `Action.Protocol.Isis.Srv6.MyLocalSid` with
   add/modify/delete operations for runtime SID table management (RFC 8986 Section 4).

5. **Flow extensions (informational)** — `routing_type`, `srv6_encap_mode`, and
   `usid_container` added to `Flow.Ipv6SegmentRouting` for traffic generation with
   uSID containers (RFC 9800 Section 4). These are handled by the traffic item layer.
