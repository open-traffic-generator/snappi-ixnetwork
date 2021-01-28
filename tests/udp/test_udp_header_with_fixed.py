import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_udp_header_with_fixed(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - fixed src and dst Port address, length, checksum
    - 1000 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    src_port = '3000'
    dst_port = '4000'
    length = '38'
    checksum = '5'
    packets = 1000
    size = 74
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
            Flow.Udp(
                src_port=Flow.Pattern(src_port),
                dst_port=Flow.Pattern(dst_port),
                length=Flow.Pattern(length),
                checksum=Flow.Pattern(checksum)
            )
        ),
    ]
    flow.duration = Flow.Duration(Flow.FixedPackets(packets=packets))
    flow.size = Flow.Size(size)
    flow.rate = Flow.Rate(value=10, unit='line')

    utils.apply_config(api, b2b_raw_config)
    attrs = {
        'UDP-Source-Port': src_port,
        'UDP-Dest-Port': dst_port,
        'UDP-Length': length,
        'UDP-Checksum': checksum
    }
    utils.validate_config(api, 'udp', **attrs)
