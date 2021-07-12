def test_pretest(api, utils):
    """
    This test does 2 things
    1) Restore ports to factory defaults and keep them ready for tests
    2) Remove any previous stale sessions in API server

    """
    config = api.config()

    for i in range(len(utils.settings.ports)):
        config.ports.port(name="port%d" % i, location=utils.settings.ports[i])[
            -1
        ]

    config.options.port_options.location_preemption = True
    api.set_config(config)

    # ports cleanup
    api._ixnetwork.Vport.find().ResetPortCpuAndFactoryDefault()

    # remove stale sessions
    for session in api.assistant.TestPlatform.Sessions.find():
        if session.Id != api.assistant.Session.Id:
            session.remove()
