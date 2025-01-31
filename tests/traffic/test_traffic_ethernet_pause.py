def test_traffic_ethernet_pause(api, b2b_raw_config, utils):
    """
    Configure the devices on Tx and Rx Port.
    Configure the flow with devices as end points.
    run the traffic
    Validation,
    - validate the port and flow statistics.
    """

    size = 1518
    packets = 100

    flow = b2b_raw_config.flows[0]
    eth = flow.packet.ethernetpause()[-1]

    eth.src.value = "00:CD:DC:CD:DC:CD"
    eth.dst.value = "00:AB:BC:AB:BC:AB"

    eth.control_op_code.value= 115

    flow.duration.fixed_packets.packets = packets
    flow.size.fixed = size
    flow.rate.percentage = 10
    flow.metrics.enable = True

    utils.start_traffic(api, b2b_raw_config)

