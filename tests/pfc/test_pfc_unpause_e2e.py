import pytest


@pytest.mark.e2e
@pytest.mark.parametrize('lossless_priorities', [[3, 4]])
def test_pfc_unpause_e2e(api, settings, utils, lossless_priorities):
    """
    Configure ports where,
    - tx port can only respond to pause and un-pause frames for
      'lossless_priorities'
    - rx port is to send pause and un-pause frames on lossless priorities
    Configure raw IPv4 flows on tx port with lossless_priorities where,
    - each flow is mapped to corresponding PHB_CS and priority queue value
    - each flow sends 100K frames at 10% of packets pps rate
      with start delay of 1s
    Configure one raw PFC Pause flow and one un-pause flow on rx port where,
    - pause frames are sent for 10 seconds (pause storm)
    - un-pause frames are sent for 10 seconds with start delay of 10s
    Validate,
    - tx/rx frame count is 0 before and (lossless_priorities * 100k)
      after pause storm
    """

    size = 128
    packets = 100000
    config = api.config()

    tx, rx = (
        config.ports
        .port(name='raw_tx', location=settings.ports[0])
        .port(name='raw_rx', location=settings.ports[1])
    )

    tx_l1 = config.layer1.layer1(
        name='txl1', port_names=[tx.name], speed=settings.speed,
        media=settings.media
    )[-1]
    qbb = tx_l1.flow_control.ieee_802_1qbb
    [
        setattr(
            qbb, 'pfc_class_%d' % i, i if i in lossless_priorities else None
        )
        for i in range(8)
    ]
    rx_l1 = config.layer1.layer1(
        name='rxl1', port_names=[rx.name], speed=settings.speed,
        media=settings.media
    )[-1]
    rx_l1.flow_control.ieee_802_1qbb
    rx_l1.flow_control.choice = rx_l1.flow_control.IEEE_802_1QBB
    config.options.port_options.location_preemption = True

    for prio in lossless_priorities:
        f = config.flows.flow(name='tx_prio_%d' % prio)[-1]
        f.tx_rx.port.tx_name = tx.name
        f.tx_rx.port.rx_name = rx.name
        eth = f.packet.ethernet()[-1]
        eth.src.value = '00:CD:DC:CD:DC:CD'
        eth.dst.value = '00:AB:BC:AB:BC:AB'
        eth.pfc_queue.value = str(prio)
        ipv4 = f.packet.ipv4()[-1]
        ipv4.src.value = '1.1.1.2'
        ipv4.dst.value = '1.1.1.1'
        ipv4.priority.dscp.phb.value = str(prio * 8)
        f.duration.fixed_packets.packets = packets
        f.duration.fixed_packets.delay = 10**9
        f.duration.fixed_packets.delay_unit = 'nanoseconds'
        f.size.fixed = size
        f.rate.percentage = 10

    rx_pause = config.flows.flow(name='rx_pfc_pause')[-1]
    rx_pause.tx_rx.port.tx_name = rx.name
    rx_pause.tx_rx.port.rx_name = tx.name
    pfc = rx_pause.packet.pfcpause()[-1]
    pfc.src.value = '00:AB:BC:AB:BC:AB'
    pfc.control_op_code.value = '0101'
    pfc.class_enable_vector.value = '0xFF'
    pfc.pause_class_3.value = 'FFFF'
    pfc.pause_class_4.value = 'FFFF'
    rx_pause.duration.fixed_seconds.seconds = 10
    rx_pause.size.fixed = size
    rx_pause.rate.percentage = 50

    rx_unpause = config.flows.flow(name='rx_pfc_unpause')[-1]
    rx_unpause.tx_rx.port.tx_name = rx.name
    rx_unpause.tx_rx.port.rx_name = tx.name
    pfc = rx_unpause.packet.pfcpause()[-1]
    pfc.src.value = '00:AB:BC:AB:BC:AB'
    pfc.control_op_code.value = '0101'
    pfc.class_enable_vector.value = '0xFF'
    pfc.pause_class_3.value = '0000'
    pfc.pause_class_4.value = '0000'
    rx_unpause.duration.fixed_seconds.seconds = 10
    rx_unpause.duration.fixed_seconds.delay = (10**9) * 10
    rx_unpause.duration.fixed_seconds.delay_unit = 'nanoseconds'
    rx_unpause.size.fixed = size
    rx_unpause.rate.percentage = 50

    utils.start_traffic(api, config)

    utils.wait_for(
        lambda: results_ok(
            api, utils, packets, lossless_priorities
        ),
        'stats to be as expected', timeout_seconds=10
    )

    utils.wait_for(
        lambda: results_ok(api, utils, packets, lossless_priorities, False),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, utils, packets, lossless_priorities, check_for_pause=True):
    """
    Returns true if stats are as expected, false otherwise.
    """

    port_results, flow_results = utils.get_all_stats(api)

    pause = [
        f.frames_rx for f in flow_results if f.name == 'rx_pfc_pause'
    ][0]
    un_pause = [
        f.frames_rx for f in flow_results if f.name == 'rx_pfc_unpause'
    ][0]
    ok = [False for i in range(len(lossless_priorities))]

    count = 0

    for fl in flow_results:
        if fl.name == 'rx_unpause' or fl.name == 'rx_pause':
            continue
        if pause > 0 and un_pause == 0 and check_for_pause and \
           fl.name.startswith("tx_prio_"):
            ok[count] = fl.frames_tx == fl.frames_rx == 0
            count += 1
            continue
        if un_pause > 0 and (check_for_pause is False) \
           and fl.name.startswith("tx_prio_"):
            ok[count] = fl.frames_tx == fl.frames_rx == packets
            count += 1

    return all(ok)
