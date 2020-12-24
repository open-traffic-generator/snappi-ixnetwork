import pytest
from abstract_open_traffic_generator import (
    config, port, layer1, flow
)


@pytest.mark.e2e
def test_global_unpause_e2e(api, settings, utils):
    """
    Configure ports where,
    - tx port can only respond to pause and un-pause frames for
      all priorities
    - rx port is to send pause and un-pause frames on all priorities
    Configure raw IPv4 flows on tx port with all class based priorities where,
    - each flow is mapped to corresponding PHB_CS and priority queue value
    - each flow sends 100K frames at 10% of packets pps rate
      with start delay of 1s
    Configure one raw Global Pause flow and one un-pause flow on rx port where,
    - pause frames are sent for 10 seconds (pause storm)
    - un-pause frames are sent for 10 seconds with start delay of 10s
    Validate,
    - tx/rx frame count is 0 before and (priorities * 100k)
      after pause storm
    """

    size = 128
    packets = 100000

    tx = port.Port(name='raw_tx', location=settings.ports[0])
    rx = port.Port(name='raw_rx', location=settings.ports[1])

    tx_l1 = layer1.Layer1(
        name='txl1', port_names=[tx.name], speed=settings.speed,
        media=settings.media,
        flow_control=layer1.FlowControl(
            choice=layer1.Ieee8023x())
    )

    rx_l1 = layer1.Layer1(
        name='rxl1', port_names=[rx.name], speed=settings.speed,
        media=settings.media,
        flow_control=layer1.FlowControl(choice=layer1.Ieee8023x())
    )

    flows = []

    flows.append(
        flow.Flow(
            name='tx_flow_global',
            tx_rx=flow.TxRx(
                flow.PortTxRx(tx_port_name=tx.name, rx_port_name=rx.name)
            ),
            packet=[
                flow.Header(
                    flow.Ethernet(
                        src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                        dst=flow.Pattern('00:AB:BC:AB:BC:AB'),
                    )
                ),
                flow.Header(
                    flow.Ipv4(
                        src=flow.Pattern('1.1.1.2'),
                        dst=flow.Pattern('1.1.1.1'),
                    )
                )
            ],
            duration=flow.Duration(
                flow.FixedPackets(
                    packets=packets, delay=10**9, delay_unit='nanoseconds'
                )
            ),
            size=flow.Size(size),
            rate=flow.Rate(value=10, unit='line')
        )
    )

    flows.append(
        flow.Flow(
            name='rx_global_pause',
            tx_rx=flow.TxRx(
                flow.PortTxRx(tx_port_name=rx.name, rx_port_name=tx.name)
            ),
            packet=[
                flow.Header(
                    flow.EthernetPause(
                        src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                        ether_type=flow.Pattern('8808'),
                        control_op_code=flow.Pattern('0001'),
                        time=flow.Pattern('FFFF')
                    )
                )
            ],
            duration=flow.Duration(flow.FixedSeconds(seconds=10)),
            size=flow.Size(size),
            rate=flow.Rate(value=50, unit='line')
        )
    )

    flows.append(
        flow.Flow(
            name='rx_global_unpause',
            tx_rx=flow.TxRx(
                flow.PortTxRx(tx_port_name=rx.name, rx_port_name=tx.name)
            ),
            packet=[
                flow.Header(
                    flow.EthernetPause(
                        src=flow.Pattern('00:AB:BC:AB:BC:AB'),
                        ether_type=flow.Pattern('8808'),
                        control_op_code=flow.Pattern('0001'),
                        time=flow.Pattern('0000')
                    )
                )
            ],
            duration=flow.Duration(flow.FixedSeconds(
                seconds=10, delay=(10**9) * 10, delay_unit='nanoseconds'
            )),
            size=flow.Size(size),
            rate=flow.Rate(value=50, unit='line')
        )
    )

    cfg = config.Config(
        ports=[tx, rx], layer1=[tx_l1, rx_l1], flows=flows,
        options=config.Options(port.Options(location_preemption=True))
    )
    utils.start_traffic(api, cfg)

    utils.wait_for(
        lambda: results_ok(
            api, utils, packets
        ),
        'stats to be as expected', timeout_seconds=10
    )

    utils.wait_for(
        lambda: results_ok(api, utils, packets, False),
        'stats to be as expected', timeout_seconds=30
    )


def results_ok(api, utils, packets, check_for_pause=True):
    """
    Returns true if stats are as expected, false otherwise.
    """
    flow_results = api.get_flow_results(utils.result.FlowRequest())
    pause = [
        f['frames_rx'] for f in flow_results if f['name'] == 'rx_global_pause'
    ][0]
    un_pause = [
        f['frames_rx'] for f in flow_results if f[
            'name'] == 'rx_global_unpause'
    ][0]
    ok = False

    for fl in flow_results:
        if fl['name'] == 'rx_global_pause' or \
           fl['name'] == 'rx_global_unpause':
            continue
        if pause > 0 and un_pause == 0 and check_for_pause and \
           fl['name'] == "tx_flow_global":
            ok = fl['frames_tx'] == fl['frames_rx'] == 0
            continue
        if un_pause > 0 and (check_for_pause is False) \
           and fl['name'] == "tx_flow_global":
            ok = fl['frames_tx'] == fl['frames_rx'] == packets

    return ok
