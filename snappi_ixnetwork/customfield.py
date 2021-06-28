from copy import deepcopy


class CustomField(object):
    """
    Implemented All custom field which specify within TrafficItem class
    Best Practice :
        - Please use self._configure_pattern to setting Pattern
    """

    _IPv4_DSCP_PHB = {
        "0": "ipv4.header.priority.ds.phb.defaultPHB.defaultPHB",
        "8": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "16": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "24": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "32": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "40": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "48": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "56": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "10": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "12": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "14": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "18": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "20": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "22": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "26": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "28": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "30": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "34": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "36": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "38": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "46": "ipv4.header.priority.ds.phb.expeditedForwardingPHB.expeditedForwardingPHB",
    }

    _IPv4_DSCP_ECN = {
        "ipv4.header.priority.ds.phb.defaultPHB.defaultPHB": "ipv4.header.priority.ds.phb.defaultPHB.unused",
        "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB": "ipv4.header.priority.ds.phb.classSelectorPHB.unused",
        "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB": "ipv4.header.priority.ds.phb.assuredForwardingPHB.unused",
        "ipv4.header.priority.ds.phb.expeditedForwardingPHB.expeditedForwardingPHB": "ipv4.header.priority.ds.phb.expeditedForwardingPHB.unused",
    }

    _ETHERNETPAUSE = {
        "dst": "ethernet.header.destinationAddress",
        "src": "ethernet.header.sourceAddress",
        "ether_type": "ethernet.header.etherType",
        "control_op_code": "custom.header.length",
        "time": "custom.header.data",
    }

    def _ipv4_priority(self, ixn_field, priority):
        if priority.choice == "dscp":
            field_type_id = None
            first_value = str(self._get_first_value(priority.dscp.phb))
            if first_value in CustomField._IPv4_DSCP_PHB:
                field_type_id = CustomField._IPv4_DSCP_PHB[first_value]
            else:
                field_type_id = CustomField._IPv4_DSCP_PHB["0"]
            if field_type_id is not None:
                self._configure_pattern(
                    ixn_field,
                    field_type_id,
                    priority.dscp.phb,
                    field_choice=True,
                )
                field_type_id = CustomField._IPv4_DSCP_ECN[field_type_id]
                self._configure_pattern(
                    ixn_field,
                    field_type_id,
                    priority.dscp.ecn,
                    field_choice=True,
                )
        elif priority.choice == "tos":
            self._configure_field(ixn_field, priority, field_choice=True)
        else:
            self._configure_pattern(
                ixn_field,
                "ipv4.header.priority.raw",
                priority.raw,
                field_choice=True,
            )

    def _get_first_value(self, phb_pattern):
        if phb_pattern.choice is None:
            return None
        if phb_pattern.choice == "value":
            value = phb_pattern.value
        elif phb_pattern.choice == "values":
            value = phb_pattern.values[0]
        elif phb_pattern.choice == "counter":
            value = phb_pattern.counter.start
        else:
            value = phb_pattern.random.min
        return value

    def adjust_header(self, headers):
        """"""
        new_headers = list()
        for header in headers:
            header = header.parent
            if header.choice == "ethernetpause":
                self._ethernet_pause(
                    new_headers, headers, header.ethernetpause
                )
            elif header.choice == "gtpv1":
                self._gtpv1(new_headers, header)
            else:
                new_headers.append(header)
        return new_headers

    def _ethernet_pause(self, new_headers, headers, ethernetpause):
        """Current IxNetwork 9.10 do not have Global Pause support.
        Therefore using Ether > Custom header as work around.
        We will remove these code and add EthernetPause in generic section.
        The implementation will only support fixed patterns for
        control_op_code and time
        """
        ethpause = deepcopy(ethernetpause)
        headers.clear()
        eth = headers.ethernet()[-1]
        cust = headers.custom()[-1]
        new_headers.append(eth.parent)
        new_headers.append(cust.parent)
        if ethpause._properties.get("src") is not None:
            eth.src.deserialize(ethpause.src.serialize("dict"))
        else:
            eth.src.value = "00:00:aa:00:00:01"
        if ethpause._properties.get("dst") is not None:
            eth.dst.deserialize(ethpause.dst.serialize("dict"))
        else:
            eth.dst.value = "01:80:c2:00:00:01"
        if ethpause._properties.get("ether_type") is not None:
            eth.ether_type.deserialize(ethpause.ether_type.serialize("dict"))
        else:
            eth.ether_type.value = "8808"
        if ethpause._properties.get("control_op_code") is not None:
            control_op_code = self._get_first_value(
                ethpause.control_op_code
            ).zfill(4)
        else:
            control_op_code = "0001"
        if ethpause._properties.get("time") is not None:
            time = self._get_first_value(ethpause.time).zfill(4)
        else:
            time = "FFFF"
        cust.bytes = "{0}{1}".format(control_op_code, time)

    def _gtpv1(self, new_headers, header):
        """"""
        new_headers.append(header)
        gtp_option = deepcopy(header)
        gtp_option.__setattr__("choice", "gtpv1option")
        gtp_option.__setattr__("gtpv1option", header.gtpv1)
        gtp_option.__delattr__("gtpv1")
        new_headers.append(gtp_option)

    def _custom_headers(self, ixn_field, packet):
        if packet.bytes is not None:
            ixn_custom_length = ixn_field.find(
                FieldTypeId="custom.header.length"
            )
            ixn_custom_length.update(
                Auto=False,
                ValueType="singleValue",
                SingleValue=len(packet.bytes) * 4,
            )
            ixn_custom_data = ixn_field.find(FieldTypeId="custom.header.data")
            ixn_custom_data.update(
                Auto=False, ValueType="singleValue", SingleValue=packet.bytes
            )
