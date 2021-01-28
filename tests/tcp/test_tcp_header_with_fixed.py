import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_tcp_header_with_fixed(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - Config is applied using validate config
    """
    src_port = '3000'
    dst_port = '4000'
    size = 74
    packets = 1000
    flow = b2b_raw_config.flows[0]

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
                dst=Flow.Pattern('10.10.10.2'),
            )
        ),
        Flow.Header(
            Flow.Tcp(
                src_port=Flow.Pattern(src_port),
                dst_port=Flow.Pattern(dst_port),
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
    }
    utils.validate_config(api, 'tcp', **attrs)
