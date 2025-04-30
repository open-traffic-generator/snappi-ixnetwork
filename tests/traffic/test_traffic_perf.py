@pytest.mark.skip(
    reason="CI-Testing"
)
def test_counter_ip_dscp(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - all Dscp values

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    b2b_raw_config.flows.clear()
    for i in range(20):
        f = b2b_raw_config.flows.flow(name="flow-%s" % i)[-1]
        f.tx_rx.port.tx_name = b2b_raw_config.ports[0].name
        f.tx_rx.port.rx_name = b2b_raw_config.ports[1].name
        eth, ipv4 = f.packet.ethernet().ipv4()
        ipv4.priority.dscp.phb.value = 46
    api.set_config(b2b_raw_config)
