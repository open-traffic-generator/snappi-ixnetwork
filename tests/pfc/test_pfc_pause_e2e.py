import pytest


@pytest.mark.e2e
@pytest.mark.parametrize("lossless_priorities", [[3, 4]])
def test_pfc_pause_e2e(api, settings, utils, lossless_priorities):
    """
    Configure ports where,
    - tx port can only respond to pause frames for `lossless_priorities`
    - rx port is capable of sending pause frames for all priorities
    Configure 8 raw IPv4 flows on tx port where,
    - each flow is mapped to corresponding PHB_CS and priority queue value
    - each flow sends 100K frames at 10% line rate and with start delay of 1s
    Configure one raw PFC Pause flow on rx port where,
    - pause frames are sent for 20 seconds (pause storm)
    Validate,
    - tx/rx frame count is 600K before and 800K after pause storm
    - rx frame count for flows pertaining to `lossless_priorities` is 0 before
      and 100K after pause storm
    - rx frame count for rest of the flows is 100K before and after pause storm
    """

    size = 128
    packets = 100000

    config = api.config()

    tx, rx = config.ports.port(name="raw_tx", location=settings.ports[0]).port(
        name="raw_rx", location=settings.ports[1]
    )

    tx_l1 = config.layer1.layer1(
        name="txl1",
        port_names=[tx.name],
        speed=settings.speed,
        media=settings.media,
    )[-1]
    qbb = tx_l1.flow_control.ieee_802_1qbb
    [
        setattr(
            qbb, "pfc_class_%d" % i, i if i in lossless_priorities else None
        )
        for i in range(8)
    ]
    rx_l1 = config.layer1.layer1(
        name="rxl1",
        port_names=[rx.name],
        speed=settings.speed,
        media=settings.media,
    )[-1]
    rx_l1.flow_control.ieee_802_1qbb
    rx_l1.flow_control.choice = rx_l1.flow_control.IEEE_802_1QBB
    config.options.port_options.location_preemption = True
    for i in range(8):
        f = config.flows.flow(name="tx_p%d" % i)[-1]
        f.tx_rx.port.tx_name = tx.name
        f.tx_rx.port.rx_name = rx.name
        eth = f.packet.ethernet()[-1]
        eth.src.value = "00:CD:DC:CD:DC:CD"
        eth.dst.value = "00:AB:BC:AB:BC:AB"
        eth.pfc_queue.value = str(i)
        ipv4 = f.packet.ipv4()[-1]
        ipv4.src.value = "1.1.1.2"
        ipv4.dst.value = "1.1.1.1"
        ipv4.priority.dscp.phb.value = str(i * 8)
        f.duration.fixed_packets.packets = packets
        f.duration.fixed_packets.delay.nanoseconds = 10 ** 9
        f.size.fixed = size
        f.rate.percentage = 10
    rx_pause = config.flows.flow(name="rx_pause")[-1]
    rx_pause.tx_rx.port.tx_name = rx.name
    rx_pause.tx_rx.port.rx_name = tx.name
    pfc = rx_pause.packet.pfcpause()[-1]
    pfc.src.value = "00:AB:BC:AB:BC:AB"
    pfc.control_op_code.value = "0101"
    pfc.class_enable_vector.value = "0xFF"
    [
        setattr(getattr(pfc, "pause_class_%d" % i), "value", "FFFF")
        for i in range(8)
    ]
    rx_pause.duration.fixed_seconds.seconds = 20
    rx_pause.size.fixed = size
    rx_pause.rate.percentage = 100

    utils.start_traffic(api, config)
    utils.wait_for(
        lambda: results_ok(
            api, config, utils, size, packets, lossless_priorities
        ),
        "stats to be as expected",
        timeout_seconds=30,
    )
    utils.wait_for(
        lambda: results_ok(api, config, utils, size, packets, []),
        "stats to be as expected",
        timeout_seconds=30,
    )


def results_ok(api, cfg, utils, size, packets, lossless_priorities):
    """
    Returns true if stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    ok = [False, False, False, False, False, False, False, False, False]

    port_tx = sum([p.frames_tx for p in port_results if p.name == "raw_tx"])
    ok[8] = port_tx == packets * (8 - len(lossless_priorities))

    for f in flow_results:
        if f.name == "rx_pause":
            continue

        _, p = f.name.split("tx_p")
        p = int(p)
        if p in lossless_priorities:
            ok[p] = f.frames_rx == 0
        else:
            ok[p] = f.frames_rx == packets

    return all(ok)
