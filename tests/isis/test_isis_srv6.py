import pytest
import time


@pytest.mark.skip(reason="Not implemented")
def test_isis_srv6(api, b2b_raw_config, utils):
    """Test ISIS SRv6 (Segment Routing over IPv6, RFC 9352)

    Topology: port1 <---> port2 (back-to-back or via DUT)

    Configuration:
    - Two ISIS Level-2 routers, each advertising a SRv6 Locator TLV (TLV 27)
      with one End SID sub-TLV (END_WITH_PSP behaviour)
    - p1 locator: fc00:1::/48,  End SID: fc00:1::1
    - p2 locator: fc00:2::/48,  End SID: fc00:2::1

    Verification:
    - ISIS L2 session comes up on both routers (l2_sessions_up == 1)
    - Traffic flows IPv6 src=link-addr -> dst=remote End SID with zero loss
    """
    packets = 1000
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
    p2d1_eth.mac = "00:00:02:03:03:03"
    p2d1_eth.mtu = 1500

    # ----------------------------------------------- IPv4 address – port 1
    p1d1_ipv4 = p1d1_eth.ipv4_addresses.add()
    p1d1_ipv4.name = "p1d1Ipv4"
    p1d1_ipv4.address = "1.1.1.2"
    p1d1_ipv4.gateway = "1.1.1.1"
    p1d1_ipv4.prefix = 24

    # ----------------------------------------------- IPv6 address – port 1
    p1d1_ipv6 = p1d1_eth.ipv6_addresses.add()
    p1d1_ipv6.name = "p1d1Ipv6"
    p1d1_ipv6.address = "2001::1:1:1:2"
    p1d1_ipv6.gateway = "2001::1:1:1:1"
    p1d1_ipv6.prefix = 64

    # ----------------------------------------------- IPv4 address – port 2
    p2d1_ipv4 = p2d1_eth.ipv4_addresses.add()
    p2d1_ipv4.name = "p2d1Ipv4"
    p2d1_ipv4.address = "1.1.1.1"
    p2d1_ipv4.gateway = "1.1.1.2"
    p2d1_ipv4.prefix = 24

    # ----------------------------------------------- IPv6 address – port 2
    p2d1_ipv6 = p2d1_eth.ipv6_addresses.add()
    p2d1_ipv6.name = "p2d1Ipv6"
    p2d1_ipv6.address = "2002::2:2:1:2"
    p2d1_ipv6.gateway = "2002::2:2:1:1"
    p2d1_ipv6.prefix = 64

    # --------------------------------------------------- ISIS router – port 1
    p1d1_isis = p1d1.isis
    p1d1_isis.name = "p1d1Isis"
    p1d1_isis.system_id = "640000000001"

    p1d1_isis.basic.ipv4_te_router_id = p1d1_ipv4.address
    p1d1_isis.basic.hostname = "ixia-c-port1"
    p1d1_isis.basic.enable_wide_metric = True
    p1d1_isis.basic.learned_lsp_filter = True

    p1d1_isis.advanced.area_addresses = ["490001"]
    p1d1_isis.advanced.enable_attached_bit = False

    # --------------------------------- SR / SRv6 capability – port 1
    p1_sr = p1d1_isis.segment_routing
    p1_rtr_cap = p1_sr.router_capability
    p1_rtr_cap.custom_router_cap_id = p1d1_ipv4.address
    p1_rtr_cap.s_bit = p1_rtr_cap.FLOOD
    p1_rtr_cap.d_bit = p1_rtr_cap.DOWN
    p1_rtr_cap.srv6_capability.o_flag = False

    # SRv6 Locator TLV (TLV 27) – port 1: fc00:1::/48
    p1_loc = p1_sr.srv6_locators.add()
    p1_loc.name = "p1d1Srv6Loc"
    p1_loc.locator = "fc00:1::"
    p1_loc.prefix_length = 48
    p1_loc.algorithm = 0
    p1_loc.metric = 10

    # End SID sub-TLV – port 1: fc00:1::1  (End with PSP)
    p1_end_sid = p1_loc.end_sids.add()
    p1_end_sid.sid = "fc00:1::1"
    p1_end_sid.endpoint_behavior = p1_end_sid.END_WITH_PSP

    # ---------------------------------------- ISIS interface – port 1
    p1d1_isis_intf = p1d1_isis.interfaces.add()
    p1d1_isis_intf.name = "p1d1IsisIntf"
    p1d1_isis_intf.eth_name = p1d1_eth.name
    p1d1_isis_intf.network_type = p1d1_isis_intf.POINT_TO_POINT
    p1d1_isis_intf.level_type = p1d1_isis_intf.LEVEL_2
    p1d1_isis_intf.metric = 10
    p1d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # --------------------------------------------------- ISIS router – port 2
    p2d1_isis = p2d1.isis
    p2d1_isis.name = "p2d1Isis"
    p2d1_isis.system_id = "650000000001"

    p2d1_isis.basic.ipv4_te_router_id = p2d1_ipv4.address
    p2d1_isis.basic.hostname = "ixia-c-port2"
    p2d1_isis.basic.enable_wide_metric = True
    p2d1_isis.basic.learned_lsp_filter = True

    p2d1_isis.advanced.area_addresses = ["490001"]
    p2d1_isis.advanced.enable_attached_bit = False

    # --------------------------------- SR / SRv6 capability – port 2
    p2_sr = p2d1_isis.segment_routing
    p2_rtr_cap = p2_sr.router_capability
    p2_rtr_cap.custom_router_cap_id = p2d1_ipv4.address
    p2_rtr_cap.s_bit = p2_rtr_cap.FLOOD
    p2_rtr_cap.d_bit = p2_rtr_cap.DOWN
    p2_rtr_cap.srv6_capability.o_flag = False

    # SRv6 Locator TLV (TLV 27) – port 2: fc00:2::/48
    p2_loc = p2_sr.srv6_locators.add()
    p2_loc.name = "p2d1Srv6Loc"
    p2_loc.locator = "fc00:2::"
    p2_loc.prefix_length = 48
    p2_loc.algorithm = 0
    p2_loc.metric = 10

    # End SID sub-TLV – port 2: fc00:2::1  (End with PSP)
    p2_end_sid = p2_loc.end_sids.add()
    p2_end_sid.sid = "fc00:2::1"
    p2_end_sid.endpoint_behavior = p2_end_sid.END_WITH_PSP

    # ---------------------------------------- ISIS interface – port 2
    p2d1_isis_intf = p2d1_isis.interfaces.add()
    p2d1_isis_intf.name = "p2d1IsisIntf"
    p2d1_isis_intf.eth_name = p2d1_eth.name
    p2d1_isis_intf.network_type = p2d1_isis_intf.POINT_TO_POINT
    p2d1_isis_intf.level_type = p2d1_isis_intf.LEVEL_2
    p2d1_isis_intf.metric = 10
    p2d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # ------- Flow 1: p1 → p2  (src=p1 link IPv6, dst=p2 End SID fc00:2::1)
    f1 = b2b_raw_config.flows.flow(name="f1:p1->p2")[-1]
    f1.metrics.enable = True
    f1.size.fixed = 300
    f1.rate.pps = 100
    f1.duration.fixed_packets.packets = packets
    f1.tx_rx.port.tx_name = p1.name
    f1.tx_rx.port.rx_name = p2.name

    f1_eth, f1_ipv6 = f1.packet.ethernet().ipv6()
    f1_eth.src.value = p1d1_eth.mac
    f1_ipv6.src.value = "2001::1:1:1:2"
    f1_ipv6.dst.value = "fc00:2::1"

    # ------- Flow 2: p2 → p1  (src=p2 link IPv6, dst=p1 End SID fc00:1::1)
    f2 = b2b_raw_config.flows.flow(name="f2:p2->p1")[-1]
    f2.metrics.enable = True
    f2.size.fixed = 300
    f2.rate.pps = 100
    f2.duration.fixed_packets.packets = packets
    f2.tx_rx.port.tx_name = p2.name
    f2.tx_rx.port.rx_name = p1.name

    f2_eth, f2_ipv6 = f2.packet.ethernet().ipv6()
    f2_eth.src.value = p2d1_eth.mac
    f2_ipv6.src.value = "2002::2:2:1:2"
    f2_ipv6.dst.value = "fc00:1::1"

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
