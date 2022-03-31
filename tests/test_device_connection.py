def test_port_name(api, utils):
    config = api.config()
    p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    d1 = config.devices.device(name="d1")[-1]
    eth1 = d1.ethernets.ethernet()[-1]
    eth1.port_name = p1.name
    eth1.name = "eth1"
    eth1.mac = "00:01:00:00:00:01"
    api.set_config(config)


def test_connection_portname(api, utils):
    config = api.config()
    api.set_config(config)
    p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    d1 = config.devices.device(name="d1")[-1]
    eth1 = d1.ethernets.ethernet()[-1]
    eth1.connection.port_name = p1.name
    eth1.name = "eth1"
    eth1.mac = "00:01:00:00:00:01"
    api.set_config(config)


def test_device_connection(api, utils):
    """
    Test when both port_name and connection.port_name is set in the config
    """
    config = api.config()
    p1, p2 = config.ports.port(
        name="p1", location=utils.settings.ports[0]
    ).port(name="p2", location=utils.settings.ports[1])
    d1 = config.devices.device(name="d1")[-1]
    eth1 = d1.ethernets.ethernet()[-1]
    eth1.port_name = p2.name
    eth1.connection.port_name = p1.name
    eth1.name = "eth1"
    eth1.mac = "00:01:00:00:00:01"
    api.set_config(config)


def test_device_lag_name(api, utils):
    config = api.config()
    p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
    lag1 = config.lags.lag(name="lag-1")[-1]
    lp1 = lag1.ports.port(port_name=p1.name)[-1]
    lp1.protocol.static.lag_id = 1
    lp1.ethernet.name = "lp1-e"
    lp1.ethernet.mac = "aa:aa:aa:aa:aa:aa"
    d1 = config.devices.device(name="d1")[-1]
    eth1 = d1.ethernets.ethernet()[-1]
    eth1.connection.lag_name = lag1.name
    eth1.name = "eth1"
    eth1.mac = "00:01:00:00:00:02"
    api.set_config(config)
