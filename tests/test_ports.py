def test_ports(api, utils):
    """Demonstrates adding ports to a configuration and setting the
    configuration on the traffic generator.
    The traffic generator should have no  items configured other than
    the ports in this test.
    """
    tx_port = utils.settings.ports[0]
    rx_port = utils.settings.ports[1]
    config = api.config()
    config.ports.port(name="tx_port", location=tx_port).port(
        name="rx_port", location=rx_port
    ).port(name="port with no location")
    config.options.port_options.location_preemption = True
    api.set_config(config)
    config = api.config()
    api.set_config(config)
