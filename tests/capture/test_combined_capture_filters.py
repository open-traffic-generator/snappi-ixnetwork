import pytest
import dpkt


# def test_combined_filters(request, tracer, api, b2b_config):
def test_combined_filters(api, settings, utils):
    """
    This test applies ethernet and vlan capture filters and verifies correct capture results
    """
    packets = 4
    config = api.config()
    p1, p2 = config.ports.port(
        name="p1", location=utils.settings.ports[0]
    ).port(name="p2", location=utils.settings.ports[1])
    cap = config.captures.capture(name="capture1")[-1]
    cap.port_names = [p2.name]
    cap.format = cap.PCAPNG
    cap.overwrite = False
    eth_filter, vlan_filter = cap.filters.ethernet().vlan()

    eth_filter.src.value = "0000ff000000"
    eth_filter.src.mask = "000000000000"
    eth_filter.src.negate = False
    eth_filter.dst.value = "000806020000"
    eth_filter.dst.mask = "000000000000"
    eth_filter.dst.negate = False

    vlan_filter.id.value = "0006"
    vlan_filter.id.mask = "F000"
    vlan_filter.id.negate = True
    vlan_filter.priority.value = "07"
    vlan_filter.priority.mask = "07"
    vlan_filter.priority.negate = False

    (f1,) = config.flows.flow(name="f1")
    f1.tx_rx.port.tx_name = p1.name
    f1.tx_rx.port.rx_name = p2.name
    f1.metrics.enable = True
    f1.size.fixed = 128
    f1.rate.pps = 1000
    f1.duration.fixed_packets.packets = 4
    eth, vlan = f1.packet.ethernet().vlan()
    eth.src.values = [
        "00:00:ff:00:00:00",
        "00:00:ff:00:00:00",
        "00:00:11:00:00:00",
        "00:00:ff:00:00:00",
    ]
    eth.dst.values = [
        "00:00:07:08:00:00",
        "00:00:44:00:00:00",
        "00:00:09:00:00:00",
        "00:08:06:02:00:00",
    ]
    vlan.priority.values = [1, 2, 3, 7]
    vlan.cfi.values = [0, 1, 0, 1]
    vlan.id.values = [5, 3, 1, 6]

    utils.start_traffic(api, config, start_capture=True)
    utils.wait_for(
        lambda: results_ok(api, ["f1"], packets),
        "stats to be as expected",
        timeout_seconds=10,
    )
    utils.stop_traffic(api, config)
    captures_ok(api, config, utils, config.ports[1].name)


def results_ok(api, flow_names, expected):
    """
    Returns True if there is no traffic loss else False
    """
    request = api.metrics_request()
    request.flow.flow_names = flow_names
    flow_results = api.get_metrics(request).flow_metrics
    flow_rx = sum([f.frames_rx for f in flow_results])
    return flow_rx == expected


def captures_ok(api, cfg, utils, name):
    pkt_count = 0
    cap_dict = utils.get_all_captures(api, cfg)
    for buf in cap_dict[name]:
        assert buf[0:6] == [0x00, 0x08, 0x06, 0x02, 0x00, 0x00]
        assert buf[6:12] == [0x00, 0x00, 0xFF, 0x00, 0x00, 0x00]
        assert buf[14:16] == [0xF0, 0x06]
        pkt_count += 1
    assert pkt_count == 1
