
import time
import dpkt

def test_icmpv6_packets(api, b2b_raw_config, utils):
    """
    Configure raw ICMPv6 flows with:
    - fixed pattern for all ICMPv6 fields
    Validate using utils.validate_config.
    """

    no_of_packets = 1
    
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

    # IPv6 addresses
    ip1 = eth1.ipv6_addresses.add()
    ip1.name = "ipv61"
    ip1.address = "2001:db8::1"
    ip1.gateway = "2001:db8::2"

    ip2 = eth2.ipv6_addresses.add()
    ip2.name = "ipv62"
    ip2.address = "2001:db8::2"
    ip2.gateway = "2001:db8::1"

    icmpv6_type = 128
    icmpv6_code = 0
    icmpv6_checksum = 1234
    icmpv6_identifier = 1
    icmpv6_seq_num = 256

    flow = b2b_raw_config.flows.flow(name="f1")[-1]
    flow.tx_rx.device.tx_names = [ip1.name]
    flow.tx_rx.device.rx_names = [ip2.name]
    flow.rate.pps = 1000
    flow.duration.fixed_packets.packets = no_of_packets
    flow.metrics.enable = True

    eth, ip, icmpv6 = flow.packet.ethernet().ipv6().icmpv6()
    icmpv6_echo = icmpv6.echo

    icmpv6_echo.type.value = icmpv6_type
    icmpv6_echo.code.value = icmpv6_code
    icmpv6_echo.checksum.custom = icmpv6_checksum
    icmpv6_echo.identifier.value = icmpv6_identifier
    icmpv6_echo.sequence_number.value = icmpv6_seq_num

    api.set_config(b2b_raw_config)

    utils.start_traffic(api, b2b_raw_config, start_capture=True)
    time.sleep(10)
    utils.stop_traffic(api, b2b_raw_config, stop_capture=True)

    captures_ok(api, b2b_raw_config, utils, no_of_packets, config.ports[1].name, icmpv6_echo)


def captures_ok(api, cfg, utils, packets, name, icmpv6_echo):
    pkt_count = 0

    request = api.capture_request()
    request.port_name = name
    pcap_bytes = api.get_capture(request)

    for _, pkt in dpkt.pcapng.Reader(pcap_bytes):
        eth = dpkt.ethernet.Ethernet(pkt)

        if isinstance(eth.data, dpkt.ip6.IP6):
            ip6 = eth.data

            if isinstance(ip6.data, dpkt.icmp6.ICMP6):
                icmp6 = ip6.data

                if icmp6.type == 143:
                    continue
                
                assert icmp6.type == icmpv6_echo.type.value
                assert icmp6.code == icmpv6_echo.code.value
                assert format(icmp6.sum, "x") == str(icmpv6_echo.checksum.custom)

                if icmp6.type in (128, 129):
                    echo = icmp6.data
                    assert echo.id == icmpv6_echo.identifier.value
                    assert echo.seq == icmpv6_echo.sequence_number.value

                pkt_count += 1
                
    assert pkt_count == packets
