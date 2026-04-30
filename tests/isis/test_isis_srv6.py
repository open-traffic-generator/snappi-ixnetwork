import pytest
import time


def test_isis_srv6_b2b(api, b2b_raw_config, utils):
    """Back-to-back ISIS-SRv6 test
    - Configure two devices with ISIS over an IPv4 link
    - Enable SRv6 via segment_routing.router_capability.srv6_capability
    - Advertise one SRv6 locator per router with one End SID each
    - Configure SRv6 Adjacency SIDs (End.X) on each interface
    - Start protocols and verify ISIS L2 sessions come up
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

    # --------------------------------------------------------------- IPv4
    p1d1_ipv4 = p1d1_eth.ipv4_addresses.add()
    p1d1_ipv4.name = "p1d1_ipv4"
    p1d1_ipv4.address = "1.1.1.2"
    p1d1_ipv4.gateway = "1.1.1.1"
    p1d1_ipv4.prefix = 24

    p2d1_ipv4 = p2d1_eth.ipv4_addresses.add()
    p2d1_ipv4.name = "p2d1_ipv4"
    p2d1_ipv4.address = "1.1.1.1"
    p2d1_ipv4.gateway = "1.1.1.2"
    p2d1_ipv4.prefix = 24

    # ========================================================= port-1 ISIS
    p1d1_isis = p1d1.isis
    p1d1_isis.name = "p1d1_isis"
    p1d1_isis.system_id = "670000000001"

    p1d1_isis.basic.hostname = "ixia-c-port1"
    p1d1_isis.basic.enable_wide_metric = True
    p1d1_isis.basic.learned_lsp_filter = False

    p1d1_isis.advanced.area_addresses = ["490001"]
    p1d1_isis.advanced.csnp_interval = 10000
    p1d1_isis.advanced.enable_hello_padding = True
    p1d1_isis.advanced.lsp_lifetime = 1200
    p1d1_isis.advanced.lsp_refresh_rate = 900

    # SRv6 capability flags
    p1d1_srv6_cap = p1d1_isis.segment_routing.router_capability.srv6_capability
    p1d1_srv6_cap.c_flag = False
    p1d1_srv6_cap.o_flag = False

    # SRv6 locator
    p1d1_loc = p1d1_isis.segment_routing.srv6_locators.add()
    p1d1_loc.locator_name = "loc1"
    p1d1_loc.locator = "fc00:0:1::"
    p1d1_loc.prefix_length = 48
    p1d1_loc.algorithm = 0
    p1d1_loc.metric = 0
    p1d1_loc.d_flag = False
    # SID structure: block=48, node=16, function=16
    p1d1_loc.sid_structure.locator_block_length = 48
    p1d1_loc.sid_structure.locator_node_length = 16
    p1d1_loc.sid_structure.function_length = 16
    p1d1_loc.sid_structure.argument_length = 0
    # Advertise as prefix
    p1d1_loc.advertise_locator_as_prefix.redistribution_type = "up"
    p1d1_loc.advertise_locator_as_prefix.route_origin = "internal"
    p1d1_loc.advertise_locator_as_prefix.prefix_attributes.n_flag = True
    p1d1_loc.advertise_locator_as_prefix.prefix_attributes.r_flag = False
    p1d1_loc.advertise_locator_as_prefix.prefix_attributes.x_flag = False

    # End SID: function=0x0001 → SID = fc00:0:1:0:1::
    p1d1_end_sid = p1d1_loc.end_sids.add()
    p1d1_end_sid.locator = "auto"
    p1d1_end_sid.function = "1"
    p1d1_end_sid.endpoint_behavior = "end"
    p1d1_end_sid.c_flag = False

    # ISIS interface
    p1d1_isis_intf = p1d1_isis.interfaces.add()
    p1d1_isis_intf.eth_name = p1d1_eth.name
    p1d1_isis_intf.name = "p1d1_isis_intf"
    p1d1_isis_intf.network_type = "point_to_point"
    p1d1_isis_intf.level_type = "level_2"
    p1d1_isis_intf.metric = 10
    p1d1_isis_intf.l2_settings.dead_interval = 30
    p1d1_isis_intf.l2_settings.hello_interval = 10
    p1d1_isis_intf.l2_settings.priority = 0

    # SRv6 Adj SID: function=0xe001 → SID = fc00:0:1:0:e001::
    p1d1_adj_sid = p1d1_isis_intf.srv6_adjacency_sids.add()
    p1d1_adj_sid.locator = "custom_locator_reference"
    p1d1_adj_sid.custom_locator_reference = "loc1"
    p1d1_adj_sid.function = "e001"
    p1d1_adj_sid.endpoint_behavior = "end_x"
    p1d1_adj_sid.algorithm = 0
    p1d1_adj_sid.weight = 0
    p1d1_adj_sid.b_flag = False
    p1d1_adj_sid.s_flag = False
    p1d1_adj_sid.p_flag = False
    p1d1_adj_sid.c_flag = False
    p1d1_adj_sid.sid_structure.locator_block_length = 48
    p1d1_adj_sid.sid_structure.locator_node_length = 16
    p1d1_adj_sid.sid_structure.function_length = 16
    p1d1_adj_sid.sid_structure.argument_length = 0

    # ========================================================= port-2 ISIS
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

    # SRv6 capability flags
    p2d1_srv6_cap = p2d1_isis.segment_routing.router_capability.srv6_capability
    p2d1_srv6_cap.c_flag = False
    p2d1_srv6_cap.o_flag = False

    # SRv6 locator
    p2d1_loc = p2d1_isis.segment_routing.srv6_locators.add()
    p2d1_loc.locator_name = "loc1"
    p2d1_loc.locator = "fc00:0:2::"
    p2d1_loc.prefix_length = 48
    p2d1_loc.algorithm = 0
    p2d1_loc.metric = 0
    p2d1_loc.d_flag = False
    p2d1_loc.sid_structure.locator_block_length = 48
    p2d1_loc.sid_structure.locator_node_length = 16
    p2d1_loc.sid_structure.function_length = 16
    p2d1_loc.sid_structure.argument_length = 0
    p2d1_loc.advertise_locator_as_prefix.redistribution_type = "up"
    p2d1_loc.advertise_locator_as_prefix.route_origin = "internal"
    p2d1_loc.advertise_locator_as_prefix.prefix_attributes.n_flag = True
    p2d1_loc.advertise_locator_as_prefix.prefix_attributes.r_flag = False
    p2d1_loc.advertise_locator_as_prefix.prefix_attributes.x_flag = False

    # End SID: function=0x0001 → SID = fc00:0:2:0:1::
    p2d1_end_sid = p2d1_loc.end_sids.add()
    p2d1_end_sid.locator = "auto"
    p2d1_end_sid.function = "1"
    p2d1_end_sid.endpoint_behavior = "end"
    p2d1_end_sid.c_flag = False

    # ISIS interface
    p2d1_isis_intf = p2d1_isis.interfaces.add()
    p2d1_isis_intf.eth_name = p2d1_eth.name
    p2d1_isis_intf.name = "p2d1_isis_intf"
    p2d1_isis_intf.network_type = "point_to_point"
    p2d1_isis_intf.level_type = "level_2"
    p2d1_isis_intf.metric = 10
    p2d1_isis_intf.l2_settings.dead_interval = 30
    p2d1_isis_intf.l2_settings.hello_interval = 10
    p2d1_isis_intf.l2_settings.priority = 0

    # SRv6 Adj SID: function=0xe001 → SID = fc00:0:2:0:e001::
    p2d1_adj_sid = p2d1_isis_intf.srv6_adjacency_sids.add()
    p2d1_adj_sid.locator = "custom_locator_reference"
    p2d1_adj_sid.custom_locator_reference = "loc1"
    p2d1_adj_sid.function = "e001"
    p2d1_adj_sid.endpoint_behavior = "end_x"
    p2d1_adj_sid.algorithm = 0
    p2d1_adj_sid.weight = 0
    p2d1_adj_sid.b_flag = False
    p2d1_adj_sid.s_flag = False
    p2d1_adj_sid.p_flag = False
    p2d1_adj_sid.c_flag = False
    p2d1_adj_sid.sid_structure.locator_block_length = 48
    p2d1_adj_sid.sid_structure.locator_node_length = 16
    p2d1_adj_sid.sid_structure.function_length = 16
    p2d1_adj_sid.sid_structure.argument_length = 0

    # ============================================================= push config
    utils.start_traffic(api, b2b_raw_config)
    time.sleep(15)

    # ============================================================= verify
    req = api.metrics_request()
    req.isis.router_names = []
    req.isis.column_names = ["l2_sessions_up"]
    results = api.get_metrics(req)
    assert len(results.isis_metrics) == 2
    for metric in results.isis_metrics:
        assert metric.l2_sessions_up >= 1, (
            "Expected ISIS L2 session up for %s, got %s"
            % (metric.name, metric.l2_sessions_up)
        )

    utils.stop_traffic(api, b2b_raw_config)
