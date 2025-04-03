from copy import deepcopy


class CustomField(object):
    """
    Implemented All custom field which specify within TrafficItem class
    Best Practice :
        - Please use self._configure_pattern to setting Pattern
    """

    class DummyPattern(object):
        def get(self, value):
            return getattr(self, value)

    @classmethod
    def _process_ipv4_priority(
        cls,
        tr_instance,
        ixn_fields,
        field_names,
        snappi_header,
        priority,
        stacks=None,
    ):
        priority = snappi_header.get(priority, True)
        choice = priority.get("choice")
        field_map = tr_instance._IPV4
        priority_obj = priority.get(choice, True)
        phb = None
        prop_types = sorted(priority_obj._TYPES)
        prop_types.reverse()
        for field in prop_types:
            property = priority_obj.get(field, True)
            if field == "phb":
                phb = property
                field = tr_instance._get_phb_type(property)
            if field == "ecn":
                field = tr_instance._get_phb_type(phb)
                field = "{}-unused".format(field)
            try:
                ind = field_names.index(field_map[field])
            except Exception:
                continue
            tr_instance._config_field_pattern(
                property, ixn_fields[ind], None, True
            )

    @classmethod
    def _process_ethernet_pause(
        cls,
        tr_instance,
        ixn_fields,
        field_names,
        snappi_header,
        ethpause,
        stacks=None,
    ):
        xpath = ixn_fields[0]["xpath"].split("/stack[@alias")[0]
        xpath = "{CE}/stack[@alias = '{HEADER}-{INDEX}']".format(
            CE=xpath, HEADER="custom", INDEX=2
        )
        custom = snappi_header.parent.custom
        control_op_code = tr_instance._get_first_value(
            snappi_header.get("control_op_code", True)
        )

        time = tr_instance._get_first_value(snappi_header.get("time", True))

        custom.bytes = "{:04x}{:x}".format(control_op_code, time)
        tr_instance._append_header(xpath, stacks, custom)

    @classmethod
    def _process_custom_header(
        cls,
        tr_instance,
        ixn_fields,
        field_names,
        snappi_header,
        custom,
        stacks=None,
    ):
        custom_bytes = snappi_header.bytes
        field_map = tr_instance._CUSTOM
        pattern = tr_instance.DummyPattern()
        pattern.choice = "value"
        pattern.value = len(custom_bytes) * 4
        ind = field_names.index(field_map["length"])
        tr_instance._config_field_pattern(pattern, ixn_fields[ind])
        pattern.value = custom_bytes
        ind = field_names.index(field_map["data"])
        tr_instance._config_field_pattern(pattern, ixn_fields[ind])

    def _get_first_value(self, pattern):
        if pattern.choice is None:
            return None
        if pattern.choice == "value":
            value = pattern.value
        elif pattern.choice == "values":
            value = pattern.values[0]
        elif pattern.choice == "counter":
            value = pattern.counter.start
        else:
            value = pattern.random.min
        return value

    def _get_phb_type(self, phb_pattern):
        value = self._get_first_value(phb_pattern)
        phb_type = "default"
        if value is None:
            value = 0
        if value > 0:
            phb_type = "phb" if value % 8 == 0 else "af"
        if value == 46:
            phb_type = "ef"
        return phb_type

    def _gtpv1(self, new_headers, header):
        """"""
        new_headers.append(header)
        gtp_option = deepcopy(header)
        gtp_option.__setattr__("choice", "gtpv1option")
        gtp_option.__setattr__("gtpv1option", header.gtpv1)
        gtp_option.__delattr__("gtpv1")
        new_headers.append(gtp_option)
