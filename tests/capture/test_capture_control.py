import pytest
import dpkt


def test_capture_control(api, utils):
    """
    The test is to check if capture has control packets included.

    Validation: packet captures should have bgp packets
    """
    config = api.config()

    tx, rx = config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    config.options.port_options.location_preemption = True
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [tx.name, rx.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    cap = config.captures.capture(name="c1")[-1]
    cap.port_names = [rx.name]
    cap.format = cap.PCAP

    tx_device, rx_device = config.devices.device(name="d1").device(name="d2")

    # tx_device config
    tx_eth = tx_device.ethernets.add()
    tx_eth.port_name = tx.name
    tx_eth.name = "tx_eth"
    tx_eth.mac = "00:00:00:00:00:aa"
    tx_ipv4 = tx_eth.ipv4_addresses.add()
    tx_ipv4.name = "tx_ipv4"
    tx_ipv4.address = "21.1.1.2"
    tx_ipv4.prefix = 24
    tx_ipv4.gateway = "21.1.1.1"
    tx_bgpv4 = tx_device.bgp
    tx_bgpv4.router_id = "192.0.0.1"
    tx_bgpv4_int = tx_bgpv4.ipv4_interfaces.add()
    tx_bgpv4_int.ipv4_name = tx_ipv4.name
    tx_bgpv4_peer = tx_bgpv4_int.peers.add()
    tx_bgpv4_peer.name = "tx_bgpv4"
    tx_bgpv4_peer.as_type = "ebgp"
    tx_bgpv4_peer.peer_address = "21.1.1.1"
    tx_bgpv4_peer.as_number = 65201

    # rx_device config
    rx_eth = rx_device.ethernets.add()
    rx_eth.port_name = rx.name
    rx_eth.name = "rx_eth"
    rx_eth.mac = "00:00:00:00:00:bb"
    rx_ipv4 = rx_eth.ipv4_addresses.add()
    rx_ipv4.name = "rx_ipv4"
    rx_ipv4.address = "21.1.1.1"
    rx_ipv4.prefix = 24
    rx_ipv4.gateway = "21.1.1.2"
    rx_bgpv4 = rx_device.bgp
    rx_bgpv4.router_id = "192.0.0.2"
    rx_bgpv4_int = rx_bgpv4.ipv4_interfaces.add()
    rx_bgpv4_int.ipv4_name = rx_ipv4.name
    rx_bgpv4_peer = rx_bgpv4_int.peers.add()
    rx_bgpv4_peer.name = "rx_bgpv4"
    rx_bgpv4_peer.as_type = "ebgp"
    rx_bgpv4_peer.peer_address = "21.1.1.2"
    rx_bgpv4_peer.as_number = 65200

    # flow config
    flow = config.flows.flow(name="flow1")[-1]
    flow.tx_rx.device.tx_names = [tx_device.name]
    flow.tx_rx.device.rx_names = [rx_device.name]

    flow.size.fixed = 1024
    flow.rate.percentage = 10
    flow.duration.fixed_packets.packets = 10
    flow.metrics.enable = True

    utils.start_traffic(api, config)

    request = api.capture_request()
    request.port_name = "rx"
    pcap_bytes = api.get_capture(request)

    bgp_pkts = []
    for _, pkt in dpkt.pcap.Reader(pcap_bytes):
        eth = dpkt.ethernet.Ethernet(pkt)
        if getattr(eth.data, "tcp", None) is not None:
            if eth.data.tcp.sport == 179:
                bgp_pkts.append(eth.data)

    print(len(bgp_pkts))
    assert len(bgp_pkts) > 0


if __name__ == "__main__":
    pytest.main(["-s", __file__])
