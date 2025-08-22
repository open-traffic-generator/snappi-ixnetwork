import pytest
import time

@pytest.mark.skip(reason="Not implemented")
def test_rsvp_traffic(api, b2b_raw_config, utils):
    """Test rsvp traffic
    - set_config
    - start protocols
    - verify rsvp metrics
    - start traffic
    - verify flow metrics
    - verify capture
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
    p1d1_eth.mac = "00:00:01:00:00:01"
    p1d1_eth.mtu = 1500

    p2d1_eth.connection.port_name = p2.name
    p2d1_eth.name = "p2d1_eth"
    p2d1_eth.mac = "00:00:02:00:00:01"
    p2d1_eth.mtu = 1500

    # port 1 device 1 ipv4
    p1d1_ipv4 = p1d1_eth.ipv4_addresses.add()
    p1d1_ipv4.address = "100.1.0.1"
    p1d1_ipv4.gateway = "100.1.0.11"
    p1d1_ipv4.name = "p1d1_ipv4"
    p1d1_ipv4.prefix = 24

    # port 1 device 1 rsvp 1
    rsvp1 = p1d1.rsvp
    rsvp1.name = "p1_rsvp"
    rsvpIf1 = rsvp1.ipv4_interfaces.add()
    rsvpIf1.ipv4_name = "p1d1_ipv4"
    rsvpIf1.neighbor_ip = "100.1.0.11"
    rsvp1_lsp_intf = rsvp1.lsp_ipv4_interfaces.add()
    rsvp1_lsp_intf.ipv4_name = "p1d1_ipv4"
    egress_lsp = rsvp1_lsp_intf.p2p_egress_ipv4_lsps
    egress_lsp.name = "egress1"

    # port 2 device 1 ipv4
    p2d1_ipv4 = p2d1_eth.ipv4_addresses.add()
    p2d1_ipv4.address = "100.1.0.11"
    p2d1_ipv4.gateway = "100.1.0.1"
    p2d1_ipv4.name = "p2d1_ipv4"
    p2d1_ipv4.prefix = 24

    # port 2 device 1 rsvp 1
    rsvp2 = p2d1.rsvp
    rsvp2.name = "p2_rsvp"
    rsvpIf2 = rsvp2.ipv4_interfaces.add()
    rsvpIf2.ipv4_name = "p2d1_ipv4"
    rsvpIf2.neighbor_ip = "100.1.0.1"
    rsvp2_lsp_intf = rsvp2.lsp_ipv4_interfaces.add()
    rsvp2_lsp_intf.ipv4_name = "p2d1_ipv4"
    ing_lsp1 = rsvp2_lsp_intf.p2p_ingress_ipv4_lsps.add()
    ing_lsp1.name = "ingress1"
    ing_lsp1.remote_address = "100.1.0.1"
    ing_lsp1.tunnel_id = 1
    ing_lsp2 = rsvp2_lsp_intf.p2p_ingress_ipv4_lsps.add()
    ing_lsp2.name = "ingress2"
    ing_lsp2.remote_address = "100.1.0.1"
    ing_lsp2.tunnel_id = 2
    ing_lsp3 = rsvp2_lsp_intf.p2p_ingress_ipv4_lsps.add()
    ing_lsp3.name = "ingress3"
    ing_lsp3.remote_address = "100.1.0.1"
    ing_lsp3.tunnel_id = 3
    ing_lsp4 = rsvp2_lsp_intf.p2p_ingress_ipv4_lsps.add()
    ing_lsp4.name = "ingress4"
    ing_lsp4.remote_address = "100.1.0.1"
    ing_lsp4.tunnel_id = 4
    ing_lsp5 = rsvp2_lsp_intf.p2p_ingress_ipv4_lsps.add()
    ing_lsp5.name = "ingress5"
    ing_lsp5.remote_address = "100.1.0.1"
    ing_lsp5.tunnel_id = 5
    ing_lsp6 = rsvp2_lsp_intf.p2p_ingress_ipv4_lsps.add()
    ing_lsp6.name = "ingress6"
    ing_lsp6.remote_address = "100.1.0.1"
    ing_lsp6.tunnel_id = 6

    # Flow
    f1 = b2b_raw_config.flows.add(name="f1")
    f1.tx_rx.device.tx_names = [ing_lsp2.name]
    f1.tx_rx.device.rx_names = [egress_lsp.name]
    f1.size.fixed = 128
    f1.rate.pps = 1000
    f1.duration.fixed_packets.packets = 1
    f1.metrics.enable = True
    f1_eth_pkt, f1_mpls_pkt, f1_ip_pkt = f1.packet.ethernet().mpls().ipv4()
    f1_eth_pkt.src.value = p2d1_eth.mac
    f1_eth_pkt.dst.choice = "auto"
    f1_mpls_pkt.label.choice = "auto"
    f1_ip_pkt.src.value = p2d1_ipv4.address
    f1_ip_pkt.dst.value = p1d1_ipv4.address

    f2 = b2b_raw_config.flows.add(name="f2")
    f2.tx_rx.device.tx_names = [ing_lsp5.name]
    f2.tx_rx.device.rx_names = [egress_lsp.name]
    f2.size.fixed = 128
    f2.rate.pps = 1000
    f2.duration.fixed_packets.packets = 1
    f2.metrics.enable = True
    f2_eth_pkt, f2_mpls_pkt, f2_ip_pkt = f2.packet.ethernet().mpls().ipv4()
    f2_eth_pkt.src.value = p2d1_eth.mac
    f2_eth_pkt.dst.value = p1d1_eth.mac
    f2_ip_pkt.src.value = p2d1_ipv4.address
    f2_ip_pkt.dst.value = p1d1_ipv4.address

    api.set_config(b2b_raw_config)


