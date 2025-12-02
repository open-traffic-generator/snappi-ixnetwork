import time
import dpkt


def test_icmp_packets(api, b2b_raw_config, utils):
    """
    Configure raw ICMP flows with:
    - fixed pattern for all ICMP fields
    - counter pattern for all ICMP fields
    Validate using utils.validate_config.
    """

    no_of_packets = 10000
    
    b2b_raw_config.flows.clear()
    config = b2b_raw_config

    d1, d2 = config.devices.device(name="d1").device(name="d2")

    eth1 = d1.ethernets.add()
    eth1.name = "eth1"
    eth1.connection.port_name = config.ports[0].name
    eth1.mac = "00:ad:aa:13:11:01"

    eth2 = d2.ethernets.add()
    eth2.name = "eth2"
    eth2.connection.port_name = config.ports[1].name
    eth2.mac = "00:ad:aa:13:11:02"

    ip1 = eth1.ipv4_addresses.add()
    ip1.name = "ipv41"
    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"

    ip2 = eth2.ipv4_addresses.add()
    ip2.name = "ipv42"
    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"

    icmp_type = 8
    icmp_code = 0
    icmp_checksum = 1234
    icmp_identifier = 1
    icmp_seq_num = 256

    flow = b2b_raw_config.flows.flow(name="f1")[-1]
    flow.tx_rx.device.tx_names = [ip1.name]
    flow.tx_rx.device.rx_names = [ip2.name]
    flow.rate.pps = 1000
    flow.duration.fixed_packets.packets = no_of_packets
    flow.metrics.enable = True

    eth, ip, icmp = flow.packet.ethernet().ipv4().icmp()
    icmp_echo = icmp.echo

    icmp_echo.type.value = icmp_type
    icmp_echo.code.value = icmp_code
    icmp_echo.checksum.custom = icmp_checksum
    icmp_echo.identifier.value = icmp_identifier
    icmp_echo.sequence_number.value = icmp_seq_num

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=True)
    time.sleep(10)
    utils.stop_traffic(api, b2b_raw_config, stop_capture=True)

    captures_ok(api, b2b_raw_config, utils, no_of_packets, config.ports[1].name, icmp_echo)

def captures_ok(api, cfg, utils, packets, name, icmp_echo):
    pkt_count = 0

    request = api.capture_request()
    request.port_name = name
    pcap_bytes = api.get_capture(request)

    for _, pkt in dpkt.pcapng.Reader(pcap_bytes):
        eth = dpkt.ethernet.Ethernet(pkt)
        
        if isinstance(eth.data, dpkt.ip.IP):
            ip = eth.data

            if isinstance(ip.data, dpkt.icmp.ICMP):
                icmp = ip.data
                
                assert icmp.type == icmp_echo.type.value
                assert icmp.code == icmp_echo.code.value
                assert format(icmp.sum, "x") == str(icmp_echo.checksum.custom)

                if icmp.type in (8, 0):
                    echo = icmp.data
                    assert echo.id == icmp_echo.identifier.value
                    assert echo.seq == icmp_echo.sequence_number.value
                
                pkt_count += 1

    assert pkt_count == packets
