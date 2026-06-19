import pytest


# NOTE on frame ordering modes
# ----------------------------
# The OTG/snappi model expresses transmit ordering through
# ``Port.Options.frame_ordering_mode`` (no_ordering | rfc2889) which pairs
# with ``Port.Options.data_integrity``. The snappi build used by this wrapper
# exposes ``config.options.port_options.data_integrity`` (the sequence /
# integrity checking knob); the ordering use cases themselves are driven by
# the surrounding building blocks - flow rate, flow metrics (loss / latency)
# and the flow end points (port.tx_rx single src->dst, or device.tx_rx with
# one_to_one / mesh for many-to-many / many-to-one).
#
# These b2b tests exercise the use cases from both ordering buckets:
#   no_ordering : line-rate throughput, loss/latency, single src->dst
#   rfc2889     : fully-meshed forwarding, many-to-one congestion/HOL,
#                 broadcast forwarding
#
# All tests run back-to-back over the two ports from settings and never create
# more than 6 device end points.


def _add_ip_devices(cfg, utils, tx_count, rx_count):
    """Create ``tx_count`` ipv4 devices on the tx port and ``rx_count`` on the
    rx port (back-to-back). Total end points must stay within 6.
    Returns (tx_ip_names, rx_ip_names) - the ipv4 address names used as flow
    end points.
    """
    assert tx_count + rx_count <= 6
    count = max(tx_count, rx_count)
    mac_tx = utils.mac_or_ip_addr_from_counter_pattern(
        "00:10:10:20:20:10", "00:00:00:00:00:01", count, True
    )
    mac_rx = utils.mac_or_ip_addr_from_counter_pattern(
        "00:10:10:20:20:20", "00:00:00:00:00:01", count, False
    )
    ip_tx = utils.mac_or_ip_addr_from_counter_pattern(
        "10.1.1.1", "0.0.1.0", count, True, False
    )
    ip_rx = utils.mac_or_ip_addr_from_counter_pattern(
        "10.1.1.2", "0.0.1.0", count, True, False
    )

    tx_names, rx_names = [], []
    for i in range(tx_count):
        dev = cfg.devices.device(name="tx_dev_%d" % (i + 1))[-1]
        eth = dev.ethernets.add()
        eth.name = "tx_eth_%d" % (i + 1)
        eth.connection.port_name = cfg.ports[0].name
        eth.mac = mac_tx[i]
        ip = eth.ipv4_addresses.add()
        ip.name = "tx_ipv4_%d" % (i + 1)
        ip.address = ip_tx[i]
        ip.gateway = ip_rx[i]
        ip.prefix = 24
        tx_names.append(ip.name)

    for i in range(rx_count):
        dev = cfg.devices.device(name="rx_dev_%d" % (i + 1))[-1]
        eth = dev.ethernets.add()
        eth.name = "rx_eth_%d" % (i + 1)
        eth.connection.port_name = cfg.ports[1].name
        eth.mac = mac_rx[i]
        ip = eth.ipv4_addresses.add()
        ip.name = "rx_ipv4_%d" % (i + 1)
        ip.address = ip_rx[i]
        ip.gateway = ip_tx[i]
        ip.prefix = 24
        rx_names.append(ip.name)

    return tx_names, rx_names


def _frames_ok(api, utils, packets):
    port_results, flow_results = utils.get_all_stats(api)
    return utils.total_frames_ok(port_results, flow_results, packets)


# ----------------------------------------------------------------------------
# no_ordering use cases
# ----------------------------------------------------------------------------


@pytest.mark.skip("WIP: frame ordering b2b coverage")
@pytest.mark.e2e
def test_no_ordering_line_rate_throughput(api, b2b_raw_config, utils):
    """no_ordering UC#1 - RFC 2544 throughput / line-rate saturation.

    Single src->dst flow at 100% line rate; ordering is irrelevant, only that
    the DUT forwards at rate with zero loss. data_integrity stays off (lowest
    scheduler overhead, the natural no_ordering setting).
    Validation: tx == rx frames (zero loss) at line rate.
    """
    SIZE = 512
    PACKETS = 100000

    b2b_raw_config.options.port_options.data_integrity = False

    f = b2b_raw_config.flows[0]
    f.size.fixed = SIZE
    f.rate.percentage = 100
    f.duration.fixed_packets.packets = PACKETS
    f.metrics.enable = True
    f.metrics.loss = True

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: _frames_ok(api, utils, PACKETS),
        "line-rate throughput with zero loss",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, b2b_raw_config)

    _, flow_results = utils.get_all_stats(api)
    for f in flow_results:
        assert f.frames_tx == f.frames_rx == PACKETS


@pytest.mark.skip("WIP: frame ordering b2b coverage")
@pytest.mark.e2e
def test_no_ordering_loss_latency(api, b2b_raw_config, utils):
    """no_ordering UC#2 - loss / latency-only measurement.

    Single flow with loss and store-forward latency metrics enabled; sequence
    numbers are not inspected so no_ordering is the right setting.
    Validation: loss is reported and latency min/avg/max are present.
    """
    SIZE = 1024
    PACKETS = 10000

    b2b_raw_config.options.port_options.data_integrity = False

    f = b2b_raw_config.flows[0]
    f.size.fixed = SIZE
    f.rate.percentage = 50
    f.duration.fixed_packets.packets = PACKETS
    f.metrics.enable = True
    f.metrics.loss = True
    f.metrics.timestamps = True
    f.metrics.latency.enable = True
    f.metrics.latency.mode = f.metrics.latency.STORE_FORWARD

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: _frames_ok(api, utils, PACKETS),
        "loss/latency stats to be as expected",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, b2b_raw_config)

    _, flow_results = utils.get_all_stats(api)
    for f in flow_results:
        assert f.loss is not None
        latency = getattr(f, "latency")
        assert getattr(latency, "minimum_ns") is not None
        assert getattr(latency, "average_ns") is not None
        assert getattr(latency, "maximum_ns") is not None


