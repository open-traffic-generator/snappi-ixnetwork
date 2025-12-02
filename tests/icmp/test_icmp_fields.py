
def test_icmp_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure raw ICMP flows with:
    - fixed pattern for all ICMP fields
    - counter pattern for all ICMP fields
    Validate using utils.validate_config.
    """

    # Fixed values
    icmp_type = 13
    icmp_code = 0
    icmp_checksum = 1234
    icmp_identifier = 1
    icmp_seq_num = 256

    flow1 = b2b_raw_config_vports.flows[0]
    eth, ip, icmp1 = flow1.packet.ethernet().ipv4().icmp()
    icmp_echo1 = icmp1.echo

    eth.src.value = "00:00:0a:00:00:01"
    eth.dst.value = "00:00:0b:00:00:02"
    ip.src.value = "10.1.1.1"
    ip.dst.value = "20.1.1.1"

    icmp_echo1.type.value = icmp_type
    icmp_echo1.code.value = icmp_code
    icmp_echo1.checksum.custom = icmp_checksum
    icmp_echo1.identifier.value = icmp_identifier
    icmp_echo1.sequence_number.value = icmp_seq_num

    # Counter pattern
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name

    eth, ip, icmp2 = flow2.packet.ethernet().ipv4().icmp()
    icmp_echo2 = icmp2.echo
    eth.src.value = "00:00:0a:00:00:01"
    eth.dst.value = "00:00:0b:00:00:02"
    ip.src.value = "10.1.1.1"
    ip.dst.value = "20.1.1.1"

    icmp_echo2.type.increment.start = 0
    icmp_echo2.type.increment.step = 1
    icmp_echo2.type.increment.count = 10

    icmp_echo2.code.increment.start = 0
    icmp_echo2.code.increment.step = 1
    icmp_echo2.code.increment.count = 5

    icmp_echo2.identifier.increment.start = 0
    icmp_echo2.identifier.increment.step = 1
    icmp_echo2.identifier.increment.count = 10

    icmp_echo2.sequence_number.increment.start = 0
    icmp_echo2.sequence_number.increment.step = 1
    icmp_echo2.sequence_number.increment.count = 10

    # Push config
    api.set_config(b2b_raw_config_vports)

    # Validate fixed
    f1_attrs = {
        "Message type": str(icmp_type),
        "Code value": str(icmp_code),
        "ICMP checksum": str(icmp_checksum),
        "Identifier": str(icmp_identifier),
        "Sequence number": str(icmp_seq_num),
    }
    utils.validate_config(api, "f1", "icmpv2", **f1_attrs)

    # Validate counter
    f2_attrs = {
        "Message type": (
            format(icmp_echo2.type.increment.start, "x"),
            str(icmp_echo2.type.increment.step),
            str(icmp_echo2.type.increment.count),
        ),
        "Code value": (
            format(icmp_echo2.code.increment.start, "x"),
            str(icmp_echo2.code.increment.step),
            str(icmp_echo2.code.increment.count),
        ),
        "Identifier": (
            format(icmp_echo2.identifier.increment.start, "x"),
            str(icmp_echo2.identifier.increment.step),
            str(icmp_echo2.identifier.increment.count),
        ),
        "Sequence number": (
            format(icmp_echo2.sequence_number.increment.start, "x"),
            str(icmp_echo2.sequence_number.increment.step),
            str(icmp_echo2.sequence_number.increment.count),
        ),
    }
    utils.validate_config(api, "f2", "icmpv2", **f2_attrs)
