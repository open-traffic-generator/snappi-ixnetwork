import pytest
import utils
from abstract_open_traffic_generator import flow as Flow


@pytest.mark.parametrize('packets', [100])
@pytest.mark.parametrize('size', [74])
def test_tcp_header_with_counter(api, b2b_raw_config, size, packets):
    """
    Configure a raw udp flow with,
    - Non-default Counter Pattern values of src and
      dst Port address, length, checksum
    - 100 frames of 74B size each
    - 10% line rate

    Validate,
    - Config is applied using validate config
    """
    flow = b2b_raw_config.flows[0]
    src_port = ('5000', '5100', '2', '1', '10')
    dst_port = ('6000', '6100', '2', '1', '10')

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
                src_port=Flow.Pattern(
                    Flow.Random(min=src_port[0], max=src_port[1],
                                step=int(src_port[2]), seed=src_port[3],
                                count=int(src_port[4]))
                ),
                dst_port=Flow.Pattern(
                    Flow.Random(min=dst_port[0], max=dst_port[1],
                                step=int(dst_port[2]), seed=dst_port[3],
                                count=int(dst_port[4]))
                ),
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
