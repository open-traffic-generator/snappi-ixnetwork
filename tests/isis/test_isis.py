import pytest
import time

# @pytest.mark.skip(reason="Not implemented")
def test_isis(api, b2b_raw_config, utils):
    """
    Test for the IS-IS metrics
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
    p1d1_isis_intf.level_type = "level_1_2"
    p1d1_isis_intf.metric = 10
    p1d1_isis_intf.name = "p1d1_isis_intf"
    p1d1_isis_intf.l2_settings.dead_interval = 30
    p1d1_isis_intf.l2_settings.hello_interval = 10
    p1d1_isis_intf.l2_settings.priority = 0
    p1d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # # port 1 device 1 isis v4 routes
    # p1d1_isis_v4routes = p1d1_isis.v4_routes.add()
    # p1d1_isis_v4routes.name = "p1d1_isis_v4routes"
    # p1d1_isis_v4routes.link_metric = 10
    # p1d1_isis_v4routes.origin_type = "internal"
    # p1d1_isis_v4routes_addr = p1d1_isis_v4routes.addresses.add()
    # p1d1_isis_v4routes_addr.address = "10.10.1.1"
    # p1d1_isis_v4routes_addr.prefix = 32
    # p1d1_isis_v4routes_addr.count = 2
    # p1d1_isis_v4routes_addr.step = 1 

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
    p2d1_isis_intf.level_type = "level_1_2"
    p2d1_isis_intf.metric = 10
    p2d1_isis_intf.name = "p2d1_isis_intf"
    p2d1_isis_intf.l2_settings.dead_interval = 30
    p2d1_isis_intf.l2_settings.hello_interval = 10
    p2d1_isis_intf.l2_settings.priority = 0
    p2d1_isis_intf.advanced.auto_adjust_supported_protocols = True

    # # port 2 device 1 isis v4 routes
    # p2d1_isis_v4routes = p2d1_isis.v4_routes.add()
    # p2d1_isis_v4routes.name = "p2d1_isis_v4routes"
    # p2d1_isis_v4routes.link_metric = 10
    # p2d1_isis_v4routes.origin_type = "internal"
    # p2d1_isis_v4routes_addr = p2d1_isis_v4routes.addresses.add()
    # p2d1_isis_v4routes_addr.address = "10.10.1.1"
    # p2d1_isis_v4routes_addr.prefix = 32
    # p2d1_isis_v4routes_addr.count = 2
    # p2d1_isis_v4routes_addr.step = 1

    # api.set_config(b2b_raw_config)
    utils.start_traffic(api, b2b_raw_config)
    # api.start_protocols()
    time.sleep(30)
    enums = [
        "l2_sessions_up",
        "l2_session_flap",
        "l2_database_size",
    ]

    # IS-IS metrics
    req = api.metrics_request()
    req.isis.router_names = []
    req.isis.column_names = enums[:3]
    results = api.get_metrics(req)
    print(results)
    utils.stop_traffic(api, b2b_raw_config)

    # TODO: Add validation

if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])