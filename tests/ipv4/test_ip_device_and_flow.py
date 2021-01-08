import pytest
from abstract_open_traffic_generator import (
    flow, device
)


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
                start="00:20:20:10:10:20",
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

    ep = flow.TxRx(
        choice=flow.DeviceTxRx(
            tx_device_names=["TxDevice"],
            rx_device_names=["RxDevice"]
        )
    )

    b2b_raw_config.flows = [flow.Flow(
        name="TxFlow",
        tx_rx=ep,
        duration=flow.Duration(
            flow.FixedPackets(
                packets=packets
            )
        ),
        size=flow.Size(size),
        rate=flow.Rate(value=10, unit='line')
    )]
    b2b_raw_config.devices = [tx_device, rx_device]
    utils.apply_config(api, b2b_raw_config)
    utils.start_traffic(api, b2b_raw_config)
    utils.wait_for(
        lambda: results_ok(api, utils, size, packets),
        'stats to be as expected', timeout_seconds=10
    )
    captures_ok(api, b2b_raw_config, utils, size, packets)


def results_ok(api, utils, size, packets):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)
    frames_ok = utils.total_frames_ok(port_results, flow_results, packets)
    bytes_ok = utils.total_bytes_ok(port_results, flow_results, packets * size)
    return frames_ok and bytes_ok


def captures_ok(api, cfg, utils, size, packets):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    src = [
        [0x0a, 0x01, 0x01, 0x01], [0x0a, 0x01, 0x02, 0x01],
        [0x0a, 0x01, 0x03, 0x01], [0x0a, 0x01, 0x04, 0x01],
        [0x0a, 0x01, 0x05, 0x01], [0x0a, 0x01, 0x06, 0x01],
        [0x0a, 0x01, 0x07, 0x01], [0x0a, 0x01, 0x08, 0x01],
        [0x0a, 0x01, 0x09, 0x01], [0x0a, 0x01, 0x0a, 0x01]
    ]
    dst = [
        [0x0a, 0x01, 0x01, 0x02], [0x0a, 0x01, 0x02, 0x02],
        [0x0a, 0x01, 0x03, 0x02], [0x0a, 0x01, 0x04, 0x02],
        [0x0a, 0x01, 0x05, 0x02], [0x0a, 0x01, 0x06, 0x02],
        [0x0a, 0x01, 0x07, 0x02], [0x0a, 0x01, 0x08, 0x02],
        [0x0a, 0x01, 0x09, 0x02], [0x0a, 0x01, 0x0a, 0x02]
    ]

    cap_dict = utils.get_all_captures(api, cfg)
    assert len(cap_dict) == 1

    for k in cap_dict:
        i = 0
        for b in cap_dict[k]:
            assert b[26:30] == src[i] and b[30:34] == dst[i]
            i = (i + 1) % 10
