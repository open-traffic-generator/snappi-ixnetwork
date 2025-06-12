import pytest
import time

@pytest.mark.skip(reason="Not implemented")
def test_isis_stats(api, b2b_raw_config, utils):
    """
    Test for the bgpv4 metrics
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    ptx, prx = b2b_raw_config.ports
    dtx, drx = b2b_raw_config.devices.device(name="dtx").device(name="rtx")

    dtx_eth = dtx.ethernets.add(name="dtx_eth")
    dtx_eth.connection.port_name = ptx.name
    dtx_eth.mac = "00:00:01:01:01:01"
    dtx_eth.mtu = 1500

    dtx_ip = dtx_eth.ipv4_addresses.add(name="dtx_ip")
    dtx_ip.address = "1.1.1.1"
    dtx_ip.gateway = "1.1.1.1"
    dtx_ip.prefix = 24

    dtx_ipv6 = dtx_eth.ipv6_addresses.add(name="dtxv6_ip")
    dtx_ipv6.address = "1100::1"
    dtx_ipv6.gateway = "1100::2"
    dtx_ipv6.prefix = 64

    dtx.isis.system_id = "640000000001"
    dtx.isis.name = "dtx_isis"

    dtx.isis.advanced.area_addresses = ["490001"]
    dtx.isis.advanced.lsp_refresh_rate = 900
    dtx.isis.advanced.enable_attached_bit = False

    dtx.isis.basic.ipv4_te_router_id = "1.1.1.1"
    dtx.isis.basic.hostname = dtx.isis.name
    dtx.isis.basic.learned_lsp_filter = True

    dtx_isis_int = dtx.isis.interfaces.add()
    dtx_isis_int.eth_name = dtx_eth.name
    dtx_isis_int.name = "dtx_isis_int"
    dtx_isis_int.network_type = dtx_isis_int.POINT_TO_POINT
    dtx_isis_int.level_type = dtx_isis_int.LEVEL_1_2

    dtx_isis_int.l2_settings.dead_interval = 30
    dtx_isis_int.l2_settings.hello_interval = 10
    dtx_isis_int.l2_settings.priority = 0

    dtx_isis_int.advanced.auto_adjust_supported_protocols = True

    dtx_isis_rr4 = dtx.isis.v4_routes.add(name="dtx_isis_rr4")
    dtx_isis_rr4.link_metric = 10
    dtx_isis_rr4.addresses.add(
        address="10.10.10.1", prefix=32, count=1, step=1
    )

    dtx_isis_rrv6 = dtx.isis.v6_routes.add(name="dtx_isis_rr6")
    dtx_isis_rrv6.addresses.add(
        address="::10:10:10:01", prefix=32, count=1, step=1
    )

    # receiver
    drx_eth = drx.ethernets.add(name="drx_eth")
    drx_eth.connection.port_name = prx.name
    drx_eth.mac = "00:00:01:01:01:02"
    drx_eth.mtu = 1500

    drx_ip = drx_eth.ipv4_addresses.add(name="drx_ip")
    drx_ip.address = "1.1.1.2"
    drx_ip.gateway = "1.1.1.1"
    drx_ip.prefix = 24
    drx_ipv6 = drx_eth.ipv6_addresses.add(name="drxv6_ip")
    drx_ipv6.address = "1100::2"
    drx_ipv6.gateway = "1100::1"
    drx_ipv6.prefix = 64

    drx.isis.system_id = "650000000001"
    drx.isis.name = "rx_isis"

    drx.isis.advanced.area_addresses = ["490001"]
    drx.isis.advanced.lsp_refresh_rate = 900
    drx.isis.advanced.enable_attached_bit = False

    drx.isis.basic.ipv4_te_router_id = "1.1.1.2"
    drx.isis.basic.hostname = drx.isis.name
    drx.isis.basic.learned_lsp_filter = True

    drx_isis_int = drx.isis.interfaces.add()
    drx_isis_int.eth_name = drx_eth.name
    drx_isis_int.name = "drx_isis_int"
    drx_isis_int.network_type = drx_isis_int.POINT_TO_POINT
    drx_isis_int.level_type = drx_isis_int.LEVEL_1_2

    drx_isis_int.l2_settings.dead_interval = 30
    drx_isis_int.l2_settings.hello_interval = 10
    drx_isis_int.l2_settings.priority = 0

    drx_isis_int.advanced.auto_adjust_supported_protocols = True

    drx_isis_rr4 = drx.isis.v4_routes.add(name="drx_isis_rr4")
    drx_isis_rr4.link_metric = 10
    drx_isis_rr4.addresses.add(
        address="20.20.20.1", prefix=32, count=1, step=1
    )

    drx_isis_rrv6 = drx.isis.v6_routes.add(name="drx_isis_rr6")
    drx_isis_rrv6.addresses.add(
        address="::20:20:20:01", prefix=32, count=1, step=1
    )

    for i in range(0, 4):
        f = b2b_raw_config.flows.add()
        f.duration.fixed_packets.packets = 100
        f.rate.pps = 50
        f.size.fixed = 128
        f.metrics.enable = True

    ftx_v4 = b2b_raw_config.flows[0]
    ftx_v4.name = "ftx_v4"
    ftx_v4.tx_rx.device.tx_names = [dtx_isis_rr4.name]
    ftx_v4.tx_rx.device.rx_names = [drx_isis_rr4.name]

    ftx_v4_eth, ftx_v4_ip, ftx_v4_tcp = ftx_v4.packet.ethernet().ipv4().tcp()
    ftx_v4_eth.src.value = dtx_eth.mac
    ftx_v4_ip.src.value = "10.10.10.1"
    ftx_v4_ip.dst.value = "20.20.20.1"
    ftx_v4_tcp.src_port.value = 5000
    ftx_v4_tcp.dst_port.value = 6000

    ftx_v6 = b2b_raw_config.flows[1]
    ftx_v6.name = "ftx_v6"
    ftx_v6.tx_rx.device.tx_names = [dtx_isis_rrv6.name]
    ftx_v6.tx_rx.device.rx_names = [drx_isis_rrv6.name]

    ftx_v6_eth, ftx_v6_ip, ftx_v6_tcp = ftx_v6.packet.ethernet().ipv6().tcp()
    ftx_v6_eth.src.value = dtx_eth.mac
    ftx_v6_ip.src.value = "::10:10:10:01"
    ftx_v6_ip.dst.value = "::20:20:20:01"
    ftx_v6_tcp.src_port.value = 5000
    ftx_v6_tcp.dst_port.value = 6000

    frx_v4 = b2b_raw_config.flows[2]
    frx_v4.name = "frx_v4"
    frx_v4.tx_rx.device.tx_names = [drx_isis_rr4.name]
    frx_v4.tx_rx.device.rx_names = [dtx_isis_rr4.name]

    frx_v4_eth, frx_v4_ip, frx_v4_tcp = frx_v4.packet.ethernet().ipv4().tcp()
    frx_v4_eth.src.value = drx_eth.mac
    frx_v4_ip.src.value = "20.20.20.1"
    frx_v4_ip.dst.value = "10.10.10.1"
    frx_v4_tcp.src_port.value = 5000
    frx_v4_tcp.dst_port.value = 6000

    frx_v6 = b2b_raw_config.flows[3]
    frx_v6.name = "frx_v6"
    frx_v6.tx_rx.device.tx_names = [drx_isis_rrv6.name]
    frx_v6.tx_rx.device.rx_names = [dtx_isis_rrv6.name]

    frx_v6_eth, frx_v6_ip, frx_v6_tcp = frx_v6.packet.ethernet().ipv6().tcp()
    frx_v6_eth.src.value = drx_eth.mac
    frx_v6_ip.src.value = "::20:20:20:01"
    frx_v6_ip.dst.value = "::10:10:10:01"
    frx_v6_tcp.src_port.value = 5000
    frx_v6_tcp.dst_port.value = 6000

    api.set_config(b2b_raw_config)

    api.start_protocols()

    time.sleep(30)

    api.start_transmit()

    time.sleep(30)