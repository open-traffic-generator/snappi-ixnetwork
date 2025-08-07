import pytest
import time

# @pytest.mark.skip(reason="Not implemented")
def test_isis_v6_rr(api, b2b_raw_config, utils):
    """Test only isis with v6 route range
    - set_config
    - start protocols
    - verify isis metrics
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    # Adding ports
    p1, p2 = b2b_raw_config.ports

    # Device
    p1d1, p2d1 = b2b_raw_config.devices.device(name="p1d1").device(name="p2d1")

    # Ethernet
    p1d1_eth, p2d1_eth = p1d1.ethernets.add(), p2d1.ethernets.add()
    p1d1_eth.connection.port_name = p1.name
    p1d1_eth.name = "p1d1_eth"
    p1d1_eth.mac = "00:00:00:01:01:01"
    p1d1_eth.mtu = 1500

    p2d1_eth.connection.port_name = p2.name
    p2d1_eth.name = "p2d1_eth"
    p2d1_eth.mac = "00:00:00:02:02:02"
    p2d1_eth.mtu = 1500

    # port 1 device 1 ipv4
    p1d1_ipv4 = p1d1_eth.ipv4_addresses.add()
    p1d1_ipv4.address = "1.1.1.2"
    p1d1_ipv4.gateway = "1.1.1.1"
    p1d1_ipv4.name = "p1d1_ipv4"
    p1d1_ipv4.prefix = 24

    # port 1 device 1 isis
    p1d1_isis = p1d1.isis
    p1d1_isis.name = "p1d1_isis"
    p1d1_isis.system_id = "640000000001"

    # port 1 device 1 isis basic
    p1d1_isis.basic.ipv4_te_router_id = p1d1_ipv4.address
    p1d1_isis.basic.hostname = "ixia-c-port1"
    p1d1_isis.basic.enable_wide_metric = True
    p1d1_isis.basic.learned_lsp_filter = True

    # port 1 device 1 isis advance
    p1d1_isis.advanced.area_addresses = ["490001"]
    p1d1_isis.advanced.csnp_interval = 10000
    p1d1_isis.advanced.enable_hello_padding = True
    p1d1_isis.advanced.lsp_lifetime = 1200
    p1d1_isis.advanced.lsp_mgroup_min_trans_interval = 5000
    p1d1_isis.advanced.lsp_refresh_rate = 900
    p1d1_isis.advanced.max_area_addresses = 3
    p1d1_isis.advanced.max_lsp_size = 1492
    p1d1_isis.advanced.psnp_interval = 2000
    p1d1_isis.advanced.enable_attached_bit = False

    # port 1 device 1 isis interface
    p1d1_isis_intf = p1d1_isis.interfaces.add()
    p1d1_isis_intf.eth_name = p1d1_eth.name
    p1d1_isis_intf.network_type = "point_to_point"
    p1d1_isis_intf.level_type = "level_1"
    p1d1_isis_intf.metric = 10
    p1d1_isis_intf.name = "p1d1_isis_intf"
    p1d1_isis_intf.l2_settings.dead_interval = 30
    p1d1_isis_intf.l2_settings.hello_interval = 10
    p1d1_isis_intf.l2_settings.priority = 0
    p1d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # port 1 device 1 isis v4 routes
    p1d1_isis_v6routes = p1d1_isis.v6_routes.add()
    p1d1_isis_v6routes.name = "p1d1_isis_v6routes"
    p1d1_isis_v6routes.link_metric = 10
    p1d1_isis_v6routes.origin_type = "internal"
    p1d1_isis_v6routes_addr = p1d1_isis_v6routes.addresses.add()
    p1d1_isis_v6routes_addr.address = "1000:0:0:1::a"
    p1d1_isis_v6routes_addr.prefix = 64
    p1d1_isis_v6routes_addr.count = 2
    p1d1_isis_v6routes_addr.step = 1 

    # port 2 device 1 ipv4
    p2d1_ipv4 = p2d1_eth.ipv4_addresses.add()
    p2d1_ipv4.address = "1.1.1.1"
    p2d1_ipv4.gateway = "1.1.1.2"
    p2d1_ipv4.name = "p2d1_ipv4"
    p2d1_ipv4.prefix = 24

    # port 2 device 1 isis
    p2d1_isis = p2d1.isis
    p2d1_isis.name = "p2d1_isis"
    p2d1_isis.system_id = "650000000001"

    # port 2 device 1 isis basic
    p2d1_isis.basic.ipv4_te_router_id = p2d1_ipv4.address
    p2d1_isis.basic.hostname = "ixia-c-port2"
    p2d1_isis.basic.enable_wide_metric = True
    p2d1_isis.basic.learned_lsp_filter = True

    # port 2 device 1 isis advanced
    p2d1_isis.advanced.area_addresses = ["490001"]
    p2d1_isis.advanced.csnp_interval = 10000
    p2d1_isis.advanced.enable_hello_padding = True
    p2d1_isis.advanced.lsp_lifetime = 1200
    p2d1_isis.advanced.lsp_mgroup_min_trans_interval = 5000
    p2d1_isis.advanced.lsp_refresh_rate = 900
    p2d1_isis.advanced.max_area_addresses = 3
    p2d1_isis.advanced.max_lsp_size = 1492
    p2d1_isis.advanced.psnp_interval = 2000
    p2d1_isis.advanced.enable_attached_bit = False

    # port 2 device 1 isis interface
    p2d1_isis_intf = p2d1_isis.interfaces.add()
    p2d1_isis_intf.eth_name = p2d1_eth.name
    p2d1_isis_intf.network_type = "point_to_point"
    p2d1_isis_intf.level_type = "level_1"
    p2d1_isis_intf.metric = 10
    p2d1_isis_intf.name = "p2d1_isis_intf"
    p2d1_isis_intf.l2_settings.dead_interval = 30
    p2d1_isis_intf.l2_settings.hello_interval = 10
    p2d1_isis_intf.l2_settings.priority = 0
    p2d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # port 2 device 1 isis v4 routes
    p2d1_isis_v6routes = p2d1_isis.v6_routes.add()
    p2d1_isis_v6routes.name = "p2d1_isis_v6routes"
    p2d1_isis_v6routes.link_metric = 10
    p2d1_isis_v6routes.origin_type = "internal"
    p2d1_isis_v6routes_addr = p2d1_isis_v6routes.addresses.add()
    p2d1_isis_v6routes_addr.address = "1000:0:0:1::b"
    p2d1_isis_v6routes_addr.prefix = 64
    p2d1_isis_v6routes_addr.count = 2
    p2d1_isis_v6routes_addr.step = 1
    
    utils.start_traffic(api, b2b_raw_config)
    
    enums = [
        "l1_sessions_up",
        "l1_session_flap",
        "l1_database_size",
    ]

    expected_results = {
        "p1d1": [1, 0, 2],
        "p2d1": [1, 0, 2],
    }

    time.sleep(10)
    
    # IS-IS metrics
    req = api.metrics_request()
    req.isis.router_names = []
    req.isis.column_names = enums[:3]
    results = api.get_metrics(req)
    
    assert len(results.isis_metrics) == 2
    for isis_res in results.isis_metrics:
        for i, enum in enumerate(enums[:3]):
            val = expected_results[isis_res.name][i]
            if "l1_sessions_up" in enum:
                assert getattr(isis_res, enum) == val
            else:
                assert getattr(isis_res, enum) >= val

    print(results)

    utils.stop_traffic(api, b2b_raw_config)


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])