import pytest
import time


def test_ping(api, b2b_raw_config):
    """
    Demonstrates test to send ipv4 and ipv6 pings

    Return the ping responses and validate as per user's expectation
    """
    port1, port2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="tx_bgp").device(name="rx_bgp")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.port_name, eth2.port_name = port1.name, port2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ipv61, ipv62 = eth1.ipv6_addresses.add(), eth2.ipv6_addresses.add()
    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"
    ipv61.name, ipv62.name = "ipv6-1", "ipv6-2"

    ip1.address = "10.1.1.1"
    ip1.gateway = "10.1.1.2"
    ip1.prefix = 24

    ip2.address = "10.1.1.2"
    ip2.gateway = "10.1.1.1"
    ip2.prefix = 24

    ipv61.address = "3000::1"
    ipv61.gateway = "3000::2"
    ipv61.prefix = 64

    ipv62.address = "3000::2"
    ipv62.gateway = "3000::1"
    ipv62.prefix = 64

    api.set_config(b2b_raw_config)

    # Check for ARP status to be resolved
    req = api.states_request()
    req.ipv4_neighbors.ethernet_names = ["eth1", "eth2"]

    retry_count = 1
    while True:
        v4_link_layer_address = []
        states = api.get_states(req)
        for state in states.ipv4_neighbors:
            if state.link_layer_address:
                v4_link_layer_address.append(state.link_layer_address)
        if (
            len(states.ipv4_neighbors) == len(v4_link_layer_address)
            and len(states.ipv4_neighbors) > 0
        ):
            print("Arp is resolved")
            break
        elif retry_count == 10:
            raise Exception("ARP didn't resolve in specified time")
        else:
            time.sleep(1)
            retry_count = retry_count + 1

    req.ipv6_neighbors.ethernet_names = ["eth1", "eth2"]
    retry_count = 1
    while True:
        v6_link_layer_address = []
        states = api.get_states(req)
        for state in states.ipv6_neighbors:
            if state.link_layer_address:
                v6_link_layer_address.append(state.link_layer_address)
        if (
            len(states.ipv6_neighbors) == len(v6_link_layer_address)
            and len(states.ipv6_neighbors) > 0
        ):
            print("Gateway MACs resolved")
            break
        elif retry_count == 10:
            raise Exception("Gateway MAC is not resolved")
        else:
            time.sleep(1)
            retry_count = retry_count + 1

    # Ping Requests once ARP is resolved
    req = api.ping_request()
    p1, p2, p3, p4 = req.endpoints.ipv4().ipv4().ipv6().ipv6()
    p1.src_name = ip1.name
    p1.dst_ip = "10.1.1.2"
    p2.src_name = ip1.name
    p2.dst_ip = "10.1.1.3"
    p3.src_name = ipv62.name
    p3.dst_ip = "3000::1"
    p4.src_name = ipv62.name
    p4.dst_ip = "3000::9"

    responses = api.send_ping(req).responses
    for resp in responses:
        if resp.src_name == ip1.name and resp.dst_ip == "10.1.1.2":
            assert resp.result == "success"
        elif resp.src_name == ip1.name and resp.dst_ip == "10.1.1.3":
            assert resp.result == "failure"
        elif resp.src_name == ipv62.name and resp.dst_ip == "3000::1":
            assert resp.result == "success"
        elif resp.src_name == ipv62.name and resp.dst_ip == "3000::9":
            assert resp.result == "failure"


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
