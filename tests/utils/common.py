import json
import os
import time
import io
import dpkt
import sys

from abstract_open_traffic_generator import (
    config, port, layer1, flow, control, result, capture
)
from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi


if sys.version_info[0] >= 3:
    # alias str as unicode for python3 and above
    unicode = str


# path to settings.json relative root dir
SETTINGS_FILE = 'settings.json'
# path to dir containing traffic configurations relative root dir
CONFIGS_DIR = 'configs'


def get_root_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_test_config_path(config_name):
    return os.path.join(get_root_dir(), CONFIGS_DIR, config_name)


def dict_items(d):
    try:
        # python 3
        return d.items()
    except Exception:
        # python 2
        return d.iteritems()


def object_dict_items(ob):
    return dict_items(ob.__dict__)


def byteify(val):
    if isinstance(val, dict):
        return {byteify(key): byteify(value) for key, value in dict_items(val)}
    elif isinstance(val, list):
        return [byteify(element) for element in val]
    # change u'string' to 'string' only for python2
    elif isinstance(val, unicode) and sys.version_info[0] == 2:
        return val.encode('utf-8')
    else:
        return val


def load_dict_from_json_file(path):
    """
    Safely load dictionary from JSON file in both python2 and python3
    """
    with open(path, 'r') as fp:
        return json.load(fp, object_hook=byteify)


class Settings(object):
    """
    Singleton for global settings
    """
    def __init__(self):
        # these not be defined and are here only for documentation
        self.username = None
        self.api_server = None
        self.ports = None
        self.speed = None
        self.timeout_seconds = None
        self.interval_seconds = None
        self.log_level = None
        self.license_servers = None

        self.load_from_settings_file()

    def load_from_settings_file(self):
        self.__dict__ = load_dict_from_json_file(self.get_settings_path())
        # overwrite with custom settings if it exists
        custom = os.environ.get('SETTINGS_FILE', None)
        if custom is not None and os.path.exists(custom):
            self.__dict__ = load_dict_from_json_file(custom)

    def get_settings_path(self):
        return os.path.join(get_root_dir(), SETTINGS_FILE)

    def register_pytest_command_line_options(self, parser):
        for key, val in object_dict_items(self):
            parser.addoption("--%s" % key, action="store", default=None)

    def load_from_pytest_command_line(self, config):
        for key, val in object_dict_items(self):
            new_val = config.getoption(key)
            if new_val is not None:
                if key in ['license_servers', 'ports']:
                    # items in a list are expected to be passed in as a string
                    # where each item is separated by whitespace
                    setattr(self, key, new_val.split())
                else:
                    setattr(self, key, new_val)


# shared global settings
settings = Settings()


def get_api_client():
    """
    Returns api client configured according to global settings
    """
    host, port = settings.api_server.split(':')
    return IxNetworkApi(
        host, port=port, license_servers=[], log_level='info'
    )


def get_b2b_raw_config():
    """
    Returns raw b2b traffic config patched with ports and speed from global
    settings and one default flow
    """
    ports = []
    # modify config to use port locations provided in settings.json
    for i, n in enumerate(['raw_tx', 'raw_rx']):
        ports.append(port.Port(name=n, location=settings.ports[i]))

    l1 = None
    # modify speed
    if settings.speed is not None:
        l1 = [
            layer1.Layer1(
                name='raw_l1', port_names=[p.name for p in ports],
                speed=settings.speed
            )
        ]

    c = capture.Capture(
        name='raw_capture', port_names=[ports[1].name], enable=True, choice=[]
    )

    # default flow with first two ports as tx/rx
    f = flow.Flow(
        name='%s->%s' % (ports[0].name, ports[1].name),
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[0].name,
                rx_port_name=ports[1].name
            )
        )
    )

    return config.Config(ports=ports, layer1=l1, flows=[f], captures=[c])


def get_capture_port_names(cfg):
    """
    Returns name of ports for which capture is enabled.
    """
    names = []
    if cfg.captures:
        for cap in cfg.captures:
            if cap.port_names and cap.enable:
                for name in cap.port_names:
                    if name not in names:
                        names.append(name)

    return names


def start_traffic(api, cfg):
    """
    Applies configuration, starts capture and starts flows.
    """
    print('Setting config ...')
    api.set_state(control.State(control.ConfigState(config=cfg, state='set')))

    capture_names = get_capture_port_names(cfg)
    if capture_names:
        print('Starting capture on ports %s ...' % str(capture_names))
        api.set_state(
            control.State(
                control.PortCaptureState(
                    port_names=capture_names, state='start'
                )
            )
        )

    print('Starting transmit on all flows ...')
    api.set_state(control.State(control.FlowTransmitState(state='start')))


def stop_traffic(api, cfg):
    """
    Stops flows and capture.
    """
    print('Stopping transmit on all flows ...')
    api.set_state(control.State(control.FlowTransmitState(state='stop')))
    capture_names = get_capture_port_names(cfg)
    if capture_names:
        print('Stopping capture on ports %s ...' % str(capture_names))
        api.set_state(
            control.State(
                control.PortCaptureState(
                    port_names=capture_names, state='stop'
                )
            )
        )