@pytest.mark.skip("WIP: frame ordering b2b coverage")
@pytest.mark.e2e
def test_no_ordering_single_src_dst(api, b2b_raw_config, utils):
    """no_ordering UC#3 - single-flow, single src->dst.

    With one flow on the port there is nothing to interleave, so ordering is
    moot and no_ordering avoids needless scheduler overhead.
    Validation: tx == rx frames and bytes.
    """
    SIZE = 256
    PACKETS = 50000

    b2b_raw_config.options.port_options.data_integrity = False

    f = b2b_raw_config.flows[0]
    f.packet.ethernet().ipv4()
    f.size.fixed = SIZE
    f.rate.percentage = 30
    f.duration.fixed_packets.packets = PACKETS
    f.metrics.enable = True
    f.metrics.loss = True

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: _frames_ok(api, utils, PACKETS),
        "single src->dst stats to be as expected",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, b2b_raw_config)

    port_results, flow_results = utils.get_all_stats(api)
    assert utils.total_bytes_ok(port_results, flow_results, PACKETS * SIZE)


# ----------------------------------------------------------------------------
# rfc2889 use cases
# ----------------------------------------------------------------------------


@pytest.mark.skip("WIP: frame ordering b2b coverage")
@pytest.mark.e2e
def test_rfc2889_fully_meshed_forwarding(api, b2b_raw_config, utils):
    """rfc2889 UC#1 - fully-meshed forwarding (many-to-many).

    3 tx devices send to 3 rx devices in mesh mode (6 end points). RFC 2889
    ordering keeps the per-stream sequencing valid under the mesh, so
    data_integrity (sequence checking) is enabled.
    Validation: every mesh combination is forwarded (tx == rx frames).
    """
    SIZE = 512
    PACKETS = 30000
    TX, RX = 3, 3

    b2b_raw_config.options.port_options.data_integrity = True

    tx_names, rx_names = _add_ip_devices(b2b_raw_config, utils, TX, RX)

    b2b_raw_config.flows.clear()
    f = b2b_raw_config.flows.flow(name="mesh")[-1]
    f.tx_rx.device.tx_names = tx_names
    f.tx_rx.device.rx_names = rx_names
    f.tx_rx.device.mode = f.tx_rx.device.MESH
    f.size.fixed = SIZE
    f.rate.percentage = 20
    f.duration.fixed_packets.packets = PACKETS
    f.metrics.enable = True
    f.metrics.loss = True

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: _frames_ok(api, utils, PACKETS),
        "fully-meshed forwarding stats to be as expected",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, b2b_raw_config)


@pytest.mark.skip("WIP: frame ordering b2b coverage")
@pytest.mark.e2e
def test_rfc2889_congestion_hol_many_to_one(api, b2b_raw_config, utils):
    """rfc2889 UC#3 - congestion control / Head-of-Line blocking.

    Many-to-one oversubscription: 5 tx devices blast a single rx device
    (6 end points). Stream ordering lets the receiver attribute frames per
    source stream, so data_integrity is enabled.
    Validation: frames forwarded to the single destination (tx == rx frames).
    """
    SIZE = 512
    PACKETS = 30000
    TX, RX = 5, 1

    b2b_raw_config.options.port_options.data_integrity = True

    tx_names, rx_names = _add_ip_devices(b2b_raw_config, utils, TX, RX)

    b2b_raw_config.flows.clear()
    f = b2b_raw_config.flows.flow(name="many_to_one")[-1]
    f.tx_rx.device.tx_names = tx_names
    f.tx_rx.device.rx_names = rx_names
    f.tx_rx.device.mode = f.tx_rx.device.MESH
    f.size.fixed = SIZE
    f.rate.percentage = 20
    f.duration.fixed_packets.packets = PACKETS
    f.metrics.enable = True
    f.metrics.loss = True

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: _frames_ok(api, utils, PACKETS),
        "many-to-one congestion stats to be as expected",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, b2b_raw_config)


@pytest.mark.skip("WIP: frame ordering b2b coverage")
@pytest.mark.e2e
def test_rfc2889_broadcast_forwarding(api, b2b_raw_config, utils):
    """rfc2889 UC#4 - broadcast forwarding & latency.

    One src -> broadcast destination MAC; RFC 2889 ordering keeps the
    broadcast stream measurable. Latency is enabled to cover broadcast
    latency, and data_integrity is on for sequence checking.
    Validation: frames forwarded and latency metrics present.
    """
    SIZE = 256
    PACKETS = 20000

    b2b_raw_config.options.port_options.data_integrity = True

    f = b2b_raw_config.flows[0]
    eth = f.packet.ethernet()[-1]
    eth.dst.value = "ff:ff:ff:ff:ff:ff"
    eth.src.value = "00:10:10:20:20:10"
    f.size.fixed = SIZE
    f.rate.percentage = 20
    f.duration.fixed_packets.packets = PACKETS
    f.metrics.enable = True
    f.metrics.loss = True
    f.metrics.latency.enable = True
    f.metrics.latency.mode = f.metrics.latency.STORE_FORWARD

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: _frames_ok(api, utils, PACKETS),
        "broadcast forwarding stats to be as expected",
        timeout_seconds=30,
    )
    utils.stop_traffic(api, b2b_raw_config)

    _, flow_results = utils.get_all_stats(api)
    for f in flow_results:
        latency = getattr(f, "latency")
        assert getattr(latency, "average_ns") is not None


if __name__ == "__main__":
    pytest.main(["-s", __file__])
