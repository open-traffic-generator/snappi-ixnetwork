# ISIS-SRv6 Implementation Design Document

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Snappi API Model](#snappi-api-model)
4. [IxNetwork RestPy to Snappi API Mapping](#ixnetwork-restpy-to-snappi-api-mapping)
5. [Implementation Plan](#implementation-plan)
6. [Back-to-Back SRv6 Test Case](#back-to-back-srv6-test-case)

---

## 1. Overview

### 1.1 What is ISIS-SRv6?

Segment Routing over IPv6 (SRv6) using ISIS (IS-IS) as the control plane is defined in:
- **RFC 8986** — SRv6 Network Programming
- **RFC 9252** — BGP Overlay Services Based on Segment Routing over IPv6 (SRv6)
- **draft-ietf-lsr-isis-srv6-extensions** — IS-IS Extensions to Support Segment Routing over IPv6

In ISIS-SRv6, the router advertises:
- **SRv6 Capability** — signals that the router supports SRv6 (advertised in TLV 242, sub-TLV 25)
- **SRv6 Locator** — an IPv6 prefix that acts as a routing locator for the node (advertised in TLV 27)
- **SRv6 End SIDs** — SRv6 Segment Identifiers tied to a locator with specific endpoint behaviors (e.g., End, End.X, End.T, End.DT6)
- **SRv6 Adjacency SIDs** — SRv6 SIDs bound to a specific adjacency (advertised in IS Reachability TLV 22 / TLV 222 sub-TLVs)

### 1.2 SRv6 SID Structure

An SRv6 SID is a 128-bit IPv6 address structured as:

```
| Locator Block | Locator Node | Function | Argument |
|<-- B bits -->|<-- N bits -->|<-- F bits -->|<-- A bits -->|
```

Typical sizes: B=48, N=16, F=16, A=0 (totaling 80 bits for the SID, leaving 48 bits for argument/zero)

### 1.3 Endpoint Behaviors (End-Point Functions)

| Behavior | Description |
|----------|-------------|
| `End` (0x0001) | Basic endpoint, no PSP/USP |
| `End.X` (0x0005) | Endpoint with cross-connect to adjacency |
| `End.T` (0x0002) | Endpoint with specific IPv6 table lookup |
| `End.DX6` (0x000E) | Endpoint with decapsulation and IPv6 cross-connect |
| `End.DX4` (0x000D) | Endpoint with decapsulation and IPv4 cross-connect |
| `End.DT6` (0x0012) | Endpoint with decapsulation and specific IPv6 table lookup |
| `End.DT4` (0x0013) | Endpoint with decapsulation and specific IPv4 table lookup |
| `End.DT46` (0x0014) | Endpoint with decapsulation and IPv4/IPv6 table lookup |

---

## 2. Architecture

### 2.1 Object Hierarchy in IxNetwork

```
Topology
  └── DeviceGroup
        ├── bridgeData          ← systemId
        ├── isisL3Router        ← router-level config
        │     ├── SRv6 Capability flags (enableSR, sRv6NodePrefix, locatorCount, ...)
        │     └── isisSRv6LocatorEntryList   ← locator config (count = locatorCount)
        │           └── isisSRv6EndSIDList    ← End SIDs per locator (count = sidCount)
        └── ethernet
              └── isisL3         ← interface-level config
                    └── isisSRv6AdjSIDList   ← Adj SIDs per interface
```

### 2.2 Snappi Object Model (Proposed)

```
Device
  └── isis (IsisRouter)
        ├── name
        ├── system_id
        ├── srv6_capability (IsisRouterSRv6Capability)  ← NEW
        │     ├── enable_sr
        │     ├── node_prefix               # sRv6NodePrefix (IPv6 loopback/router-id)
        │     ├── node_prefix_length        # sRv6NodePrefixLength
        │     ├── d_bit                     # dBit
        │     ├── s_bit                     # sBitForSRv6Cap
        │     ├── c_flag                    # cFlagOfSRv6Cap
        │     ├── d_bit_for_srv6_cap        # dBitForSRv6Cap
        │     ├── e_flag_of_srv6_cap_tlv    # eFlagOfSRv6CapTlv
        │     ├── o_flag_of_srv6_cap_tlv    # oFlagOfSRv6CapTlv
        │     └── locator_count             # locatorCount
        ├── srv6_locators (list of IsisRouterSRv6Locator)  ← NEW
        │     ├── name
        │     ├── locator_name              # locatorName
        │     ├── locator                   # locator (IPv6 prefix)
        │     ├── prefix_length             # prefixLength
        │     ├── locator_size              # locatorSize
        │     ├── metric                    # metric
        │     ├── algorithm                 # algorithm
        │     ├── redistribution            # redistribution (up/down)
        │     ├── route_origin              # routeOrigin (internal/external)
        │     ├── d_bit                     # dBit
        │     ├── advertise_locator_as_prefix # advertiseLocatorAsPrefix
        │     ├── n_flag                    # enableNFlag
        │     ├── r_flag                    # enableRFlag
        │     ├── x_flag                    # enableXFlag
        │     ├── mt_id                     # mtId
        │     ├── sid_count                 # sidCount
        │     └── end_sids (list of IsisRouterSRv6EndSid)
        │           ├── name
        │           ├── sid_name            # sidName
        │           ├── sid                 # sid (IPv6 SID address)
        │           ├── end_point_function  # endPointFunction
        │           ├── flags               # flags
        │           ├── c_flag              # cFlag
        │           ├── function_length     # functionLength
        │           ├── argument_length     # argumentLength
        │           ├── locator_block_length # locatorBlockLength
        │           ├── locator_node_length  # locatorNodeLength
        │           ├── include_srv6_sid_structure_sub_sub_tlv # includeSRv6SIDStructureSubSubTlv
        │           └── advertise_custom_sub_tlv # advertiseCustomSubTLV
        └── interfaces (list)
              └── IsisInterface
                    ├── eth_name
                    ├── ...existing fields...
                    └── srv6_adj_sids (list of IsisInterfaceSRv6AdjSid)  ← NEW
                          ├── name
                          ├── ipv6_adj_sid          # ipv6AdjSid
                          ├── end_point_function     # endPointFunction
                          ├── algorithm             # algorithm
                          ├── weight                # weight
                          ├── b_flag                # bFlag
                          ├── s_flag                # sFlag
                          ├── p_flag                # pFlag
                          ├── c_flag                # cFlag
                          ├── function_length       # functionLength
                          ├── argument_length       # argumentLength
                          ├── locator_block_length  # locatorBlockLength
                          ├── locator_node_length   # locatorNodeLength
                          └── include_srv6_sid_structure_sub_sub_tlv
```

---

## 3. Snappi API Model

### 3.1 New Snappi Classes Required

The following new classes need to be added to the snappi OpenAPI/OTG schema and auto-generated Python client:

#### `IsisRouterSRv6Capability`
Controls SRv6 capability advertisement in the IS-IS Router Capability TLV (TLV 242).

| Snappi Field | Type | Default | Description |
|---|---|---|---|
| `enable_sr` | bool | True | Enable SR for IPv6 |
| `node_prefix` | str | `"fc00::1"` | SRv6 node prefix (IPv6 loopback) |
| `node_prefix_length` | int | 128 | SRv6 node prefix length |
| `c_flag` | bool | False | C-Flag in SRv6 Capability |
| `d_bit_for_srv6_cap` | bool | False | D-Bit in SRv6 Capability |
| `e_flag_of_srv6_cap_tlv` | bool | False | E-Flag of SRv6 Capability TLV |
| `o_flag_of_srv6_cap_tlv` | bool | False | O-Flag of SRv6 Capability TLV |
| `locator_count` | int | 1 | Number of SRv6 locators |

#### `IsisRouterSRv6Locator`
Represents one SRv6 locator advertised in IS-IS TLV 27.

| Snappi Field | Type | Default | Description |
|---|---|---|---|
| `name` | str | required | Name of this locator object |
| `locator_name` | str | `"loc1"` | Locator name string |
| `locator` | str | `"fc00:0:1::"` | IPv6 locator prefix |
| `prefix_length` | int | 48 | Locator prefix length (bits) |
| `locator_size` | int | 64 | Locator size (bits in SID) |
| `metric` | int | 0 | Locator metric |
| `algorithm` | int | 0 | Algorithm (0=SPF, 128+=Flex-Algo) |
| `redistribution` | str | `"up"` | `up` or `down` |
| `route_origin` | str | `"internal"` | `internal` or `external` |
| `d_bit` | bool | False | D-Bit in locator TLV |
| `advertise_locator_as_prefix` | bool | True | Advertise locator as IPv6 prefix |
| `n_flag` | bool | True | N-Flag (node prefix flag) |
| `r_flag` | bool | False | R-Flag (redistribution flag) |
| `x_flag` | bool | False | X-Flag (external flag) |
| `mt_id` | int | 0 | Multi-Topology ID |
| `sid_count` | int | 1 | Number of End SIDs under this locator |
| `end_sids` | list[IsisRouterSRv6EndSid] | [] | List of End SIDs |

#### `IsisRouterSRv6EndSid`
Represents one SRv6 End SID under a locator.

| Snappi Field | Type | Default | Description |
|---|---|---|---|
| `name` | str | required | Name of this End SID object |
| `sid_name` | str | `"end_sid_1"` | SID name string |
| `sid` | str | `"fc00:0:1::1"` | 128-bit IPv6 SID value |
| `end_point_function` | str | `"end"` | Endpoint behavior |
| `flags` | int | 0 | Flags byte |
| `c_flag` | bool | False | C-Flag (compression) |
| `function_length` | int | 16 | Function field length (bits) |
| `argument_length` | int | 0 | Argument field length (bits) |
| `locator_block_length` | int | 48 | Locator block length (bits) |
| `locator_node_length` | int | 16 | Locator node length (bits) |
| `include_srv6_sid_structure_sub_sub_tlv` | bool | False | Include SID Structure sub-sub-TLV |
| `advertise_custom_sub_tlv` | bool | False | Advertise custom sub-TLV |

`end_point_function` enum values:

| Snappi value | IxNetwork value | RFC 8986 behavior |
|---|---|---|
| `"end"` | `"End"` | Basic endpoint |
| `"end_with_psp"` | `"End (PSP)"` | End with PSP |
| `"end_with_usp"` | `"End (USP)"` | End with USP |
| `"end_with_psp_usp"` | `"End (PSP, USP)"` | End with PSP and USP |
| `"end_x"` | `"End.X"` | End with adjacency cross-connect |
| `"end_t"` | `"End.T"` | End with table lookup |
| `"end_dx6"` | `"End.DX6"` | End with DX6 |
| `"end_dx4"` | `"End.DX4"` | End with DX4 |
| `"end_dt6"` | `"End.DT6"` | End with DT6 |
| `"end_dt4"` | `"End.DT4"` | End with DT4 |
| `"end_dt46"` | `"End.DT46"` | End with DT46 |

#### `IsisInterfaceSRv6AdjSid`
Represents one SRv6 adjacency SID on an ISIS interface.

| Snappi Field | Type | Default | Description |
|---|---|---|---|
| `name` | str | required | Name of this Adj SID object |
| `ipv6_adj_sid` | str | `"fc00:0:1:e001::"` | IPv6 adjacency SID |
| `end_point_function` | str | `"end_x"` | Endpoint function (typically End.X) |
| `algorithm` | int | 0 | Algorithm |
| `weight` | int | 0 | Weight |
| `b_flag` | bool | False | B-Flag |
| `s_flag` | bool | False | S-Flag (set/group) |
| `p_flag` | bool | False | P-Flag (persistent) |
| `c_flag` | bool | False | C-Flag (compression) |
| `function_length` | int | 16 | Function length (bits) |
| `argument_length` | int | 0 | Argument length (bits) |
| `locator_block_length` | int | 48 | Locator block length (bits) |
| `locator_node_length` | int | 16 | Locator node length (bits) |
| `include_srv6_sid_structure_sub_sub_tlv` | bool | False | Include SID Structure sub-sub-TLV |

---

## 4. IxNetwork RestPy to Snappi API Mapping

### 4.1 ISIS L3 Router — SRv6 Capability Fields

Maps to **`isisL3Router`** in IxNetwork.

| Snappi API Field | IxNetwork Attribute | IxNetwork JSON key | Notes |
|---|---|---|---|
| `isis.srv6_capability.enable_sr` | `EnableSR` | `enableSR` | Bool multivalue |
| `isis.srv6_capability.node_prefix` | `SRv6NodePrefix` | `sRv6NodePrefix` | IPv6 multivalue |
| `isis.srv6_capability.node_prefix_length` | `SRv6NodePrefixLength` | `sRv6NodePrefixLength` | Int multivalue |
| `isis.srv6_capability.c_flag` | `CFlagOfSRv6Cap` | `cFlagOfSRv6Cap` | Bool multivalue |
| `isis.srv6_capability.d_bit_for_srv6_cap` | `DBitForSRv6Cap` | `dBitForSRv6Cap` | Bool multivalue |
| `isis.srv6_capability.e_flag_of_srv6_cap_tlv` | `EFlagOfSRv6CapTlv` | `eFlagOfSRv6CapTlv` | Bool multivalue |
| `isis.srv6_capability.o_flag_of_srv6_cap_tlv` | `OFlagOfSRv6CapTlv` | `oFlagOfSRv6CapTlv` | Bool multivalue |
| `isis.srv6_capability.locator_count` | `LocatorCount` | `locatorCount` | Int scalar — controls list size |

### 4.2 ISIS SRv6 Locator Entry List

Maps to **`isisSRv6LocatorEntryList`** child of `isisL3Router`.

| Snappi API Field | IxNetwork Attribute | IxNetwork JSON key | Notes |
|---|---|---|---|
| `locator.locator_name` | `LocatorName` | `locatorName` | String list |
| `locator.locator` | `Locator` | `locator` | IPv6 prefix multivalue |
| `locator.prefix_length` | `PrefixLength` | `prefixLength` | Int multivalue |
| `locator.locator_size` | `LocatorSize` | `locatorSize` | Int multivalue |
| `locator.metric` | `Metric` | `metric` | Int multivalue |
| `locator.algorithm` | `Algorithm` | `algorithm` | Int multivalue |
| `locator.redistribution` | `Redistribution` | `redistribution` | Enum multivalue (`up`/`down`) |
| `locator.route_origin` | `RouteOrigin` | `routeOrigin` | Enum multivalue (`internal`/`external`) |
| `locator.d_bit` | `DBit` | `dBit` | Bool multivalue |
| `locator.advertise_locator_as_prefix` | `AdvertiseLocatorAsPrefix` | `advertiseLocatorAsPrefix` | Bool multivalue |
| `locator.n_flag` | `EnableNFlag` | `enableNFlag` | Bool multivalue |
| `locator.r_flag` | `EnableRFlag` | `enableRFlag` | Bool multivalue |
| `locator.x_flag` | `EnableXFlag` | `enableXFlag` | Bool multivalue |
| `locator.mt_id` | `MtId` | `mtId` | Int multivalue |
| `locator.sid_count` | `SidCount` | `sidCount` | Int scalar — controls End SID list size |

### 4.3 ISIS SRv6 End SID List

Maps to **`isisSRv6EndSIDList`** child of `isisSRv6LocatorEntryList`.

| Snappi API Field | IxNetwork Attribute | IxNetwork JSON key | Notes |
|---|---|---|---|
| `end_sid.sid_name` | `SidName` | `sidName` | String multivalue |
| `end_sid.sid` | `Sid` | `sid` | IPv6 multivalue |
| `end_sid.end_point_function` | `EndPointFunction` | `endPointFunction` | Enum multivalue |
| `end_sid.flags` | `Flags` | `flags` | Int multivalue |
| `end_sid.c_flag` | `CFlag` | `cFlag` | Bool multivalue |
| `end_sid.function_length` | `FunctionLength` | `functionLength` | Int multivalue |
| `end_sid.argument_length` | `ArgumentLength` | `argumentLength` | Int multivalue |
| `end_sid.locator_block_length` | `LocatorBlockLength` | `locatorBlockLength` | Int multivalue |
| `end_sid.locator_node_length` | `LocatorNodeLength` | `locatorNodeLength` | Int multivalue |
| `end_sid.include_srv6_sid_structure_sub_sub_tlv` | `IncludeSRv6SIDStructureSubSubTlv` | `includeSRv6SIDStructureSubSubTlv` | Bool multivalue |
| `end_sid.advertise_custom_sub_tlv` | `AdvertiseCustomSubTLV` | `advertiseCustomSubTLV` | Bool multivalue |

### 4.4 ISIS L3 Interface — SRv6 Adjacency SID

Maps to **`isisSRv6AdjSIDList`** child of `isisL3` (interface).  
The interface `isisL3` must also have `EnableIPv6SID` set to enable SRv6 Adj SID advertisement.

| Snappi API Field | IxNetwork Attribute | IxNetwork JSON key | Notes |
|---|---|---|---|
| `intf.enable_ipv6_sid` | `EnableIPv6SID` | `enableIPv6SID` | Bool multivalue — gates adj SID |
| `adj_sid.ipv6_adj_sid` | `Ipv6AdjSid` | `ipv6AdjSid` | IPv6 multivalue |
| `adj_sid.end_point_function` | `EndPointFunction` | `endPointFunction` | Enum multivalue |
| `adj_sid.algorithm` | `Algorithm` | `algorithm` | Int multivalue |
| `adj_sid.weight` | `Weight` | `weight` | Int multivalue |
| `adj_sid.b_flag` | `BFlag` | `bFlag` | Bool multivalue |
| `adj_sid.s_flag` | `SFlag` | `sFlag` | Bool multivalue |
| `adj_sid.p_flag` | `PFlag` | `pFlag` | Bool multivalue |
| `adj_sid.c_flag` | `CFlag` | `cFlag` | Bool multivalue |
| `adj_sid.function_length` | `FunctionLength` | `functionLength` | Int multivalue |
| `adj_sid.argument_length` | `ArgumentLength` | `argumentLength` | Int multivalue |
| `adj_sid.locator_block_length` | `LocatorBlockLength` | `locatorBlockLength` | Int multivalue |
| `adj_sid.locator_node_length` | `LocatorNodeLength` | `locatorNodeLength` | Int multivalue |
| `adj_sid.include_srv6_sid_structure_sub_sub_tlv` | `IncludeSRv6SIDStructureSubSubTlv` | `includeSRv6SIDStructureSubSubTlv` | Bool multivalue |

### 4.5 Endpoint Function Enum Map

| Snappi value | IxNetwork value |
|---|---|
| `"end"` | `"End"` |
| `"end_with_psp"` | `"End (PSP)"` |
| `"end_with_usp"` | `"End (USP)"` |
| `"end_with_psp_usp"` | `"End (PSP, USP)"` |
| `"end_with_usd"` | `"End (USD)"` |
| `"end_x"` | `"End.X"` |
| `"end_x_with_psp"` | `"End.X (PSP)"` |
| `"end_x_with_usp"` | `"End.X (USP)"` |
| `"end_t"` | `"End.T"` |
| `"end_dx6"` | `"End.DX6"` |
| `"end_dx4"` | `"End.DX4"` |
| `"end_dt6"` | `"End.DT6"` |
| `"end_dt4"` | `"End.DT4"` |
| `"end_dt46"` | `"End.DT46"` |
| `"end_b6_encaps"` | `"End.B6.Encaps"` |
| `"end_bm"` | `"End.BM"` |

### 4.6 Redistribution Enum Map

| Snappi value | IxNetwork value |
|---|---|
| `"up"` | `"up"` |
| `"down"` | `"down"` |

### 4.7 Route Origin Enum Map

| Snappi value | IxNetwork value |
|---|---|
| `"internal"` | `"internal"` |
| `"external"` | `"external"` |

---

## 5. Implementation Plan

### 5.1 Files to Modify

| File | Change |
|---|---|
| `snappi_ixnetwork/device/isis.py` | Add SRv6 capability, locator, End SID, Adj SID configuration methods |
| `snappi_ixnetwork/device/ngpf.py` | Add `IsisRouterSRv6Capability`, locator, End SID, Adj SID to device encap map if needed |

### 5.2 New Attribute Maps (to add in `isis.py`)

```python
_SRV6_CAPABILITY = {
    "enable_sr": "enableSR",
    "node_prefix": "sRv6NodePrefix",
    "node_prefix_length": "sRv6NodePrefixLength",
    "c_flag": "cFlagOfSRv6Cap",
    "d_bit_for_srv6_cap": "dBitForSRv6Cap",
    "e_flag_of_srv6_cap_tlv": "eFlagOfSRv6CapTlv",
    "o_flag_of_srv6_cap_tlv": "oFlagOfSRv6CapTlv",
}

_SRV6_LOCATOR = {
    "locator": "locator",
    "prefix_length": "prefixLength",
    "locator_size": "locatorSize",
    "metric": "metric",
    "algorithm": "algorithm",
    "d_bit": "dBit",
    "advertise_locator_as_prefix": "advertiseLocatorAsPrefix",
    "n_flag": "enableNFlag",
    "r_flag": "enableRFlag",
    "x_flag": "enableXFlag",
    "mt_id": "mtId",
}

_SRV6_LOCATOR_REDISTRIBUTION = {
    "redistribution": {
        "ixn_attr": "redistribution",
        "enum_map": {"up": "up", "down": "down"},
    }
}

_SRV6_LOCATOR_ROUTE_ORIGIN = {
    "route_origin": {
        "ixn_attr": "routeOrigin",
        "enum_map": {"internal": "internal", "external": "external"},
    }
}

_SRV6_END_SID = {
    "sid": "sid",
    "flags": "flags",
    "c_flag": "cFlag",
    "function_length": "functionLength",
    "argument_length": "argumentLength",
    "locator_block_length": "locatorBlockLength",
    "locator_node_length": "locatorNodeLength",
    "include_srv6_sid_structure_sub_sub_tlv": "includeSRv6SIDStructureSubSubTlv",
    "advertise_custom_sub_tlv": "advertiseCustomSubTLV",
}

_SRV6_END_POINT_FUNCTION = {
    "end_point_function": {
        "ixn_attr": "endPointFunction",
        "enum_map": {
            "end":               "End",
            "end_with_psp":      "End (PSP)",
            "end_with_usp":      "End (USP)",
            "end_with_psp_usp":  "End (PSP, USP)",
            "end_with_usd":      "End (USD)",
            "end_x":             "End.X",
            "end_x_with_psp":    "End.X (PSP)",
            "end_x_with_usp":    "End.X (USP)",
            "end_t":             "End.T",
            "end_dx6":           "End.DX6",
            "end_dx4":           "End.DX4",
            "end_dt6":           "End.DT6",
            "end_dt4":           "End.DT4",
            "end_dt46":          "End.DT46",
            "end_b6_encaps":     "End.B6.Encaps",
            "end_bm":            "End.BM",
        },
    }
}

_SRV6_ADJ_SID = {
    "ipv6_adj_sid": "ipv6AdjSid",
    "algorithm": "algorithm",
    "weight": "weight",
    "b_flag": "bFlag",
    "s_flag": "sFlag",
    "p_flag": "pFlag",
    "c_flag": "cFlag",
    "function_length": "functionLength",
    "argument_length": "argumentLength",
    "locator_block_length": "locatorBlockLength",
    "locator_node_length": "locatorNodeLength",
    "include_srv6_sid_structure_sub_sub_tlv": "includeSRv6SIDStructureSubSubTlv",
}
```

### 5.3 New Methods in `Isis` class

```python
def _configure_srv6_capability(self, isis, ixn_isis_router):
    """Configure SRv6 capability on the ISIS router (isisL3Router)."""
    srv6_cap = isis.get("srv6_capability")
    if srv6_cap is None:
        return
    locator_count = srv6_cap.get("locator_count") or 1
    ixn_isis_router["enableSR"] = self.multivalue(srv6_cap.get("enable_sr", True))
    ixn_isis_router["locatorCount"] = locator_count
    self.configure_multivalues(srv6_cap, ixn_isis_router, Isis._SRV6_CAPABILITY)


def _configure_srv6_locators(self, isis, ixn_isis_router):
    """Configure SRv6 locators (isisSRv6LocatorEntryList) under isisL3Router."""
    srv6_locators = isis.get("srv6_locators")
    if srv6_locators is None:
        return
    ixn_locator_list = self.create_node(ixn_isis_router, "isisSRv6LocatorEntryList")
    for locator in srv6_locators:
        ixn_locator = self.add_element(ixn_locator_list, locator.get("locator_name"))
        sid_count = locator.get("sid_count") or 1
        ixn_locator["sidCount"] = sid_count
        self.configure_multivalues(locator, ixn_locator, Isis._SRV6_LOCATOR)
        self.configure_multivalues(locator, ixn_locator, Isis._SRV6_LOCATOR_REDISTRIBUTION)
        self.configure_multivalues(locator, ixn_locator, Isis._SRV6_LOCATOR_ROUTE_ORIGIN)
        end_sids = locator.get("end_sids")
        if end_sids is not None:
            self._configure_srv6_end_sids(end_sids, ixn_locator)


def _configure_srv6_end_sids(self, end_sids, ixn_locator):
    """Configure SRv6 End SIDs (isisSRv6EndSIDList) under a locator entry."""
    ixn_end_sid_list = self.create_node(ixn_locator, "isisSRv6EndSIDList")
    for end_sid in end_sids:
        ixn_end_sid = self.add_element(ixn_end_sid_list, end_sid.get("sid_name"))
        self.configure_multivalues(end_sid, ixn_end_sid, Isis._SRV6_END_SID)
        self.configure_multivalues(end_sid, ixn_end_sid, Isis._SRV6_END_POINT_FUNCTION)


def _configure_srv6_adj_sids(self, interface, ixn_isis):
    """Configure SRv6 Adjacency SIDs (isisSRv6AdjSIDList) under isisL3 interface."""
    srv6_adj_sids = interface.get("srv6_adj_sids")
    if srv6_adj_sids is None:
        return
    # Enable SRv6 on the interface
    ixn_isis["enableIPv6SID"] = self.multivalue(True)
    ixn_adj_sid_list = self.create_node(ixn_isis, "isisSRv6AdjSIDList")
    for adj_sid in srv6_adj_sids:
        ixn_adj_sid = self.add_element(ixn_adj_sid_list)
        self.configure_multivalues(adj_sid, ixn_adj_sid, Isis._SRV6_ADJ_SID)
        self.configure_multivalues(adj_sid, ixn_adj_sid, Isis._SRV6_END_POINT_FUNCTION)
```

### 5.4 Integration Points

In `_config_isis_interface` (existing method), add a call to `_configure_srv6_adj_sids` at the end:

```python
# In _config_isis_interface, after srlg_values block:
self._configure_srv6_adj_sids(interface, ixn_isis)
```

In `_config_isis_router` (existing method), add calls after existing configurations:

```python
# In _config_isis_router:
self._configure_srv6_capability(otg_isis_router, ixn_isis_router)
self._configure_srv6_locators(otg_isis_router, ixn_isis_router)
```

---

## 6. Back-to-Back SRv6 Test Case

The following test case validates a back-to-back ISIS-SRv6 session between two emulated devices, advertises locators with End SIDs, and verifies ISIS adjacency comes up.

### 6.1 Topology

```
+------------------+              +------------------+
|   Port 1 (P1)    |              |   Port 2 (P2)    |
|                  |              |                  |
|  Device: p1d1    +--------------+  Device: p2d1    |
|  MAC: 00:00:00:01:01:01        |  MAC: 00:00:00:02:02:02 |
|  IPv6: 2001:db8::1/64          |  IPv6: 2001:db8::2/64   |
|                  |   b2b link   |                  |
|  ISIS Router     |              |  ISIS Router     |
|  SystemID:       |              |  SystemID:       |
|  670000000001    |              |  680000000001    |
|                  |              |                  |
|  SRv6 Node Pfx:  |              |  SRv6 Node Pfx:  |
|  fc00::1/128     |              |  fc00::2/128     |
|                  |              |                  |
|  Locator:        |              |  Locator:        |
|  fc00:0:1::/48   |              |  fc00:0:2::/48   |
|  End SID:        |              |  End SID:        |
|  fc00:0:1::1     |              |  fc00:0:2::1     |
|  (End function)  |              |  (End function)  |
+------------------+              +------------------+
```

### 6.2 Test Code

```python
# tests/isis/test_isis_srv6.py
import pytest
import time


def test_isis_srv6_b2b(api, b2b_raw_config, utils):
    """
    Back-to-back ISIS-SRv6 test:
    - Configure two devices with ISIS over IPv6 link
    - Enable SRv6 capability on both routers
    - Advertise one SRv6 locator per router with one End SID
    - Configure SRv6 Adjacency SIDs on each interface
    - Start protocols and verify ISIS sessions come up
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    # ------------------------------------------------------------------ ports
    p1, p2 = b2b_raw_config.ports

    # ---------------------------------------------------------------- devices
    p1d1, p2d1 = b2b_raw_config.devices.device(name="p1d1").device(name="p2d1")

    # --------------------------------------------------------------- ethernet
    p1d1_eth = p1d1.ethernets.add()
    p1d1_eth.connection.port_name = p1.name
    p1d1_eth.name = "p1d1_eth"
    p1d1_eth.mac = "00:00:00:01:01:01"
    p1d1_eth.mtu = 1500

    p2d1_eth = p2d1.ethernets.add()
    p2d1_eth.connection.port_name = p2.name
    p2d1_eth.name = "p2d1_eth"
    p2d1_eth.mac = "00:00:00:02:02:02"
    p2d1_eth.mtu = 1500

    # --------------------------------------------------------------- IPv6 addresses
    p1d1_ipv6 = p1d1_eth.ipv6_addresses.add()
    p1d1_ipv6.name = "p1d1_ipv6"
    p1d1_ipv6.address = "2001:db8::1"
    p1d1_ipv6.gateway = "2001:db8::2"
    p1d1_ipv6.prefix = 64

    p2d1_ipv6 = p2d1_eth.ipv6_addresses.add()
    p2d1_ipv6.name = "p2d1_ipv6"
    p2d1_ipv6.address = "2001:db8::2"
    p2d1_ipv6.gateway = "2001:db8::1"
    p2d1_ipv6.prefix = 64

    # ======================================================= PORT-1 ISIS Router
    p1d1_isis = p1d1.isis
    p1d1_isis.name = "p1d1_isis"
    p1d1_isis.system_id = "670000000001"

    # Basic router settings
    p1d1_isis.basic.hostname = "ixia-c-port1"
    p1d1_isis.basic.enable_wide_metric = True
    p1d1_isis.basic.learned_lsp_filter = False

    # Advanced router settings
    p1d1_isis.advanced.area_addresses = ["490001"]
    p1d1_isis.advanced.csnp_interval = 10000
    p1d1_isis.advanced.enable_hello_padding = True
    p1d1_isis.advanced.lsp_lifetime = 1200
    p1d1_isis.advanced.lsp_refresh_rate = 900

    # SRv6 Capability (NEW)
    p1d1_isis.srv6_capability.enable_sr = True
    p1d1_isis.srv6_capability.node_prefix = "fc00::1"
    p1d1_isis.srv6_capability.node_prefix_length = 128
    p1d1_isis.srv6_capability.locator_count = 1
    p1d1_isis.srv6_capability.c_flag = False
    p1d1_isis.srv6_capability.d_bit_for_srv6_cap = False

    # SRv6 Locator (NEW)
    p1d1_isis_loc = p1d1_isis.srv6_locators.add()
    p1d1_isis_loc.name = "p1d1_isis_loc1"
    p1d1_isis_loc.locator_name = "loc1"
    p1d1_isis_loc.locator = "fc00:0:1::"
    p1d1_isis_loc.prefix_length = 48
    p1d1_isis_loc.locator_size = 64
    p1d1_isis_loc.metric = 0
    p1d1_isis_loc.algorithm = 0
    p1d1_isis_loc.redistribution = "up"
    p1d1_isis_loc.route_origin = "internal"
    p1d1_isis_loc.advertise_locator_as_prefix = True
    p1d1_isis_loc.n_flag = True
    p1d1_isis_loc.sid_count = 1

    # SRv6 End SID under Locator (NEW)
    p1d1_isis_end_sid = p1d1_isis_loc.end_sids.add()
    p1d1_isis_end_sid.name = "p1d1_isis_end_sid1"
    p1d1_isis_end_sid.sid_name = "End_SID_P1"
    p1d1_isis_end_sid.sid = "fc00:0:1::1"
    p1d1_isis_end_sid.end_point_function = "end"
    p1d1_isis_end_sid.function_length = 16
    p1d1_isis_end_sid.argument_length = 0
    p1d1_isis_end_sid.locator_block_length = 48
    p1d1_isis_end_sid.locator_node_length = 16
    p1d1_isis_end_sid.include_srv6_sid_structure_sub_sub_tlv = True

    # Port-1 ISIS Interface
    p1d1_isis_intf = p1d1_isis.interfaces.add()
    p1d1_isis_intf.eth_name = p1d1_eth.name
    p1d1_isis_intf.name = "p1d1_isis_intf"
    p1d1_isis_intf.network_type = "point_to_point"
    p1d1_isis_intf.level_type = "level_2"
    p1d1_isis_intf.metric = 10
    p1d1_isis_intf.l2_settings.dead_interval = 30
    p1d1_isis_intf.l2_settings.hello_interval = 10
    p1d1_isis_intf.l2_settings.priority = 0

    # SRv6 Adjacency SID on interface (NEW)
    p1d1_isis_adj_sid = p1d1_isis_intf.srv6_adj_sids.add()
    p1d1_isis_adj_sid.name = "p1d1_isis_adj_sid1"
    p1d1_isis_adj_sid.ipv6_adj_sid = "fc00:0:1:e001::"
    p1d1_isis_adj_sid.end_point_function = "end_x"
    p1d1_isis_adj_sid.algorithm = 0
    p1d1_isis_adj_sid.weight = 0
    p1d1_isis_adj_sid.b_flag = False
    p1d1_isis_adj_sid.s_flag = False
    p1d1_isis_adj_sid.p_flag = False
    p1d1_isis_adj_sid.function_length = 16
    p1d1_isis_adj_sid.locator_block_length = 48
    p1d1_isis_adj_sid.locator_node_length = 16

    # ======================================================= PORT-2 ISIS Router
    p2d1_isis = p2d1.isis
    p2d1_isis.name = "p2d1_isis"
    p2d1_isis.system_id = "680000000001"

    p2d1_isis.basic.hostname = "ixia-c-port2"
    p2d1_isis.basic.enable_wide_metric = True
    p2d1_isis.basic.learned_lsp_filter = False

    p2d1_isis.advanced.area_addresses = ["490001"]
    p2d1_isis.advanced.csnp_interval = 10000
    p2d1_isis.advanced.enable_hello_padding = True
    p2d1_isis.advanced.lsp_lifetime = 1200
    p2d1_isis.advanced.lsp_refresh_rate = 900

    # SRv6 Capability (NEW)
    p2d1_isis.srv6_capability.enable_sr = True
    p2d1_isis.srv6_capability.node_prefix = "fc00::2"
    p2d1_isis.srv6_capability.node_prefix_length = 128
    p2d1_isis.srv6_capability.locator_count = 1
    p2d1_isis.srv6_capability.c_flag = False
    p2d1_isis.srv6_capability.d_bit_for_srv6_cap = False

    # SRv6 Locator (NEW)
    p2d1_isis_loc = p2d1_isis.srv6_locators.add()
    p2d1_isis_loc.name = "p2d1_isis_loc1"
    p2d1_isis_loc.locator_name = "loc1"
    p2d1_isis_loc.locator = "fc00:0:2::"
    p2d1_isis_loc.prefix_length = 48
    p2d1_isis_loc.locator_size = 64
    p2d1_isis_loc.metric = 0
    p2d1_isis_loc.algorithm = 0
    p2d1_isis_loc.redistribution = "up"
    p2d1_isis_loc.route_origin = "internal"
    p2d1_isis_loc.advertise_locator_as_prefix = True
    p2d1_isis_loc.n_flag = True
    p2d1_isis_loc.sid_count = 1

    # SRv6 End SID under Locator (NEW)
    p2d1_isis_end_sid = p2d1_isis_loc.end_sids.add()
    p2d1_isis_end_sid.name = "p2d1_isis_end_sid1"
    p2d1_isis_end_sid.sid_name = "End_SID_P2"
    p2d1_isis_end_sid.sid = "fc00:0:2::1"
    p2d1_isis_end_sid.end_point_function = "end"
    p2d1_isis_end_sid.function_length = 16
    p2d1_isis_end_sid.argument_length = 0
    p2d1_isis_end_sid.locator_block_length = 48
    p2d1_isis_end_sid.locator_node_length = 16
    p2d1_isis_end_sid.include_srv6_sid_structure_sub_sub_tlv = True

    # Port-2 ISIS Interface
    p2d1_isis_intf = p2d1_isis.interfaces.add()
    p2d1_isis_intf.eth_name = p2d1_eth.name
    p2d1_isis_intf.name = "p2d1_isis_intf"
    p2d1_isis_intf.network_type = "point_to_point"
    p2d1_isis_intf.level_type = "level_2"
    p2d1_isis_intf.metric = 10
    p2d1_isis_intf.l2_settings.dead_interval = 30
    p2d1_isis_intf.l2_settings.hello_interval = 10
    p2d1_isis_intf.l2_settings.priority = 0

    # SRv6 Adjacency SID on interface (NEW)
    p2d1_isis_adj_sid = p2d1_isis_intf.srv6_adj_sids.add()
    p2d1_isis_adj_sid.name = "p2d1_isis_adj_sid1"
    p2d1_isis_adj_sid.ipv6_adj_sid = "fc00:0:2:e001::"
    p2d1_isis_adj_sid.end_point_function = "end_x"
    p2d1_isis_adj_sid.algorithm = 0
    p2d1_isis_adj_sid.weight = 0
    p2d1_isis_adj_sid.b_flag = False
    p2d1_isis_adj_sid.s_flag = False
    p2d1_isis_adj_sid.p_flag = False
    p2d1_isis_adj_sid.function_length = 16
    p2d1_isis_adj_sid.locator_block_length = 48
    p2d1_isis_adj_sid.locator_node_length = 16

    # ================================================================ push config
    utils.start_traffic(api, b2b_raw_config)

    # =========================================================== verify protocol
    # Wait for ISIS adjacency to come up
    time.sleep(15)

    # Verify ISIS session states
    isis_metrics = api.get_isis_metrics(
        api.metrics_request().isis
    )
    for metric in isis_metrics.isis_metrics:
        assert metric.l2_sessions_up >= 1, (
            "Expected ISIS L2 session up for %s, got %s"
            % (metric.name, metric.l2_sessions_up)
        )

    # Verify learned SRv6 locators (via learned LSP info)
    # Note: actual learned-info API calls depend on snappi version
    # utils.verify_isis_learned_info(api, ...)

    utils.stop_traffic(api, b2b_raw_config)
```

### 6.3 Expected IxNetwork JSON Payload (excerpt)

The following shows the relevant portion of the IxNetwork JSON config that would be generated by the snappi-ixnetwork translator for Port-1:

```json
{
  "xpath": "/topology[1]/deviceGroup[1]",
  "isisL3Router": [
    {
      "xpath": "/topology[1]/deviceGroup[1]/isisL3Router[1]",
      "name": {"value": "p1d1_isis"},
      "enableSR": {"value": true},
      "sRv6NodePrefix": {"value": "fc00::1"},
      "sRv6NodePrefixLength": {"value": 128},
      "locatorCount": 1,
      "cFlagOfSRv6Cap": {"value": false},
      "dBitForSRv6Cap": {"value": false},
      "enableTE": {"value": false},
      "enableWideMetric": {"value": true},
      "discardLSPs": {"value": false},
      "enableHostName": {"value": true},
      "hostName": {"value": "ixia-c-port1"},
      "isisSRv6LocatorEntryList": [
        {
          "xpath": "/topology[1]/deviceGroup[1]/isisL3Router[1]/isisSRv6LocatorEntryList[1]",
          "locatorName": ["loc1"],
          "locator": {"value": "fc00:0:1::"},
          "prefixLength": {"value": 48},
          "locatorSize": {"value": 64},
          "metric": {"value": 0},
          "algorithm": {"value": 0},
          "redistribution": {"value": "up"},
          "routeOrigin": {"value": "internal"},
          "dBit": {"value": false},
          "advertiseLocatorAsPrefix": {"value": true},
          "enableNFlag": {"value": true},
          "enableRFlag": {"value": false},
          "enableXFlag": {"value": false},
          "mtId": {"value": 0},
          "sidCount": 1,
          "isisSRv6EndSIDList": [
            {
              "xpath": "/topology[1]/deviceGroup[1]/isisL3Router[1]/isisSRv6LocatorEntryList[1]/isisSRv6EndSIDList[1]",
              "sidName": {"value": "End_SID_P1"},
              "sid": {"value": "fc00:0:1::1"},
              "endPointFunction": {"value": "End"},
              "flags": {"value": 0},
              "cFlag": {"value": false},
              "functionLength": {"value": 16},
              "argumentLength": {"value": 0},
              "locatorBlockLength": {"value": 48},
              "locatorNodeLength": {"value": 16},
              "includeSRv6SIDStructureSubSubTlv": {"value": true}
            }
          ]
        }
      ]
    }
  ],
  "ethernet": [
    {
      "xpath": "/topology[1]/deviceGroup[1]/ethernet[1]",
      "isisL3": [
        {
          "xpath": "/topology[1]/deviceGroup[1]/ethernet[1]/isisL3[1]",
          "name": {"value": "p1d1_isis_intf"},
          "networkType": {"value": "pointpoint"},
          "levelType": {"value": "level2"},
          "interfaceMetric": {"value": 10},
          "enableIPv6SID": {"value": true},
          "isisSRv6AdjSIDList": [
            {
              "xpath": "/topology[1]/deviceGroup[1]/ethernet[1]/isisL3[1]/isisSRv6AdjSIDList[1]",
              "ipv6AdjSid": {"value": "fc00:0:1:e001::"},
              "endPointFunction": {"value": "End.X"},
              "algorithm": {"value": 0},
              "weight": {"value": 0},
              "bFlag": {"value": false},
              "sFlag": {"value": false},
              "pFlag": {"value": false},
              "cFlag": {"value": false},
              "functionLength": {"value": 16},
              "argumentLength": {"value": 0},
              "locatorBlockLength": {"value": 48},
              "locatorNodeLength": {"value": 16}
            }
          ]
        }
      ]
    }
  ]
}
```

### 6.4 Verification Steps

| Step | Verification | API Call |
|---|---|---|
| 1 | ISIS L2 session up | `api.get_isis_metrics()` → `l2_sessions_up >= 1` |
| 2 | ISIS LSP database populated | Check via learned LSP info APIs |
| 3 | Locator `fc00:0:1::/48` advertised by P1 visible on P2 | Learned LSP info from P2's perspective |
| 4 | End SID `fc00:0:1::1` with `End` function visible | Check End SID sub-TLV in learned LSP |
| 5 | Adj SID `fc00:0:1:e001::` visible | Check Adj SID sub-TLV in learned adjacency info |
| 6 | Traffic forwarding using SRv6 SIDs (optional) | Configure flow with IPv6 destination = locator |

---

## Appendix A: ISIS-SRv6 TLV/Sub-TLV Reference

| TLV/Sub-TLV | Type | Description |
|---|---|---|
| TLV 242 | Router Capability | Contains sub-TLV 25 (SRv6 Capability) |
| Sub-TLV 25 of TLV 242 | SRv6 Capability | Flags: O, D; Reserved |
| TLV 27 | SRv6 Locator | IPv6 prefix + locator flags + SID sub-TLVs |
| Sub-TLV 5 of TLV 27 | SRv6 End SID | SID value + End-Point function + flags |
| Sub-TLV 1 of TLV 22 | SRv6 Adj SID | IPv6 SID + flags for adjacency |
| Sub-Sub-TLV 1 of End SID | SRv6 SID Structure | Locator Block/Node, Function, Argument lengths |

## Appendix B: Key RFCs and Drafts

| Reference | Description |
|---|---|
| RFC 8986 | SRv6 Network Programming |
| RFC 9252 | BGP Overlay Services Based on SRv6 |
| draft-ietf-lsr-isis-srv6-extensions | IS-IS Extensions to Support SRv6 |
| RFC 8402 | Segment Routing Architecture |
| RFC 8667 | IS-IS Extensions for Segment Routing (MPLS SR, provides base SR framework) |
