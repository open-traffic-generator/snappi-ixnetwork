import pytest


@pytest.mark.skip(
    reason="""
    Skipping as this test as starting the protcols,
    might cause an issue in CI/CD
    """
)
def test_bgp_speaker(api, b2b_raw_config):
    """This is the configuration steps in https://github.com/Azure/sonic-mgmt/blob/master/tests/bgp/test_bgp_speaker.py

    logging.info("Start exabgp on ptf")
    for i in range(0, 3):
        local_ip = str(speaker_ips[i].ip)
        ptfhost.exabgp(name="bgps%d" % i,
                       state="started",
                       local_ip=local_ip,
                       router_id=local_ip,
                       peer_ip=lo_addr,
                       local_asn=bgp_speaker_asn,
                       peer_asn=mg_facts['minigraph_bgp_asn'],
                       port=str(port_num[i]))
    """
    local_ip = ["10.10.0.1", "20.20.0.1", "30.30.0.1"]
    local_asn = "65000"
    peer_asn = "65000"

    dev = b2b_raw_config.devices.device()[-1]
    dev.name = "BGP device"
    dev.container_name = b2b_raw_config.ports[0].name
    eth = dev.ethernet
    ipv4 = eth.ipv4
    ipv4.name = "ipv4"
    ipv4.address.values = local_ip
    ipv4.gateway.value = peer_ip
    bgpv4 = ipv4.bgpv4
    bgpv4.name = "bgpv4"
    bgpv4.router_id.values, bgpv4.dut_ipv4_address.value = local_ip, peer_ip
    bgpv4.as_number.value, bgpv4.dut_as_number.value = local_asn, peer_asn
    b2b_raw_config.flows.clear()
    api.set_config(b2b_raw_config)
    transmit_state = api.transmit_state()
    transmit_state.state = "start"
    api.set_transmit_state(transmit_state)
    import time

    time.sleep(5)
    transmit_state.state = "stop"
    api.set_transmit_state(transmit_state)
