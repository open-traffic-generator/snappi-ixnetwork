import pytest


@pytest.mark.skip("skip until migrated to snappi")
@pytest.mark.e2e
def test_ip_device_and_flow(api, b2b_raw_config, utils):
    """
    Configure the devices on Tx and Rx Port.
    Configure the flow with devices as end points.
    run the traffic
    Validation,
    - validate the port and flow statistics.
    """

    size = 128
    packets = 100000

    tx_eth = device.Ethernet(
        name="TxMac",
        mac=device.Pattern(
            choice=device.Counter(
                start="00:10:10:20:20:10",
                step="00:00:00:00:00:01"
            )
        )
    )

    tx_ip = device.Ipv4(
        name="TxIP",
        address=device.Pattern(
            choice=device.Counter(
                start="10.1.1.1",
                step="0.0.1.0"
            )
        ),
        gateway=device.Pattern(
            choice=device.Counter(
                start="10.1.1.2",
                step="0.0.1.0"
            )
        ),
        prefix=device.Pattern("24"),
        ethernet=tx_eth
    )

    rx_eth = device.Ethernet(
        name="RxMac",
        mac=device.Pattern(
            choice=device.Counter(
                start="00:10:10:20:20:20",
                step="00:00:00:00:00:01",
                up=False
            )
        )
    )

    rx_ip = device.Ipv4(
        name="RxIP",
        address=device.Pattern(
            choice=device.Counter(
                start="10.1.1.2",
                step="0.0.1.0"
            )
        ),
        gateway=device.Pattern(
            choice=device.Counter(
                start="10.1.1.1",
                step="0.0.1.0"
            )
        ),
        prefix=device.Pattern("24"),
        ethernet=rx_eth
    )

    tx_device = device.Device(
        name="TxDevice",
        container_name=b2b_raw_config.ports[0].name,
        device_count=10,
        choice=tx_ip
    )

    rx_device = device.Device(
        name="RxDevice",
        container_name=b2b_raw_config.ports[1].name,
        device_count=10,
        choice=rx_ip
    )
    b2b_raw_config.devices = [tx_device, rx_device]

    ep = flow.TxRx(
        choice=flow.DeviceTxRx(
            tx_device_names=["TxDevice"],
            rx_device_names=["RxDevice"]
        )
    )

    b2b_raw_config.flows = [flow.Flow(
        name="TxFlow-1",
        tx_rx=ep,
        duration=flow.Duration(
            flow.FixedPackets(
                packets=packets
            )
        ),
        size=flow.Size(size),
        rate=flow.Rate(value=10, unit='line')
    )]

    b2b_raw_config.flows.append(
        flow.Flow(
            name="TxFlow-2",
            tx_rx=ep,
            duration=flow.Duration(
                flow.FixedPackets(
                    packets=packets
                )
            ),
            packet=[
                flow.Header(flow.Ethernet()),
                flow.Header(flow.Ipv4()),
                flow.Header(
                    flow.Tcp(
                        src_port=flow.Pattern(
                            flow.Counter(
                                start="5000",
                                step="1",
                                count=10
                            )
                        ),
                        dst_port=flow.Pattern(
                            flow.Counter(
                                start="2000",
                                step="1",
                                count=10
                            )
                        )
                    )
                )
            ],
            size=flow.Size(size * 2),
            rate=flow.Rate(value=10, unit='line')
        )
    )

    utils.apply_config(api, b2b_raw_config)
    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, utils, size, size * 2, packets),
        'stats to be as expected', timeout_seconds=10
    )
    api.set_state(control.State(control.FlowTransmitState(state='stop')))
    captures_ok(api, b2b_raw_config, utils, packets * 2)


def results_ok(api, utils, size1, size2, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets * 2)
    bytes_ok = utils.total_bytes_ok(
        port_results, flow_results, packets * size1 + packets * size2
    )
    return frames_ok and bytes_ok


def captures_ok(api, cfg, utils, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x10 + i] for i in range(10)]
    dst_mac = [[0x00, 0x10, 0x10, 0x20, 0x20, 0x20 - i] for i in range(10)]

    src_ip = [
        [0x0a, 0x01, 0x01, 0x01], [0x0a, 0x01, 0x02, 0x01],
        [0x0a, 0x01, 0x03, 0x01], [0x0a, 0x01, 0x04, 0x01],
        [0x0a, 0x01, 0x05, 0x01], [0x0a, 0x01, 0x06, 0x01],
        [0x0a, 0x01, 0x07, 0x01], [0x0a, 0x01, 0x08, 0x01],
        [0x0a, 0x01, 0x09, 0x01], [0x0a, 0x01, 0x0a, 0x01]
    ]
    dst_ip = [
        [0x0a, 0x01, 0x01, 0x02], [0x0a, 0x01, 0x02, 0x02],
        [0x0a, 0x01, 0x03, 0x02], [0x0a, 0x01, 0x04, 0x02],
        [0x0a, 0x01, 0x05, 0x02], [0x0a, 0x01, 0x06, 0x02],
        [0x0a, 0x01, 0x07, 0x02], [0x0a, 0x01, 0x08, 0x02],
        [0x0a, 0x01, 0x09, 0x02], [0x0a, 0x01, 0x0a, 0x02]
    ]

    src_port = [[0x13, 0x88 + i] for i in range(10)]
    dst_port = [[0x07, 0xd0 + i] for i in range(10)]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1
    sizes = [128, 256]
    size_dt = {
        128: [0 for i in range(10)],
        256: [0 for i in range(10)]
    }

    for b in cap_dict[list(cap_dict.keys())[0]]:
        i = dst_mac.index(b[0:6])
        assert b[0:6] == dst_mac[i] and b[6:12] == src_mac[i]
        assert b[26:30] == src_ip[i] and b[30:34] == dst_ip[i]
        assert len(b) in sizes
        size_dt[len(b)][i] += 1
        if len(b) == 256:
            assert b[34:36] == src_port[i] and b[36:38] == dst_port[i]

    assert sum(size_dt[128]) + sum(size_dt[256]) == packets
