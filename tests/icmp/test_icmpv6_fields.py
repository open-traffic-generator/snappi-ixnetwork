def test_icmpv6_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure raw ICMPv6 flows with ,
    - fixed pattern for the fields
    - counter pattern for the fields

    Validate,
    - Fetch the ICMPv6 header config via restpy and validate
      against expected
    """
    # fixed
    icmpv6_type = 128
    icmpv6_code = 0
    icmpv6_identifier = 1
    icmpv6_seq_num = 256    
    icmpv6_checksum = 1234

    flow1 = b2b_raw_config_vports.flows[0]
    src = "00:0C:29:E3:53:EA"
    dst = "00:0C:29:E3:53:F4"

    eth, ipv6, icmpv61 = flow1.packet.ethernet().ipv6().icmpv6()
    icmpv6_echo1 = icmpv61.echo
    eth.src.value = src
    eth.dst.value = dst
    ipv6.src.value = "2001::1"
    ipv6.dst.value = "2002::1"

    icmpv6_echo1.type.value = icmpv6_type
    icmpv6_echo1.code.value = icmpv6_code
    icmpv6_echo1.identifier.value = icmpv6_identifier
    icmpv6_echo1.sequence_number.value = icmpv6_seq_num
    icmpv6_echo1.checksum.custom = icmpv6_checksum
    
    # fixed validation
    f1_attrs = {
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.messageType": str(icmpv6_type),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.code": str(icmpv6_code),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.checksum": str(icmpv6_checksum),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.identifier": str(icmpv6_identifier),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.sequenceNumber": str(icmpv6_seq_num),
    }

    # counter
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    
    eth, ipv6, icmpv62 = flow2.packet.ethernet().ipv6().icmpv6()
    icmpv6_echo2 = icmpv62.echo
    eth.src.value = src
    eth.dst.value = dst
    ipv6.src.value = "2001::1"
    ipv6.dst.value = "2002::1"

    icmpv6_echo2.type.increment.start = 0
    icmpv6_echo2.type.increment.step = 1
    icmpv6_echo2.type.increment.count = 10

    icmpv6_echo2.code.increment.start = 0
    icmpv6_echo2.code.increment.step = 1
    icmpv6_echo2.code.increment.count = 5

    icmpv6_echo2.identifier.increment.start = 0
    icmpv6_echo2.identifier.increment.step = 1
    icmpv6_echo2.identifier.increment.count = 10

    icmpv6_echo2.sequence_number.increment.start = 0
    icmpv6_echo2.sequence_number.increment.step = 1
    icmpv6_echo2.sequence_number.increment.count = 10

    # counter validation
    f2_attrs = {
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.messageType": (
            format(icmpv6_echo2.type.increment.start, "x"),
            str(icmpv6_echo2.type.increment.step),
            str(icmpv6_echo2.type.increment.count),
        ),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.code": (
            format(icmpv6_echo2.code.increment.start, "x"),
            str(icmpv6_echo2.code.increment.step),
            str(icmpv6_echo2.code.increment.count),
        ),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.identifier": (
            format(icmpv6_echo2.identifier.increment.start, "x"),
            str(icmpv6_echo2.identifier.increment.step),
            str(icmpv6_echo2.identifier.increment.count),
        ),
        "icmpv6.icmpv6Message.icmpv6MessegeType.echoRequestMessage.sequenceNumber": (
            format(icmpv6_echo2.sequence_number.increment.start, "x"),
            str(icmpv6_echo2.sequence_number.increment.step),
            str(icmpv6_echo2.sequence_number.increment.count),
        ),
    }

    api.set_config(b2b_raw_config_vports)

    utils.validate_config(api, "f1", "icmpv6", **f1_attrs)
    utils.validate_config(api, "f2", "icmpv6", **f2_attrs)
