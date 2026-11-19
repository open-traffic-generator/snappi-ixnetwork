import pytest


@pytest.mark.e2e
def test_pfc_stats_b2b(api, settings, utils):
    """
    Configure a back-to-back setup where,
    - both ports use IEEE 802.1Qbb (PFC) flow control with priorities 3 and 4
      lossless
    Configure,
    - 2 raw IPv4 flows on tx port (priority queue 3 and 0), each sending a
      fixed number of frames
    - 1 raw PFC pause flow on rx port with zero pause quanta (the pause is
      released immediately, so data flows are never blocked)
    Fetch port and flow stats and validate,
    - tx port frames_tx / rx port frames_rx include the data frames
    - each data flow has frames_tx == frames_rx == packets
    - PFC pause flow has frames_tx == pause packets
    """

    size = 128
    packets = 1000
    pause_packets = 100
    lossless_priorities = [3, 4]

    config = api.config()

    tx, rx = config.ports.port(name="tx", location=settings.ports[0]).port(
        name="rx", location=settings.ports[1]
    )

    for port in (tx, rx):
        l1 = config.layer1.layer1(
            name="%s_l1" % port.name,
            port_names=[port.name],
            speed=settings.speed,
            media=settings.media,
        )[-1]
        l1.flow_control.choice = l1.flow_control.IEEE_802_1QBB
        qbb = l1.flow_control.ieee_802_1qbb
        for i in range(8):
            setattr(
                qbb,
                "pfc_class_%d" % i,
                i if i in lossless_priorities else None,
            )
    config.options.port_options.location_preemption = True

    for priority in (3, 0):
        f = config.flows.flow(name="data_p%d" % priority)[-1]
        f.tx_rx.port.tx_name = tx.name
        f.tx_rx.port.rx_name = rx.name
        eth = f.packet.ethernet()[-1]
        eth.src.value = "00:CD:DC:CD:DC:CD"
        eth.dst.value = "00:AB:BC:AB:BC:AB"
        eth.pfc_queue.value = priority
        ipv4 = f.packet.ipv4()[-1]
        ipv4.src.value = "1.1.1.2"
        ipv4.dst.value = "1.1.1.1"
        ipv4.priority.dscp.phb.value = priority * 8
        f.duration.fixed_packets.packets = packets
        f.size.fixed = size
        f.rate.percentage = 10
        f.metrics.enable = True

    pause = config.flows.flow(name="pfc_pause")[-1]
    pause.tx_rx.port.tx_name = rx.name
    pause.tx_rx.port.rx_name = tx.name
    pfc = pause.packet.pfcpause()[-1]
    pfc.src.value = "00:AB:BC:AB:BC:AB"
    pfc.control_op_code.value = 257
    pfc.class_enable_vector.value = 255
    for i in range(8):
        getattr(pfc, "pause_class_%d" % i).value = 0
    pause.duration.fixed_packets.packets = pause_packets
    pause.size.fixed = size
    pause.rate.percentage = 10
    pause.metrics.enable = True

    utils.start_traffic(api, config)

    utils.wait_for(
        lambda: stats_ok(
            api, utils, packets, pause_packets, len(config.flows) - 1
        ),
        "port and flow stats to be as expected",
        timeout_seconds=60,
    )


def stats_ok(api, utils, packets, pause_packets, data_flow_count):
    """
    Returns true if port and flow stats are as expected, false otherwise.
    """
    port_results, flow_results = utils.get_all_stats(api)

    port_tx = sum(p.frames_tx for p in port_results if p.name == "tx")
    port_rx = sum(p.frames_rx for p in port_results if p.name == "rx")
    expected = packets * data_flow_count
    if port_tx < expected or port_rx < expected:
        return False

    for f in flow_results:
        if f.name.startswith("data_p"):
            if f.frames_tx != packets or f.frames_rx != packets:
                return False
        elif f.name == "pfc_pause":
            if f.frames_tx != pause_packets:
                return False
    return len(flow_results) == data_flow_count + 1
