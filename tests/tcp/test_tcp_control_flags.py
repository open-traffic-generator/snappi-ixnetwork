from abstract_open_traffic_generator import flow as Flow


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

    flow.packet = [
        Flow.Header(
            Flow.Ethernet(
                src=Flow.Pattern('00:0c:29:1d:10:67'),
                dst=Flow.Pattern('00:0c:29:1d:10:71')
            )
        ),
        Flow.Header(
            Flow.Ipv4(
                src=Flow.Pattern('10.10.10.1'),
                dst=Flow.Pattern('10.10.10.2')
            )
        ),
        Flow.Header(
            Flow.Tcp(
                src_port=Flow.Pattern(src_port),
                dst_port=Flow.Pattern(dst_port),
                ecn_ns=Flow.Pattern(control_flags[0]),
                ecn_cwr=Flow.Pattern(control_flags[1]),
                ecn_echo=Flow.Pattern(control_flags[2]),
                ctl_urg=Flow.Pattern(control_flags[3]),
                ctl_ack=Flow.Pattern(control_flags[4]),
                ctl_psh=Flow.Pattern(control_flags[5]),
                ctl_rst=Flow.Pattern(control_flags[6]),
                ctl_syn=Flow.Pattern(control_flags[7]),
                ctl_fin=Flow.Pattern(control_flags[8]),
            )
        ),
    ]
    flow.duration = Flow.Duration(Flow.FixedPackets(packets=packets))
    flow.size = Flow.Size(size)
    flow.rate = Flow.Rate(value=10, unit='line')

    utils.apply_config(api, b2b_raw_config)
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
