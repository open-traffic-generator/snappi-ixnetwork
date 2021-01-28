import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_layer1_flow_control_8021qbb(api, tx_port, rx_port, options, utils):
    """
    Test that layer1 flow control 8021qbb configuration settings
    are being applied correctly.

    Validation: Validate the layer1 8021qbb properties applied using Restpy
    """
    port1_delay = 3
    port1_pfc_priority_groups = [1, 0, -1, -1, 7, -1, -1, -1]
    directed_address = '01 80 C2 00 00 01'

    enabled_pfc = Ieee8021qbb(pfc_delay=3,
                              pfc_class_0=port1_pfc_priority_groups[0],
                              pfc_class_1=port1_pfc_priority_groups[1],
                              pfc_class_4=port1_pfc_priority_groups[4])
    fcoe1 = Layer1(name='enabled pfc delay',
                   port_names=[tx_port.name],
                   speed=utils.settings.speed,
                   auto_negotiate=True,
                   media=utils.settings.media,
                   flow_control=FlowControl(directed_address=directed_address,
                                            choice=enabled_pfc))

    disabled_pfc = Ieee8021qbb(pfc_delay=0)
    fcoe2 = Layer1(name='disabled pfc delay',
                   port_names=[rx_port.name],
                   auto_negotiate=True,
                   speed=utils.settings.speed,
                   media=utils.settings.media,
                   flow_control=FlowControl(directed_address=directed_address,
                                            choice=disabled_pfc))

    config = Config(ports=[tx_port, rx_port],
                    layer1=[fcoe1, fcoe2],
                    options=options)
    api.set_state(State(ConfigState(config=config, state='set')))
    validate_8021qbb_config(api,
                            port1_delay,
                            port1_pfc_priority_groups,
                            directed_address)


def validate_8021qbb_config(api,
                            port1_delay,
                            port1_pfc_priority_groups,
                            directed_address):
    """
    Validate 8021qbb config using Restpy
    """
    ixnetwork = api._ixnetwork
    port1 = ixnetwork.Vport.find()[0]
    port2 = ixnetwork.Vport.find()[1]
    type = port1.Type.replace('Fcoe', '')
    type = type[0].upper() + type[1:]
    assert getattr(port1.L1Config, type).FlowControlDirectedAddress \
        == directed_address
    assert getattr(port1.L1Config, type).Fcoe.PfcPauseDelay \
        == port1_delay
    assert getattr(port1.L1Config, type).Fcoe.PfcPriorityGroups  \
        == port1_pfc_priority_groups
    assert getattr(port2.L1Config, type).Fcoe.EnablePFCPauseDelay \
        is False
