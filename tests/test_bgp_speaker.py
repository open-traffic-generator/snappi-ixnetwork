def test_bgp_speaker(api, utils):
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
    local_ip = ['10.10.0.1', '20.20.0.1', '30.30.0.1']
    local_asn = '65000'

    config = api.config()
    port1, = config.ports.port(name='port1',
                               location=utils.settings.ports[0])

    device1,  = (
        config.
        devices.device(name="device1", container_name=port1.name)
    )
    # device1_device config
    device1_eth = device1.ethernet
    device1_eth.name = "device1_eth"
    device1_ipv4 = device1_eth.ipv4
    device1_ipv4.name = "device1_ipv4"
    device1_ipv4.address.value = "22.1.1.2"
    device1_ipv4.prefix.value = "24"
    device1_ipv4.gateway.value = "22.1.1.1"
    device1_bgpv4 = device1_ipv4.bgpv4
    device1_bgpv4.name = "device1_bgpv4"
    device1_bgpv4.as_type = "ebgp"
    device1_bgpv4.dut_ipv4_address.values = local_ip
    device1_bgpv4.as_number.value = local_asn

    response = api.set_config(config)
    assert(len(response.errors)) == 0
