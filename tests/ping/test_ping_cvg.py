import pytest


def test_ping_cvg(api, utils):
    """
    Demonstrates test to send ipv4 and ipv6 pings

    Return the ping responses and validate as per user's expectation
    """
    conv_config = api.config()
    port1, port2 = conv_config.ports.port(
        name="tx", location=utils.settings.ports[0]
    ).port(name="rx", location=utils.settings.ports[1])

    conv_config.options.port_options.location_preemption = True
    ly = conv_config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port1.name, port2.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    d1, d2 = conv_config.devices.device(name="tx_bgp").device(name="rx_bgp")
    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = port1.name, port2.name   # noqa
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

    api.set_config(conv_config)

    print("Starting all protocols ...")
    ps = api.control_state()
    ps.choice = ps.PROTOCOL
    ps.protocol.choice = ps.protocol.ALL
    ps.protocol.all.state = ps.protocol.all.START
    res = api.set_control_state(ps)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    cs = api.control_state()
    cs.choice = cs.TRAFFIC
    cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
    cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
    res = api.set_control_state(cs)
    if len(res.warnings) > 0:
        print("Warnings: {}".format(res.warnings))

    try:
        cs = api.control_action()
        cs.protocol.ipv4.ping.requests.add(src_name=ip1.name, dst_ip="10.1.1.2")
        cs.protocol.ipv4.ping.requests.add(src_name=ip1.name, dst_ip="10.1.1.3")

        responses = api.set_control_action(
            cs
        ).response.protocol.ipv4.ping.responses
        for resp in responses:
            if resp.src_name == ip1.name and resp.dst_ip == "10.1.1.2":
                assert resp.result == "succeeded"
            elif resp.src_name == ip1.name and resp.dst_ip == "10.1.1.3":
                assert resp.result == "failed"
            elif resp.src_name == ipv62.name and resp.dst_ip == "3000::1":
                assert resp.result == "succeeded"
            elif resp.src_name == ipv62.name and resp.dst_ip == "3000::9":
                assert resp.result == "failed"
        cs = api.control_state()
        cs.choice = cs.TRAFFIC
        cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
        res = api.set_control_state(cs)
        if len(res.warnings) > 0:
            print("Warnings: {}".format(res.warnings))
    except Exception as e:
        cs = api.control_state()
        cs.choice = cs.TRAFFIC
        cs.traffic.choice = cs.traffic.FLOW_TRANSMIT
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
        res = api.set_control_state(cs)
        if len(res.warnings) > 0:
            print("Warnings: {}".format(res.warnings))
        raise Exception(e)
