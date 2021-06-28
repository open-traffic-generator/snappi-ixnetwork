def test_layer1_flow_control_8021qbb(api, utils):
    """
    Test that layer1 flow control 8021qbb configuration settings
    are being applied correctly.

    Validation: Validate the layer1 8021qbb properties applied using Restpy
    """
    port1_delay = 3
    port1_pfc_priority_groups = [1, 0, 2, 3, 7, 5, 6, 7]
    directed_address = "01 80 C2 00 00 01"
    config = api.config()
    config.ports.port().port()
    tx_port = config.ports[0]
    rx_port = config.ports[1]
    tx_port.name = "Tx port"
    tx_port.location = utils.settings.ports[0]
    rx_port.location = utils.settings.ports[1]
    rx_port.name = "Rx port"
    config.layer1.layer1().layer1()
    fcoe1 = config.layer1[0]
    fcoe2 = config.layer1[1]
    fcoe1.name = "enabled pfc delay"
    fcoe1.port_names = [tx_port.name]
    fcoe1.speed = utils.settings.speed
    fcoe1.auto_negotiate = True
    fcoe1.media = utils.settings.media
    fcoe1.flow_control.directed_address = directed_address
    fcoe1.flow_control.ieee_802_1qbb.pfc_delay = 3
    fcoe1.flow_control.ieee_802_1qbb.pfc_class_0 = port1_pfc_priority_groups[0]
    fcoe1.flow_control.ieee_802_1qbb.pfc_class_1 = port1_pfc_priority_groups[1]
    fcoe1.flow_control.ieee_802_1qbb.pfc_class_4 = port1_pfc_priority_groups[4]
    fcoe2.name = "disabled pfc delay"
    fcoe2.port_names = [rx_port.name]
    fcoe2.speed = utils.settings.speed
    fcoe2.auto_negotiate = True
    fcoe2.media = utils.settings.media
    fcoe2.flow_control.directed_address = directed_address
    fcoe2.flow_control.ieee_802_1qbb.pfc_delay = 0
    api.set_config(config)
    validate_8021qbb_config(
        api, port1_delay, port1_pfc_priority_groups, directed_address
    )


def validate_8021qbb_config(
    api, port1_delay, port1_pfc_priority_groups, directed_address
):
    """
    Validate 8021qbb config using Restpy
    """
    ixnetwork = api._ixnetwork
    port1 = ixnetwork.Vport.find()[0]
    port2 = ixnetwork.Vport.find()[1]
    type = port1.Type.replace("Fcoe", "")
    type = type[0].upper() + type[1:]
    assert (
        getattr(port1.L1Config, type).FlowControlDirectedAddress
        == directed_address
    )
    assert getattr(port1.L1Config, type).Fcoe.PfcPauseDelay == port1_delay
    assert (
        getattr(port1.L1Config, type).Fcoe.PfcPriorityGroups
        == port1_pfc_priority_groups
    )
    assert getattr(port2.L1Config, type).Fcoe.EnablePFCPauseDelay is False
