from snappi_ixnetwork.timer import Timer


class ProtocolMetrics(object):
    # Currently paging of the statistic view is not handled
    # TODO Need to enhance when device groups statistics reach
    # more than one page.

    _SUPPORTED_PROTOCOLS_ = [
        "bgpv4"
    ]
    _PROTO_NAME_MAP_ = {
        "bgpv4": 'BGP Peer Per Port',
        "bgpv4_drill": 'BGP Peer Drill Down'
    }

    _RESULT_COLUMNS = {
        "bgpv4": [
            ("name", "Device Group", str),
            ("sessions_total", "Sessions Total", int),
            ("sessions_up", "Sessions Up", int),
            ("sessions_down", "Sessions Down", int),
            ("sessions_not_started", "Sessions Not Started", int),
            ("routes_advertised", "Routes Advertised", int),
            ("routes_withdrawn", "Routes Withdrawn", int),
        ]
    }

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self.columns = []
        self.device_names = []

    def get_supported_protocols(self):
        """
        Return the protocols that are supported currently
        """
        return self._SUPPORTED_PROTOCOLS_

    def _get_per_port_stat_view(self, protocol):
        protocol_name = self._PROTO_NAME_MAP_.get(protocol)
        if protocol_name is None:
            raise NotImplementedError(
                "{} is Not Implemented".format(protocol)
            )
        try:
            table = self._api.assistant.StatViewAssistant(protocol_name, 10)
        except Exception:
            msg = "Could not retrieve stats view for {}\
                make sure the protocol is up and running".format(protocol)
            raise Exception(msg)
        drill_option = [
            opt for opt in table.DrillDownOptions()
            if 'Device Group' in opt
        ]
        if len(drill_option) == 0:
            raise LookupError("Could not fetch drill down option")
        table._View.DrillDown.find().TargetDrillDownOption = drill_option[0]
        return table

    def _get_per_device_group_stats(self, protocol):
        table = self._get_per_port_stat_view(protocol)
        v = table._View
        column_names = self._RESULT_COLUMNS.get(protocol)
        row_lst = list()
        for row in range(len(table.Rows)):
            try:
                v.DrillDown.find().TargetRowIndex = row
                v.DrillDown.find().DoDrillDown()
                drill = self._api.assistant.StatViewAssistant(
                    self._PROTO_NAME_MAP_.get(protocol + '_drill')
                )
            except Exception as e:
                msg = 'Could not retrive drill down view at row index %s'\
                    % (row)
                raise Exception(msg + e)
            for dev_row in drill.Rows:
                dev_name = dev_row['Device Group']
                if len(self.names) > 0 and dev_name not in self.names:
                    continue
                row_dt = dict()
                for sn, ixn, typ in column_names:
                    try:
                        value = dev_row[ixn]
                    except Exception:
                        value = 'NA'
                    self._set_result_value(
                        row_dt, sn, value, typ
                    )
                row_lst.append(row_dt)
        return row_lst

    def _set_result_value(self, row_dt, stat_name, stat_value, stat_type=str):
        if len(self.columns) == 0 or stat_name in self.columns:
            try:
                row_dt[stat_name] = stat_type(stat_value)
            except Exception:
                row_dt[stat_name] = 0 \
                    if stat_type.__name__ in ['float', 'int'] else stat_value

    def results(self, request):
        """
        Return the Protocol statistics
        args:
            request: <type obj> MetricRequest object
            protocol: <type str> protocol name
        *Note: supported protocols can be fetched via,
        self.get_supported_protocols()
        """
        protocol = request.choice
        request = getattr(request, protocol)
        self.names = request._properties.get('device_names')
        if self.names is None:
            self.names = []
        self.columns = request._properties.get('column_names')
        if self.columns is None:
            self.columns = []
        if len(self.columns) > 0:
            self.columns.append('name')
            self.columns = list(set(self.columns))
        with Timer(self._api, "Fetching {} Metrics".format(protocol)):
            return self._get_per_device_group_stats(protocol)
