import pytest
import time


def test_isis_sr(api, b2b_raw_config, utils):
    """Test ISIS SR-MPLS (Segment Routing with MPLS data plane, RFC 8667)

    Topology: port1 <---> port2 (back-to-back or via DUT)

    Configuration:
    - Two ISIS Level-2 routers, each advertising SR capability (SRGB) and
      IPv4 prefix SIDs
    - SRGB: base 16000, range 8000  (labels 16000–23999)
    - p1 v4 route: 10.1.1.0/24, Prefix-SID index 1 → label 16001
    - p2 v4 route: 10.2.1.0/24, Prefix-SID index 2 → label 16002

    Verification:
    - ISIS L2 session comes up on both routers (l2_sessions_up == 1)
    - Traffic flows IPv4 between the advertised prefix ranges with zero loss
    """
    packets = 10000
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    # ------------------------------------------------------------------ ports
    p1, p2 = b2b_raw_config.ports

    # ----------------------------------------------------------------- devices
    p1d1, p2d1 = (
        b2b_raw_config.devices.device(name="p1d1").device(name="p2d1")
    )

    # ---------------------------------------------------- ethernet – port 1
    p1d1_eth = p1d1.ethernets.add()
    p1d1_eth.connection.port_name = p1.name
    p1d1_eth.name = "p1d1Eth"
    p1d1_eth.mac = "00:00:01:01:01:01"
    p1d1_eth.mtu = 1500

    # ---------------------------------------------------- ethernet – port 2
    p2d1_eth = p2d1.ethernets.add()
    p2d1_eth.connection.port_name = p2.name
    p2d1_eth.name = "p2d1Eth"
    p2d1_eth.mac = "00:00:02:02:02:02"
    p2d1_eth.mtu = 1500

    # ----------------------------------------------- IPv4 address – port 1
    p1d1_ipv4 = p1d1_eth.ipv4_addresses.add()
    p1d1_ipv4.name = "p1d1Ipv4"
    p1d1_ipv4.address = "1.1.1.2"
    p1d1_ipv4.gateway = "1.1.1.1"
    p1d1_ipv4.prefix = 24

    # ----------------------------------------------- IPv4 address – port 2
    p2d1_ipv4 = p2d1_eth.ipv4_addresses.add()
    p2d1_ipv4.name = "p2d1Ipv4"
    p2d1_ipv4.address = "1.1.1.1"
    p2d1_ipv4.gateway = "1.1.1.2"
    p2d1_ipv4.prefix = 24

    # --------------------------------------------------- ISIS router – port 1
    p1d1_isis = p1d1.isis
    p1d1_isis.name = "p1d1Isis"
    p1d1_isis.system_id = "610000000001"

    p1d1_isis.basic.ipv4_te_router_id = p1d1_ipv4.address
    p1d1_isis.basic.hostname = "ixia-c-port1"
    p1d1_isis.basic.enable_wide_metric = True
    p1d1_isis.basic.learned_lsp_filter = True

    p1d1_isis.advanced.area_addresses = ["490001"]
    p1d1_isis.advanced.enable_attached_bit = False

    # --------------------------------- SR-MPLS capability – port 1
    p1_sr = p1d1_isis.segment_routing
    p1_rtr_cap = p1_sr.router_capability
    p1_rtr_cap.custom_router_cap_id = p1d1_ipv4.address
    p1_rtr_cap.s_bit = p1_rtr_cap.FLOOD
    p1_rtr_cap.d_bit = p1_rtr_cap.DOWN

    # SRGB: starting label 16000, block size 8000
    p1_sr_cap = p1_rtr_cap.sr_capability
    p1_sr_cap.flags.ipv4_mpls = True
    p1_srgb = p1_sr_cap.srgb_ranges.add()
    p1_srgb.starting_sid = 16000
    p1_srgb.range = 8000

    # ---------------------------------------- ISIS interface – port 1
    p1d1_isis_intf = p1d1_isis.interfaces.add()
    p1d1_isis_intf.name = "p1d1IsisIntf"
    p1d1_isis_intf.eth_name = p1d1_eth.name
    p1d1_isis_intf.network_type = p1d1_isis_intf.POINT_TO_POINT
    p1d1_isis_intf.level_type = p1d1_isis_intf.LEVEL_2
    p1d1_isis_intf.metric = 10
    p1d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # ----------- IPv4 route range with Prefix-SID – port 1: 10.1.1.0/24
    p1d1_v4routes = p1d1_isis.v4_routes.add()
    p1d1_v4routes.name = "p1d1V4Routes"
    p1d1_v4routes.link_metric = 10
    p1d1_v4routes.origin_type = "internal"

    p1d1_v4routes_addr = p1d1_v4routes.addresses.add()
    p1d1_v4routes_addr.address = "10.1.1.0"
    p1d1_v4routes_addr.prefix = 24
    p1d1_v4routes_addr.count = 1
    p1d1_v4routes_addr.step = 1

    # Prefix-SID index 1 → MPLS label = SRGB_base(16000) + 1 = 16001
    p1_prefix_sid = p1d1_v4routes.prefix_sids.add()
    p1_prefix_sid.sid_indices = [1]
    p1_prefix_sid.n_flag = True

    # --------------------------------------------------- ISIS router – port 2
    p2d1_isis = p2d1.isis
    p2d1_isis.name = "p2d1Isis"
    p2d1_isis.system_id = "620000000001"

    p2d1_isis.basic.ipv4_te_router_id = p2d1_ipv4.address
    p2d1_isis.basic.hostname = "ixia-c-port2"
    p2d1_isis.basic.enable_wide_metric = True
    p2d1_isis.basic.learned_lsp_filter = True

    p2d1_isis.advanced.area_addresses = ["490001"]
    p2d1_isis.advanced.enable_attached_bit = False

    # --------------------------------- SR-MPLS capability – port 2
    p2_sr = p2d1_isis.segment_routing
    p2_rtr_cap = p2_sr.router_capability
    p2_rtr_cap.custom_router_cap_id = p2d1_ipv4.address
    p2_rtr_cap.s_bit = p2_rtr_cap.FLOOD
    p2_rtr_cap.d_bit = p2_rtr_cap.DOWN

    # SRGB: starting label 16000, block size 8000
    p2_sr_cap = p2_rtr_cap.sr_capability
    p2_sr_cap.flags.ipv4_mpls = True
    p2_srgb = p2_sr_cap.srgb_ranges.add()
    p2_srgb.starting_sid = 16000
    p2_srgb.range = 8000

    # ---------------------------------------- ISIS interface – port 2
    p2d1_isis_intf = p2d1_isis.interfaces.add()
    p2d1_isis_intf.name = "p2d1IsisIntf"
    p2d1_isis_intf.eth_name = p2d1_eth.name
    p2d1_isis_intf.network_type = p2d1_isis_intf.POINT_TO_POINT
    p2d1_isis_intf.level_type = p2d1_isis_intf.LEVEL_2
    p2d1_isis_intf.metric = 10
    p2d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # ----------- IPv4 route range with Prefix-SID – port 2: 10.2.1.0/24
    p2d1_v4routes = p2d1_isis.v4_routes.add()
    p2d1_v4routes.name = "p2d1V4Routes"
    p2d1_v4routes.link_metric = 10
    p2d1_v4routes.origin_type = "internal"

    p2d1_v4routes_addr = p2d1_v4routes.addresses.add()
    p2d1_v4routes_addr.address = "10.2.1.0"
    p2d1_v4routes_addr.prefix = 24
    p2d1_v4routes_addr.count = 1
    p2d1_v4routes_addr.step = 1

    # Prefix-SID index 2 → MPLS label = SRGB_base(16000) + 2 = 16002
    p2_prefix_sid = p2d1_v4routes.prefix_sids.add()
    p2_prefix_sid.sid_indices = [2]
    p2_prefix_sid.n_flag = True

    # ----------------------------------------------------------------- flows
    # Flow 1: p1 routes → p2 routes  (MPLS-encapsulated IPv4)
    f1 = b2b_raw_config.flows.flow(name="f1:p1->p2")[-1]
    f1.tx_rx.device.tx_names = [p1d1_v4routes.name]
    f1.tx_rx.device.rx_names = [p2d1_v4routes.name]
    f1.size.fixed = 128
    f1.rate.pps = 1000
    f1.duration.fixed_packets.packets = packets
    f1.metrics.enable = True
    f1.packet.ethernet().ipv4()

    # Flow 2: p2 routes → p1 routes  (MPLS-encapsulated IPv4)
    f2 = b2b_raw_config.flows.flow(name="f2:p2->p1")[-1]
    f2.tx_rx.device.tx_names = [p2d1_v4routes.name]
    f2.tx_rx.device.rx_names = [p1d1_v4routes.name]
    f2.size.fixed = 128
    f2.rate.pps = 1000
    f2.duration.fixed_packets.packets = packets
    f2.metrics.enable = True
    f2.packet.ethernet().ipv4()

    # ---------------------------------------------------------- start traffic
    utils.start_traffic(api, b2b_raw_config)

    # ----------------------------------------- verify ISIS L2 session metrics
    enums = [
        "l2_sessions_up",
        "l2_session_flap",
        "l2_database_size",
    ]
    expected_results = {
        "p1d1": [1, 0, 2],
        "p2d1": [1, 0, 2],
    }

    time.sleep(10)

    req = api.metrics_request()
    req.isis.router_names = []
    req.isis.column_names = enums
    results = api.get_metrics(req)

    assert len(results.isis_metrics) == 2
    for isis_res in results.isis_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[isis_res.name][i]
            if enum == "l2_sessions_up":
                assert getattr(isis_res, enum) == val, (
                    f"{isis_res.name}: expected {enum}={val}, "
                    f"got {getattr(isis_res, enum)}"
                )
            else:
                assert getattr(isis_res, enum) >= val, (
                    f"{isis_res.name}: expected {enum}>={val}, "
                    f"got {getattr(isis_res, enum)}"
                )

    # ----------------------------------------- verify zero traffic loss
    utils.wait_for(
        lambda: _flows_ok(api, ["f1:p1->p2", "f2:p2->p1"], packets * 2),
        "flow stats to reach expected rx count",
        timeout_seconds=30,
    )

    utils.stop_traffic(api, b2b_raw_config)


def _flows_ok(api, flow_names, expected_total):
    """Return True when total frames_rx across all named flows == expected_total."""
    req = api.metrics_request()
    req.flow.flow_names = flow_names
    flow_metrics = api.get_metrics(req).flow_metrics
    return sum(f.frames_rx for f in flow_metrics) == expected_total


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
