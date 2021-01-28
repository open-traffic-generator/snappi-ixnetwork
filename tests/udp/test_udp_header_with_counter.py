import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_udp_header_with_counter(api, b2b_raw_config, utils):
    """
    Configure a raw udp flow with,
    - Non-default Counter Pattern values of src and
      dst Port address, length, checksum
    - 100 frames of 74B size each
    - 10% line rate

    Validate,
    - tx/rx frame count is as expected
    - all captured frames have expected src and dst Port address
    """
    flow = b2b_raw_config.flows[0]

    src_port = ('5000', '2', '10')
    dst_port = ('6000', '2', '10')
    length = ('35', '1', '2')
    checksum = ('6', '1', '2')
    packets = 100
    size = 74

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
            Flow.Udp(
                src_port=Flow.Pattern(
                    Flow.Counter(start=src_port[0], step=src_port[1],
                                 count=int(src_port[2]))
                ),
                dst_port=Flow.Pattern(
                    Flow.Counter(start=dst_port[0], step=dst_port[1],
                                 count=int(dst_port[2]), up=False)
                ),
                length=Flow.Pattern(
                    Flow.Counter(start=length[0], step=length[1],
                                 count=int(length[2]))
                ),
                checksum=Flow.Pattern(
                    Flow.Counter(start=checksum[0], step=checksum[1],
                                 count=int(checksum[2]))
                )
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