def get_all_stats(api, print_output=True):
    """
    Returns all port and flow stats
    """
    print('Fetching all port stats ...')
    port_results = api.get_port_results(result.PortRequest())
    if port_results is None:
        port_results = []

    print('Fetching all flow stats ...')
    flow_results = api.get_flow_results(result.FlowRequest())
    if flow_results is None:
        flow_results = []

    if print_output:
        print_stats(port_stats=port_results, flow_stats=flow_results)

    return port_results, flow_results


def get_all_captures(api, cfg):
    """
    Returns a dictionary where port name is the key and value is a list of
    frames where each frame is represented as a list of bytes.
    """
    cap_dict = {}
    for name in get_capture_port_names(cfg):
        print('Fetching captures from port %s' % name)
        pcap_bytes = api.get_capture_results(
            result.CaptureRequest(port_name=name)
        )
        if len(pcap_bytes) < 1000:
            print('Received incomplete pcap from port %s, retrying ...' % name)
            pcap_bytes = api.get_capture_results(
                result.CaptureRequest(port_name=name)
            )

        cap_dict[name] = []
        for ts, pkt in dpkt.pcap.Reader(io.BytesIO(pcap_bytes)):
            if sys.version_info[0] == 2:
                cap_dict[name].append([ord(b) for b in pkt])
            else:
                cap_dict[name].append(list(pkt))

    return cap_dict


def seconds_elapsed(start_seconds):
    return int(round(time.time() - start_seconds))


def timed_out(start_seconds, timeout):
    return seconds_elapsed(start_seconds) > timeout


def wait_for(func, condition_str, interval_seconds=None, timeout_seconds=None):
    """
    Keeps calling the `func` until it returns true or `timeout_seconds` occurs
    every `interval_seconds`. `condition_str` should be a constant string
    implying the actual condition being tested.

    Usage
    -----
    If we wanted to poll for current seconds to be divisible by `n`, we would
    implement something similar to following:
    ```
    import time
    def wait_for_seconds(n, **kwargs):
        condition_str = 'seconds to be divisible by %d' % n

        def condition_satisfied():
            return int(time.time()) % n == 0

        poll_until(condition_satisfied, condition_str, **kwargs)
    ```
    """
    if interval_seconds is None:
        interval_seconds = settings.interval_seconds
    if timeout_seconds is None:
        timeout_seconds = settings.timeout_seconds
    start_seconds = int(time.time())

    print('\n\nWaiting for %s ...' % condition_str)
    while True:
        res = func()
        if res:
            print('Done waiting for %s' % condition_str)
            break
        if res is None:
            raise Exception('Wait aborted for %s' % condition_str)
        if timed_out(start_seconds, timeout_seconds):
            msg = 'Time out occurred while waiting for %s' % condition_str
            raise Exception(msg)

        time.sleep(interval_seconds)


def print_stats(port_stats=None, flow_stats=None, clear_screen=False):
    if clear_screen:
        os.system('clear')

    if port_stats is not None:
        row_format = "{:>15}" * 6
        border = '-' * (15 * 6 + 5)
        print('\nPort Stats')
        print(border)
        print(
            row_format.format(
                'Port', 'Tx Frames', 'Tx Bytes', 'Rx Frames', 'Rx Bytes',
                'Tx FPS'
            )
        )
        for stat in port_stats:
            print(
                row_format.format(
                    stat['name'], stat['frames_tx'], stat['bytes_tx'],
                    stat['frames_rx'], stat['bytes_rx'], stat['frames_tx_rate']
                )
            )
            break
        print(border)
        print("")
        print("")

    if flow_stats is not None:
        row_format = "{:>15}" * 3
        border = '-' * (15 * 3 + 5)
        print('Flow Stats')
        print(border)
        print(row_format.format('Flow', 'Rx Frames', 'Rx Bytes'))
        for stat in flow_stats:
            print(row_format.format(
                stat['name'], stat['frames_rx'], stat['bytes_rx_rate'])
            )
        print(border)
        print("")
        print("")


def flow_transmit_matches(flow_results, state):
    return len(flow_results) == len(
        list(filter(lambda f: f['transmit'] == state, flow_results))
    )


def total_frames_ok(port_results, flow_results, expected):
    port_tx = sum(
        [0 if 'frames_tx' not in p else p['frames_tx'] for p in port_results]
    )
    # port_rx = sum([p['frames_rx'] for p in port_results])
    flow_rx = sum([f['frames_rx'] for f in flow_results])

    return port_tx == flow_rx == expected


def total_bytes_ok(port_results, flow_results, expected):
    port_tx = sum(
        [0 if 'bytes_tx' not in p else p['bytes_tx'] for p in port_results]
    )
    # port_rx = sum([p['bytes_rx'] for p in port_results])
    flow_rx = sum([f['bytes_rx'] for f in flow_results])

    return port_tx == flow_rx == expected


def total_bytes_in_frame_size_range(start, end, step, count):
    """
    Returns total bytes after summing up all frame sizes in the given range.
    """
    pkt_count = 0
    total_bytes = 0
    partial_bytes = 0
    for i in range(start, end + 1, step):
        total_bytes += i
        pkt_count += 1
    total_count = int(count / pkt_count)
    partial_count = count % pkt_count
    n = 0
    for i in range(start, end + 1, step):
        if n == partial_count:
            break
        partial_bytes += i
        n += 1

    return total_bytes * total_count + partial_bytes
