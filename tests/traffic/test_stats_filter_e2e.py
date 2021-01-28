import pytest


@pytest.mark.skip("skip until migrated to snappi")
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

    f1_size = 74
    f2_size = 1500
    ports = b2b_raw_config.ports
    flow1 = b2b_raw_config.flows[0]

    flow2 = flow.Flow(
        name='f2',
        tx_rx=flow.TxRx(
            flow.PortTxRx(
                tx_port_name=ports[0].name,
                rx_port_name=ports[1].name
            )
        )
    )
    b2b_raw_config.flows.append(flow2)

    flow1.size = flow.Size(f1_size)
    flow1.rate = flow.Rate(value=10, unit='line')
    flow1.duration = flow.Duration(flow.Continuous())

    flow2.size = flow.Size(f2_size)
    flow2.rate = flow.Rate(value=10, unit='line')
    flow2.duration = flow.Duration(flow.Continuous())

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    time.sleep(5)

    # Validation on Port statistics based on port names
    port_names = ['raw_tx', 'raw_rx']
    for port_name in port_names:
        port_results = api.get_port_results(result.PortRequest(
                                            port_names=[port_name]))
        validate_port_stats_based_on_port_name(port_results, port_name)

    # Validation on Port statistics based on column names
    column_names = ['frames_tx_rate', 'bytes_tx_rate',
                    'frames_rx_rate', 'bytes_rx_rate']
    for column_name in column_names:
        port_results = api.get_port_results(result.PortRequest(
                                            column_names=['name',
                                                          column_name]))
        validate_port_stats_based_on_column_name(port_results,
                                                 column_name)

    # Validation on Flow statistics based on flow names
    flow_names = ['f1', 'f2']
    for flow_name in flow_names:
        flow_results = api.get_flow_results(result.FlowRequest(
                                            flow_names=[flow_name],
                                            column_names=['name']))
        validate_flow_stats_based_on_flow_name(flow_results, flow_name)

    # Validation on Flow statistics based on column names
    column_names = ['frames_tx_rate', 'bytes_tx_rate',
                    'frames_rx_rate', 'bytes_rx_rate']
    for column_name in column_names:
        flow_results = api.get_flow_results(result.FlowRequest(
                                            column_names=['name',
                                                          column_name]))
        validate_flow_stats_based_on_column_name(flow_results,
                                                 column_name)

    utils.stop_traffic(api, b2b_raw_config)


def validate_port_stats_based_on_port_name(port_results, port_name):
    """
    Validate stats based on port_names
    """
    for row in port_results:
        assert row['name'] == port_name


def validate_port_stats_based_on_column_name(port_results,
                                             column_name):
    """
    Validate Port stats based on column_names
    """
    for row in port_results:
        if row['name'] == 'raw_tx':
            if column_name == 'frames_tx_rate':
                assert row[column_name] > 0
            elif column_name == 'bytes_tx_rate':
                assert row[column_name] > 0
        elif row['name'] == 'raw_rx':
            if column_name == 'frames_rx_rate':
                assert row[column_name] > 0
            elif column_name == 'bytes_rx_rate':
                assert row[column_name] > 0


def validate_flow_stats_based_on_flow_name(flow_results, flow_name):
    """
    Validate Flow stats based on flow_names
    """
    for row in flow_results:
        assert row['name'] == flow_name


def validate_flow_stats_based_on_column_name(flow_results,
                                             column_name):
    """
    Validate Flow stats based on column_names
    """
    for row in flow_results:
        assert row[column_name] > 0
