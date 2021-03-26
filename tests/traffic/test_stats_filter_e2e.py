import pytest
import time


@pytest.mark.e2e
def test_stats_filter_e2e(api, b2b_raw_config, utils):
    """
    configure two flows f1 and f2
    - Send continuous packets from f1 of size 74B
    - Send continuous packets from f2 of size 1500B

    Validation:
    1) Get port statistics based on port name & column names and assert
    each port & column has returned the values and assert
    2) Get flow statistics based on flow name & column names and assert
    each flow & column has returned the values and assert
    """
    api.set_config(api.config())
    f1_size = 74
    f2_size = 1500
    ports = b2b_raw_config.ports
    flow1 = b2b_raw_config.flows[0]
    flow2 = b2b_raw_config.flows.flow()[-1]
    flow2.name = 'f2'
    flow2.tx_rx.port.tx_name = ports[0].name
    flow2.tx_rx.port.rx_name = ports[1].name

    flow1.size.fixed = f1_size
    flow1.rate.percentage = 10
    flow1.duration.continuous

    flow2.size.fixed = f2_size
    flow2.rate.percentage = 10
    flow2.duration.continuous

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    time.sleep(5)

    # Validation on Port statistics based on port names
    port_names = ['raw_tx', 'raw_rx']
    for port_name in port_names:
        req = api.metrics_request()
        req.port.port_names = [port_name]
        port_results = api.get_metrics(req).port_metrics
        validate_port_stats_based_on_port_name(port_results, port_name)

    # Validation on Port statistics based on column names
    column_names = ['frames_tx_rate', 'bytes_tx_rate',
                    'frames_rx_rate', 'bytes_rx_rate']
    for column_name in column_names:
        req = api.metrics_request()
        req.port.column_names = ['name', column_name]
        port_results = api.get_metrics(req).port_metrics
        validate_port_stats_based_on_column_name(port_results,
                                                 column_name)

    # Validation on Flow statistics based on flow names
    flow_names = ['f1', 'f2']
    for flow_name in flow_names:
        req = api.metrics_request()
        req.flow.flow_names = [flow_name]
        req.flow.column_names = ['name']
        flow_results = api.get_metrics(req).flow_metrics
        validate_flow_stats_based_on_flow_name(flow_results, flow_name)

    # Validation on Flow statistics based on column names
    column_names = ['frames_tx_rate', 'frames_rx_rate']
    for column_name in column_names:
        req = api.metrics_request()
        req.flow.column_names = ['name', column_name]
        flow_results = api.get_metrics(req).flow_metrics
        validate_flow_stats_based_on_column_name(flow_results,
                                                 column_name)

    utils.stop_traffic(api, b2b_raw_config)


def validate_port_stats_based_on_port_name(port_results, port_name):
    """
    Validate stats based on port_names
    """
    for row in port_results:
        assert row.name == port_name


def validate_port_stats_based_on_column_name(port_results,
                                             column_name):
    """
    Validate Port stats based on column_names
    """
    for row in port_results:
        if row.name == 'raw_tx':
            if column_name == 'frames_tx_rate':
                assert getattr(row, column_name) > 0
            elif column_name == 'bytes_tx_rate':
                assert getattr(row, column_name) > 0
        elif row.name == 'raw_rx':
            if column_name == 'frames_rx_rate':
                assert getattr(row, column_name) > 0
            elif column_name == 'bytes_rx_rate':
                assert getattr(row, column_name) > 0


def validate_flow_stats_based_on_flow_name(flow_results, flow_name):
    """
    Validate Flow stats based on flow_names
    """
    for row in flow_results:
        assert row.name == flow_name


def validate_flow_stats_based_on_column_name(flow_results,
                                             column_name):
    """
    Validate Flow stats based on column_names
    """
    for row in flow_results:
        assert round(getattr(row, column_name)) > 0
