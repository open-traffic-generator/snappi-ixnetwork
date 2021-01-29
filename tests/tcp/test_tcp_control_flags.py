def test_tcp_control_flags(api, b2b_raw_config, utils):
    """
    Configure a raw tcp flow with,
    - with different control flags
    - 1000 frames of 1500B size each
    - 10% line rate

    Validate,
    - Config is applied using validate config
    """
    flow = b2b_raw_config.flows[0]
    src_port = '3000'
    dst_port = '4000'
    control_flags = '111100101'
    size = 1500
    packets = 100
    flow.packet.ethernet().ipv4().tcp()
    tcp = flow.packet[-1]
    tcp.src_port.value = src_port
    tcp.dst_port.value = dst_port
    flags = [
        "ecn_ns", "ecn_cwr", "ecn_echo", "ctl_urg", "ctl_ack",
        "ctl_psh", "ctl_rst", "ctl_syn", "ctl_fin"
    ]
    for i, f in enumerate(flags):
        getattr(tcp, f).value = control_flags[i]

    flow.duration.fixed_packets.packets = packets
    flow.size.fixed = size
    flow.rate.percentage = 10

    api.set_config(b2b_raw_config)

    attrs = {
        'TCP-Source-Port': src_port,
        'TCP-Dest-Port': dst_port,
        'NS': control_flags[0],
        'CWR': control_flags[1],
        'ECN-Echo': control_flags[2],
        'URG': control_flags[3],
        'ACK': control_flags[4],
        'PSH': control_flags[5],
        'RST': control_flags[6],
        'SYN': control_flags[7],
        'FIN': control_flags[8]
    }
    utils.validate_config(api, 'tcp', **attrs)
