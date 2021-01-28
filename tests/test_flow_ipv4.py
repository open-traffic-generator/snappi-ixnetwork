import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_flow_ipv4(serializer, tx_port, rx_port, b2b_ipv4_devices, api):
    """IPv4 Flow with different priority test traffic configuration
    """
    endpoint = DeviceTxRx(tx_device_names=[b2b_ipv4_devices[0].name],
                          rx_device_names=[b2b_ipv4_devices[1].name])

    test_dscp = Priority(
        Dscp(phb=Pattern(Dscp.PHB_CS7, ingress_result_name='phb')))
    ip_dscp_flow = Flow(name='IPv4 DSCP',
                        tx_rx=TxRx(endpoint),
                        packet=[
                            Header(Ethernet()),
                            Header(Vlan()),
                            Header(
                                Ipv4(priority=test_dscp,
                                     identification=Pattern(
                                         Counter(start='1', step='2',
                                                 count=4)),
                                     total_length=Pattern('90'))),
                        ],
                        size=Size(128),
                        rate=Rate('line', 50),
                        duration=Duration(FixedPackets(packets=0)))

    # Probably Tos.HIGH rather than Tos.LOW
    test_tos = Priority(
        Tos(precedence=Pattern(Tos.PRE_FLASH_OVERRIDE,
                               ingress_result_name='tos precedence'),
            delay=Pattern(Tos.NORMAL),
            throughput=Pattern(Tos.LOW),
            reliability=Pattern(Tos.NORMAL),
            monetary=Pattern(Tos.LOW),
            unused=Pattern(Tos.LOW)))
    ip_tos_flow = Flow(name='IPv4 TOS',
                       tx_rx=TxRx(endpoint),
                       packet=[
                           Header(Ethernet()),
                           Header(Vlan()),
                           Header(Ipv4(priority=test_tos)),
                       ],
                       size=Size(128),
                       rate=Rate('line', 50),
                       duration=Duration(FixedPackets(packets=0)))

    test_pattern = Priority(Pattern(Counter(start='0', step='1', count=256)))
    ip_pattern_flow = Flow(name='IPv4 Pattern',
                       tx_rx=TxRx(endpoint),
                       packet=[
                           Header(Ethernet()),
                           Header(Vlan()),
                           Header(Ipv4(priority=test_pattern,
                                       src=Pattern('1.1.1.2'),
                                       dst=Pattern('1.1.1.1'))),
                       ],
                       duration=Duration(Continuous()))
    
    config = Config(ports=[tx_port, rx_port],
                    devices=b2b_ipv4_devices,
                    flows=[
                        ip_dscp_flow,
                        ip_tos_flow,
                        ip_pattern_flow
                    ])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])
