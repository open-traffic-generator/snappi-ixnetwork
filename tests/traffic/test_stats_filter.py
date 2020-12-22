from abstract_open_traffic_generator import flow
from abstract_open_traffic_generator import result


def test_stats_filter(api, b2b_raw_config, utils):
    """
    configure two flows f1 and f2
    - Send 1000 packets from f1 of size 74B
    - Send 2000 packets from f2 of size 1500B

    Validation:
    1) Get port statistics based on port name & column names and assert
    each port & column has returned the values and assert them against
    packets and frame size sent
    2) Get flow statistics based on flow name & column names and assert
    each flow & column has returned the values and assert them against
    packets and frame size sent
    """

    f1_packets = 1000
    f2_packets = 2000
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

    flow1.duration = flow.Duration(flow.FixedPackets(packets=f1_packets))
    flow1.size = flow.Size(f1_size)
    flow1.rate = flow.Rate(value=10, unit='line')

    flow2.duration = flow.Duration(flow.FixedPackets(packets=f2_packets))
    flow2.size = flow.Size(f2_size)
    flow2.rate = flow.Rate(value=10, unit='line')

    utils.start_traffic(api, b2b_raw_config, start_capture=False)
    utils.wait_for(
        lambda: utils.is_traffic_stopped(api), 'traffic to stop'
    )

    utils.wait_for(
        lambda: utils.is_stats_accumulated(api, f1_packets + f2_packets),
        'stats to be accumulated'
    )

    # Validation on Port statistics based on port names
    port_names = ['raw_tx', 'raw_rx']
    for port_name in port_names:
        port_results = api.get_port_results(result.PortRequest(
                                            port_names=[port_name]))
        validate_port_stats_based_on_port_name(port_results, port_name)

    # Validation on Port statistics based on column names
    column_names = ['frames_tx', 'frames_rx', 'bytes_tx', 'bytes_rx']
    for column_name in column_names:
        port_results = api.get_port_results(result.PortRequest(
                                            column_names=['name',
                                                          column_name]))
        validate_port_stats_based_on_column_name(port_results,
                                                 column_name,
                                                 f1_packets,
                                                 f2_packets,
                                                 f1_size,
                                                 f2_size)

    # Validation on Flow statistics based on flow names
    flow_names = ['f1', 'f2']
    for flow_name in flow_names:
        flow_results = api.get_flow_results(result.FlowRequest(
                                            flow_names=[flow_name],
                                            column_names=['name']))
        validate_flow_stats_based_on_flow_name(flow_results, flow_name)

    # Validation on Flow statistics based on column names
    column_names = ['frames_tx', 'frames_rx', 'bytes_rx']
    for column_name in column_names:
        flow_results = api.get_flow_results(result.FlowRequest(
                                            column_names=['name',
                                                          column_name]))
        validate_flow_stats_based_on_column_name(flow_results,
                                                 column_name,
                                                 f1_packets,
                                                 f2_packets,
                                                 f1_size,
                                                 f2_size)


def validate_port_stats_based_on_port_name(port_results, port_name):
    """
    Validate stats based on port_names
    """
    for row in port_results:
        assert row['name'] == port_name


def validate_port_stats_based_on_column_name(port_results,
                                             column_name,
                                             f1_packets,
                                             f2_packets,
                                             f1_size,
                                             f2_size):
    """
    Validate Port stats based on column_names
    """

    total_bytes = (f1_packets * f1_size) + (f2_packets * f2_size)
    total_packets = f1_packets + f2_packets
    for row in port_results:
        if row['name'] == 'raw_tx':
            if column_name == 'frames_tx':
                assert row[column_name] == total_packets
            elif column_name == 'bytes_tx':
                assert row[column_name] == total_bytes
        elif row['name'] == 'raw_rx':
            if column_name == 'frames_rx':
                assert row[column_name] == total_packets
            elif column_name == 'bytes_rx':
                assert row[column_name] == total_bytes


def validate_flow_stats_based_on_flow_name(flow_results, flow_name):
    """
    Validate Flow stats based on flow_names
    """
    for row in flow_results:
        assert row['name'] == flow_name


def validate_flow_stats_based_on_column_name(flow_results,
                                             column_name,
                                             f1_packets,
                                             f2_packets,
                                             f1_size,
                                             f2_size):
    """
    Validate Flow stats based on column_names
    """
    for row in flow_results:
        if row['name'] == 'f1':
            if column_name == 'frames_tx':
                assert row[column_name] == f1_packets
            elif column_name == 'frames_rx':
                assert row[column_name] == f1_packets
            elif column_name == 'bytes_rx':
                assert row[column_name] == f1_packets * f1_size
        elif row['name'] == 'f2':
            if column_name == 'frames_tx':
                assert row[column_name] == f2_packets
            elif column_name == 'frames_rx':
                assert row[column_name] == f2_packets
            elif column_name == 'bytes_rx':
                assert row[column_name] == f2_packets * f2_size
