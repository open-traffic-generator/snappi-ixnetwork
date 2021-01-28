import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_layer1_fcoe(serializer, api, tx_port, rx_port, options):
    """Test that layer1 fcoe configuration settings are being applied correctly.
    """
    enabled_pfc = Ieee8021qbb(pfc_delay=3,
                              pfc_class_0=1,
                              pfc_class_1=0,
                              pfc_class_4=7)
    fcoe1 = Layer1(name='enabled pfc delay',
                   port_names=[tx_port.name],
                   auto_negotiate=True,
                   flow_control=FlowControl(directed_address='0180C2000001',
                                            choice=enabled_pfc))

    disabled_pfc = Ieee8021qbb(pfc_delay=0)
    fcoe2 = Layer1(name='disabled pfc delay',
                   port_names=[rx_port.name],
                   auto_negotiate=True,
                   flow_control=FlowControl(directed_address='0180C2000001',
                                            choice=disabled_pfc))

    config = Config(ports=[tx_port, rx_port],
                    layer1=[fcoe1, fcoe2],
                    options=options)
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
