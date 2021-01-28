import pytest


@pytest.mark.skip("skip until migrated to snappi")
def test_counter_mac_addrs(api, b2b_raw_config, utils):
    """
    Configure a raw ethernet flow with,
    - counter pattern for src and dst MAC address and ether type

    Validate,
    - Fetch the ethernet header config via restpy and validate
    against expected
    """
    f = b2b_raw_config.flows[0]
    count = 10
    src = '00:0C:29:E3:53:EA'
    dst = '00:0C:29:E3:53:F4'
    step = '00:00:00:00:01:00'
    eth_type = '8100'
    eth_step = '2'

    src_mac_list = flow.Counter(
        start=src,
        step=step,
        count=count
    )

    dst_mac_list = flow.Counter(
        start=dst,
        step=step,
        count=count,
        up=False
    )

    eth_type_list = flow.Counter(
        start=eth_type,
        step=eth_step,
        count=count
    )

    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern(src_mac_list),
                dst=flow.Pattern(dst_mac_list),
                ether_type=flow.Pattern(eth_type_list)
            )
        )
    ]

    utils.apply_config(api, b2b_raw_config)

    attrs = {
        'Destination MAC Address': (
            dst.lower(),
            step,
            str(count)
        ),
        'Source MAC Address': (
            src.lower(),
            step,
            str(count)
        ),
        'Ethernet-Type': (eth_type, eth_step, str(count)),
    }
    utils.validate_config(api, 'ethernet', **attrs)
