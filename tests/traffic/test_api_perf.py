import pytest
import utils
import traceback
import time
from abstract_open_traffic_generator import flow, control, result


CSV_COLUMNS = [
    'config_type', 'iterations', 'set_config_ms', 'start_flows_ms',
    'stop_flows_ms', 'start_capture_ms', 'stop_capture_ms',
    'get_port_results_ms', 'get_flow_results_ms', 'get_captures_ms', 'result'
]
CSV_DIR = utils.new_logs_dir()


@pytest.mark.e2e
@pytest.mark.parametrize(
    'config_type', ['one_flow_tcp_128b', 'ten_flows_tcp_128b']
)
@pytest.mark.parametrize("iterations", [10])
def test_api_perf(settings, config_type, iterations):
    """
    This test collects avg duration in milliseconds for all required API calls
    required in a usual E2E test script.
    """
    packets = 100
    row = new_result_dict(config_type, iterations)

    for i in range(1, iterations + 1):
        try:
            api = utils.get_api_client()
            print('Config %s Iteration %d' % (config_type, i))
            config = eval(config_type)(settings, packets)

            set_config(api, config, row)
            start_capture(api, config, row)
            start_flows(api, config, row)
            utils.wait_for(
                lambda: utils.is_traffic_stopped(
                    api, [f.name for f in config.flows]
                ),
                'traffic to be stopped', timeout_seconds=10
            )
            stop_flows(api, config, row)
            stop_capture(api, config, row)
            get_port_results(api, config, row, packets)
            get_flow_results(api, config, row, packets)
            get_captures(api, config, row, packets)
            row['result'] = 'PASSED'
        except Exception:
            traceback.print_exc()
        finally:
            # cleanup API session
            if api.assistant is not None:
                api.assistant.Session.remove()

    for key in CSV_COLUMNS:
        if key.endswith('_ms'):
            row[key] //= iterations
    utils.append_csv_row(CSV_DIR, 'api_perf.csv', CSV_COLUMNS, row)


def new_result_dict(config_type, iterations):
    return {
        'config_type': config_type,
        'iterations': iterations,
        'set_config_ms': 0,
        'start_flows_ms': 0,
        'stop_flows_ms': 0,
        'start_capture_ms': 0,
        'stop_capture_ms': 0,
        'get_port_results_ms': 0,
        'get_flow_results_ms': 0,
        'get_captures_ms': 0,
        'result': 'FAILED'
    }


def ms_elapsed(start_ms):
    return int(round(time.time() * 1000 - start_ms))


def ms_now():
    return time.time() * 1000


def set_config(api, config, row):
    print('Setting config ...')
    t = ms_now()
    api.set_state(
        control.State(control.ConfigState(config=config, state='set'))
    )
    row['set_config_ms'] += ms_elapsed(t)


def start_flows(api, config, row):
    print('Starting flows ...')
    t = ms_now()
    api.set_state(control.State(control.FlowTransmitState(state='start')))
    row['start_flows_ms'] += ms_elapsed(t)


def stop_flows(api, config, row):
    print('Stopping flows ...')
    t = ms_now()
    api.set_state(control.State(control.FlowTransmitState(state='stop')))
    row['stop_flows_ms'] += ms_elapsed(t)


def start_capture(api, config, row):
    print('Starting capture ...')
    t = ms_now()
    api.set_state(
        control.State(
            control.PortCaptureState(
                port_names=[config.ports[1].name], state='start'
            )
        )
    )
    row['start_capture_ms'] += ms_elapsed(t)


def stop_capture(api, config, row):
    # TODO: investigate why executing this function causes exception
    return
    print('Stopping capture ...')
    t = ms_now()
    api.set_state(
        control.State(
            control.PortCaptureState(
                port_names=[config.ports[1].name], state='stop'
            )
        )
    )
    row['stop_capture_ms'] += ms_elapsed(t)


def get_port_results(api, config, row, packets):
    print('Fetching port results ...')
    t = ms_now()
    port_results = api.get_port_results(result.PortRequest())
    row['get_port_results_ms'] += ms_elapsed(t)
    utils.print_stats(port_stats=port_results)

    n = len(config.flows)
    assert sum([p['frames_tx'] for p in port_results]) == packets * n
    assert sum([p['frames_rx'] for p in port_results]) == packets * n


def get_flow_results(api, config, row, packets):
    print('Fetching flow results ...')
    t = ms_now()
    flow_results = api.get_flow_results(result.FlowRequest())
    row['get_flow_results_ms'] += ms_elapsed(t)
    utils.print_stats(flow_stats=flow_results)

    assert all([f['frames_tx'] == packets for f in flow_results])
    assert all([f['frames_rx'] == packets for f in flow_results])


def get_captures(api, config, row, packets):
    print('Fetching captures ...')
    t = ms_now()
    cap_dict = utils.get_all_captures(api, config)
    row['get_captures_ms'] += ms_elapsed(t)

    for k in cap_dict:
        assert len(cap_dict[k]) == packets * len(config.flows)


def one_flow_tcp_128b(settings, packets):
    config = utils.get_b2b_raw_config()
    f = config.flows[0]
    f.packet = [
        flow.Header(
            flow.Ethernet(
                src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                dst=flow.Pattern('00:AB:BC:AB:BC:AB')
            )
        ),
        flow.Header(
            flow.Ipv4(
                src=flow.Pattern('1.1.1.2'),
                dst=flow.Pattern('1.1.1.1')
            )
        ),
        flow.Header(
            flow.Tcp(
                src_port=flow.Pattern(
                    ['5000', '5050', '5015', '5040', '5032', '5021']
                ),
                dst_port=flow.Pattern(['6000', '6015', '6050']),
            )
        )
    ]
    f.duration = flow.Duration(flow.FixedPackets(packets=packets))
    f.size = flow.Size(128)
    f.rate = flow.Rate(value=10, unit='line')
    return config


def ten_flows_tcp_128b(settings, packets):
    config = utils.get_b2b_raw_config()
    config.flows = []

    for i in range(1, 11):
        f = flow.Flow(
            name='f%d' % i,
            tx_rx=flow.TxRx(
                flow.PortTxRx(
                    tx_port_name=config.ports[0].name,
                    rx_port_name=config.ports[1].name
                )
            )
        )
        f.packet = [
            flow.Header(
                flow.Ethernet(
                    src=flow.Pattern('00:CD:DC:CD:DC:CD'),
                    dst=flow.Pattern('00:AB:BC:AB:BC:AB')
                )
            ),
            flow.Header(
                flow.Ipv4(
                    src=flow.Pattern('1.1.1.2'),
                    dst=flow.Pattern('1.1.1.1')
                )
            ),
            flow.Header(
                flow.Tcp(
                    src_port=flow.Pattern(
                        ['5000', '5050', '5015', '5040', '5032', '5021']
                    ),
                    dst_port=flow.Pattern(['6000', '6015', '6050']),
                )
            )
        ]
        f.duration = flow.Duration(flow.FixedPackets(packets=packets))
        f.size = flow.Size(128)
        f.rate = flow.Rate(value=10, unit='line')

        config.flows.append(f)

    return config
