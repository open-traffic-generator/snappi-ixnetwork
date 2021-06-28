import pytest


@pytest.mark.skip(reason="Not yet implemented")
def test_ingress_result_name(tx_port, rx_port, b2b_ipv4_devices, api):
    """
    A unique name that can be used to drill down into flow results.
    The name will appears as one of the ingress_result_name options in requesting flow results and as a property in a flow result
    ingress_result_name will configure through Pattern. This test will covered following ingress_result_name within traffic items
        -Test Data:
            VLAN - priority (priority=Pattern(choice='1', ingress_result_name='VLAN priority'))
            Ipv4 - src (src=Pattern(ingress_result_name='IPv4 src'))
        - Pause Storm
            PfcPause - src (src=Pattern('00:00:fa:ce:fa:ce', ingress_result_name='PfcPause src'))
    """
    data_endpoint = DeviceTxRx(
        tx_device_names=[b2b_ipv4_devices[0].name],
        rx_device_names=[b2b_ipv4_devices[1].name],
    )

    test_dscp = Priority(Dscp(phb=Pattern(Dscp.PHB_CS7)))
    test_flow = Flow(
        name="Test Data",
        tx_rx=TxRx(data_endpoint),
        packet=[
            Header(Ethernet()),
            Header(
                Vlan(
                    priority=Pattern(
                        choice="1", ingress_result_name="VLAN priority"
                    )
                )
            ),
            Header(Ipv4(priority=test_dscp)),
        ],
        size=Size(128),
        rate=Rate("line", 50),
        duration=Duration(FixedPackets(packets=0)),
    )

    pause_endpoint = PortTxRx(
        tx_port_name=tx_port.name, rx_port_name=rx_port.name
    )
    pause = Header(
        PfcPause(
            dst=Pattern("01:80:C2:00:00:01"),
            src=Pattern(
                "00:00:fa:ce:fa:ce", ingress_result_name="PfcPause src"
            ),
            class_enable_vector=Pattern("1"),
            pause_class_0=Pattern("3"),
            pause_class_1=Pattern(Counter(start="2", step="6", count=99)),
            pause_class_2=Pattern(
                Counter(start="1", step="6", count=99, up=False)
            ),
            pause_class_3=Pattern(["6", "9", "2", "39"]),
            pause_class_4=Pattern(
                Random(min="11", max="33", step=1, seed="4", count=10)
            ),
        )
    )
    pause_flow = Flow(
        name="Pause Storm",
        tx_rx=TxRx(pause_endpoint),
        packet=[pause],
        size=Size(64),
        rate=Rate("line", value=100),
        duration=Duration(FixedPackets(packets=0)),
    )

    config = Config(
        ports=[tx_port, rx_port],
        devices=b2b_ipv4_devices,
        flows=[test_flow, pause_flow],
    )
    api.set_state(State(ConfigState(config=config, state="set")))


if __name__ == "__main__":
    pytest.main(["-s", __file__])
