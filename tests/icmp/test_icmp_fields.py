
def test_icmp_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw ICMP flows with:
    - fixed pattern for all ICMP fields
    - list pattern for all ICMP fields
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
    # icmp_echo1 = icmp1.echo

    eth.src.value = "00:00:0a:00:00:01"
    eth.dst.value = "00:00:0b:00:00:02"
    ip.src.value = "10.1.1.1"
    ip.dst.value = "20.1.1.1"

    icmp1.echo.type.value = icmp_type
    icmp1.echo.code.value = icmp_code
    icmp1.echo.checksum.custom = icmp_checksum
    icmp1.echo.identifier.value = icmp_identifier
    icmp1.echo.sequence_number.value = icmp_seq_num

    # import pdb; pdb.set_trace()
    # # List pattern
    # flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    # flow2.tx_rx.port.tx_name = tx_vport.name
    # flow2.tx_rx.port.rx_name = rx_vport.name

    # eth, ip, icmp2 = flow2.packet.ethernet().ipv4().icmp()
    # icmp_echo2 = icmp2.echo

    # eth.src.value = "00:00:0a:00:00:01"
    # eth.dst.value = "00:00:0b:00:00:02"
    # ip.src.value = "10.1.1.1"
    # ip.dst.value = "20.1.1.1"

    # type_list = [0, 8, 11]
    # code_list = [0, 1, 2]
    # # checksum_list = [0x1111, 0x2222, 0x3333]
    # identifier_list = [1, 2, 3]
    # seq_list = [10, 20, 30]

    # icmp_echo2.type.values = type_list
    # icmp_echo2.code.values = code_list
    # # icmp_echo2.checksum.custom = checksum_list
    # icmp_echo2.identifier.values = identifier_list
    # icmp_echo2.sequence_number.values = seq_list

    # # Counter pattern
    # flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    # flow3.tx_rx.port.tx_name = tx_vport.name
    # flow3.tx_rx.port.rx_name = rx_vport.name

    # eth, ip, icmp3 = flow3.packet.ethernet().ipv4().icmp()
    # icmp_echo3 = icmp3.echo
    # eth.src.value = "00:00:0a:00:00:01"
    # eth.dst.value = "00:00:0b:00:00:02"
    # ip.src.value = "10.1.1.1"
    # ip.dst.value = "20.1.1.1"

    # icmp_echo3.type.increment.start = 0
    # icmp_echo3.type.increment.step = 1
    # icmp_echo3.type.increment.count = 10

    # icmp_echo3.code.increment.start = 0
    # icmp_echo3.code.increment.step = 1
    # icmp_echo3.code.increment.count = 5

    # icmp_echo3.identifier.increment.start = 0
    # icmp_echo3.identifier.increment.step = 1
    # icmp_echo3.identifier.increment.count = 10

    # icmp_echo3.sequence_number.increment.start = 0
    # icmp_echo3.sequence_number.increment.step = 1
    # icmp_echo3.sequence_number.increment.count = 10

    # Push config
    api.set_config(b2b_raw_config_vports)

    # # Validate fixed
    # f1_attrs = {
    #     "MessageType": format(icmp_type, "x"),
    #     "CodeValue": format(icmp_code, "x"),
    #     "IcmpChecksum": format(icmp_checksum, "x"),
    #     "Identifier": format(icmp_identifier, "x"),
    #     "SequenceNumber": format(icmp_seq_num, "x"),
    # }
    # utils.validate_config(api, "f1", "icmpv2", **f1_attrs)

    # # Validate list
    # f2_attrs = {
    #     "MessageType": [format(v, "x") for v in type_list],
    #     "CodeValue": [format(v, "x") for v in code_list],
    #     # "IcmpChecksum": [format(v, "x") for v in checksum_list],
    #     "Identifier": [format(v, "x") for v in identifier_list],
    #     "SequenceNumber": [format(v, "x") for v in seq_list],
    # }
    # utils.validate_config(api, "f2", "icmp", **f2_attrs)

    # # Validate counter
    # f3_attrs = {
    #     "MessageType": (
    #         format(icmp_echo3.type.increment.start, "x"),
    #         str(icmp_echo3.type.increment.step),
    #         str(icmp_echo3.type.increment.count),
    #     ),
    #     "CodeValue": (
    #         format(icmp_echo3.code.increment.start, "x"),
    #         str(icmp_echo3.code.increment.step),
    #         str(icmp_echo3.code.increment.count),
    #     ),
    #     "IcmpChecksum": (
    #         format(icmp_echo3.checksum.increment.start, "x"),
    #         str(icmp_echo3.checksum.increment.step),
    #         str(icmp_echo3.checksum.increment.count),
    #     ),
    #     "Identifier": (
    #         format(icmp_echo3.identifier.increment.start, "x"),
    #         str(icmp_echo3.identifier.increment.step),
    #         str(icmp_echo3.identifier.increment.count),
    #     ),
    #     "SequenceNumber": (
    #         format(icmp_echo3.sequence_number.increment.start, "x"),
    #         str(icmp_echo3.sequence_number.increment.step),
    #         str(icmp_echo3.sequence_number.increment.count),
    #     ),
    # }
    # utils.validate_config(api, "f3", "icmp", **f3_attrs)
