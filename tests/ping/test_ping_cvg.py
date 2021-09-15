def test_ping_cvg(cvg_api, utils):
    """
    Demonstrates test to send ipv4 and ipv6 pings

    Return the ping responses and validate as per user's expectation
    """
    conv_config = cvg_api.convergence_config()
    config = conv_config.config
    port1, port2 = config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    config.options.port_options.location_preemption = True
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port1.name, port2.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    d1, d2 = config.devices.device(
        name="tx_bgp").device(name="rx_bgp")
    d1.container_name, d2.container_name = port1.name, port2.name
    eth1, eth2 = d1.ethernet, d2.ethernet
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4, eth2.ipv4
    ipv61, ipv62 = eth1.ipv6, eth2.ipv6
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

    cvg_api.set_config(conv_config)

    cs = cvg_api.convergence_state()
    cs.transmit.state = cs.transmit.START
    cvg_api.set_state(cs)

    try:
        req = cvg_api.ping_request()
        p1, p2, p3, p4 = req.endpoints.ipv4().ipv4().ipv6().ipv6()
        p1.src_name = ip1.name
        p1.dst_ip = "10.1.1.2"
        p2.src_name = ip1.name
        p2.dst_ip = "10.1.1.3"
        p3.src_name = ipv62.name
        p3.dst_ip = "3000::1"
        p4.src_name = ipv62.name
        p4.dst_ip = "3000::9"

        responses = cvg_api.send_ping(req).responses
        for resp in responses:
            if resp.src_name == ip1.name and resp.dst_ip == "10.1.1.2":
                assert resp.result == "success"
            elif resp.src_name == ip1.name and resp.dst_ip == "10.1.1.3":
                assert resp.result == "failure"
            elif resp.src_name == ipv62.name and resp.dst_ip == "3000::1":
                assert resp.result == "success"
            elif resp.src_name == ipv62.name and resp.dst_ip == "3000::9":
                assert resp.result == "failure"
        cs = cvg_api.convergence_state()
        cs.transmit.state = cs.transmit.STOP
        cvg_api.set_state(cs)
    except Exception as e:
        cs = cvg_api.convergence_state()
        cs.transmit.state = cs.transmit.STOP
        cvg_api.set_state(cs)
        raise Exception(e)
