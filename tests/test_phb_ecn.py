def test_phb_ecn(api, tx_port, rx_port, b2b_raw_config):
    """
    This will test that phb and ecn are set on an ipv4 header
    """
    b2b_raw_config.flows.clear()
    f = b2b_raw_config.flows.flow()[-1]
    f.name = "Ipv4 with Phb and Ecn"
    f.tx_rx.port.tx_name = tx_port.name
    f.tx_rx.port.rx_name = rx_port.name
    f.packet.ethernet().ipv4()
    ip = f.packet[-1]
    ip.priority.choice = ip.priority.DSCP
    ip.priority.dscp.phb.values = [
        ip.priority.dscp.phb.CS2,
        ip.priority.dscp.phb.CS1,
        ip.priority.dscp.phb.CS5,
    ]
    ip.priority.dscp.ecn.value = ip.priority.dscp.ecn.CAPABLE_TRANSPORT_1
    api.set_config(b2b_raw_config)
