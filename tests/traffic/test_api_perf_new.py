import pytest
from snappi_ixnetwork import timer
from collections import OrderedDict
import utils

CSV_DIR = utils.new_logs_dir()

@pytest.mark.skip(reason="skip to CICD faster")
@pytest.mark.parametrize("iterations", [1, 10])
@pytest.mark.parametrize("num_of_flows", [100])
@pytest.mark.parametrize("size", [128])
@pytest.mark.parametrize("packets", [1000])
def test_api_perf(
    api, b2b_raw_config, iterations, num_of_flows, size, packets
):
    api_log_map = OrderedDict()
    api_log_map["config_type"] = "{}_flows_tcp_{}b".format(num_of_flows, size)
    api_log_map["iterations"] = iterations
    api.set_config(api.config())
    b2b_raw_config.flows.clear()
    for flow_num in range(num_of_flows):
        flow = b2b_raw_config.flows.flow(name="flow-%s" % flow_num)[-1]
        flow.tx_rx.port.tx_name = b2b_raw_config.ports[0].name
        flow.tx_rx.port.rx_name = b2b_raw_config.ports[1].name
        flow.size.fixed = size
        flow.duration.fixed_packets.packets = packets
        flow.metrics.enable = True
        eth, ipv4, tcp = flow.packet.ethernet().ipv4().tcp()
        eth.src.value = "00:CD:DC:CD:DC:CD"
        eth.dst.value = "00:AB:BC:AB:BC:AB"
        ipv4.src.value = "10.1.1.1"
        ipv4.dst.value = "10.1.1.2"
        tcp.src_port.value = 5000
        tcp.dst_port.value = 6000
    for turn in range(iterations):
        utils.start_traffic(api, b2b_raw_config)
        utils.wait_for(
            lambda: utils.is_traffic_stopped(
                api, [f.name for f in b2b_raw_config.flows]
            ),
            "traffic to be stopped",
            timeout_seconds=50,
        )
        utils.stop_traffic(api, b2b_raw_config, False)
        get_captures(api, b2b_raw_config, packets)
        set_values(timer.timer_data, api_log_map)
    for key, value in api_log_map.items():
        if key in ["config_type", "iterations"]:
            continue
        api_log_map[key] = "%.3fs" % (value)
    utils.append_csv_row(
        CSV_DIR, "api_perf.csv", api_log_map.keys(), api_log_map
    )


def set_values(iter_log, api_log_map):
    for key, value in iter_log.items():
        if key not in api_log_map:
            api_log_map[key] = 0
        api_log_map[key] += value


def get_captures(api, config, packets):
    print("Fetching captures ...")
    cap_dict = utils.get_all_captures(api, config)
    for k in cap_dict:
        assert len(cap_dict[k]) == packets * len(config.flows)
