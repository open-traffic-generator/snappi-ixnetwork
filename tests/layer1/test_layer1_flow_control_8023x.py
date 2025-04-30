@pytest.mark.skip(
    reason="CI-Testing"
)
def test_layer1_flow_control_8023x(api, utils):
    """
    Test that layer1 flow controle 8023x configuration settings
    are being applied correctly.

    Validation: Validate the layer1 properties applied using Restpy
    """

    directed_address = "01:80:C2:00:00:02"

    config = api.config()
    config.ports.port().port()
    tx_port, rx_port = config.ports[0], config.ports[1]
    tx_port.name, rx_port.name = "Tx port", "Rx port"
    tx_port.location = utils.settings.ports[0]
    rx_port.location = utils.settings.ports[1]

    config.layer1.layer1().layer1()
    fcoe1, fcoe2 = config.layer1[0], config.layer1[1]
    fcoe1.name, fcoe2.name = "pfc delay-1", "pfc delay-2"
    fcoe1.port_names, fcoe2.port_names = [tx_port.name], [rx_port.name]
    fcoe1.speed, fcoe2.speed = utils.settings.speed, utils.settings.speed
    fcoe1.auto_negotiate, fcoe2.auto_negotiate = True, True
    fcoe1.media, fcoe2.media = utils.settings.media, utils.settings.media
    fcoe1.flow_control.directed_address = directed_address
    fcoe2.flow_control.directed_address = directed_address
    fcoe1.flow_control.choice = "ieee_802_3x"
    fcoe2.flow_control.choice = "ieee_802_3x"
    api.set_config(config)
    validate_8023x_config(api)


def validate_8023x_config(api):
    """
    Validate 8023x config using Restpy
    """
    ixnetwork = api._ixnetwork
    port1 = ixnetwork.Vport.find()[0]
    port2 = ixnetwork.Vport.find()[1]
    type = port1.Type.replace("Fcoe", "")
    type = type[0].upper() + type[1:]
    assert (
        getattr(port1.L1Config, type).FlowControlDirectedAddress
        == "0180C2000002"
    )
    assert getattr(port1.L1Config, type).Fcoe.FlowControlType == "ieee802.3x"
    assert getattr(port2.L1Config, type).Fcoe.FlowControlType == "ieee802.3x"
