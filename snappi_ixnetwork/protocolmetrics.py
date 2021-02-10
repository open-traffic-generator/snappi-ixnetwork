from snappi_ixnetwork.timer import Timer
import time


class ProtocolMetrics(object):
    # Currently paging of the statistic view is not handled
    # TODO Need to enhance when device groups statistics reach
    # more than one page.

    _SUPPORTED_PROTOCOLS_ = [
        "bgpv4"
    ]
    _PROTO_NAME_MAP_ = {
        "bgpv4": {
            'per_port': 'BGP Peer Per Port',
            'drill_down': 'BGP Peer Drill Down',
            'drill_down_options': [
                'BGP Peer:Per Device Group', 'BGP Peer:Per Session'
            ]
        }
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
        self.metric_timeout = 90

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
            table = self._api.assistant.StatViewAssistant(
                protocol_name['per_port'], self.metric_timeout
            )
        except Exception:
            msg = "Could not retrieve stats view for {}\
                make sure the protocol is up and running".format(protocol)
            raise Exception(msg)
        return table

    def _check_if_page_ready(self, view):
        count = 0
        while True:
            if view.Data.IsReady:
                break
            if count >= self.metric_timeout:
                raise Exception("View Page is not ready")
            time.sleep(0.5)
            count += 1

    def _get_per_device_group_stats(self, protocol):
        table = self._get_per_port_stat_view(protocol)
        table_len = len(table.Rows)
        v = table._View
        self._check_if_page_ready(v)
        drill_option = self._PROTO_NAME_MAP_[protocol]['drill_down_options'][0]
        per_port = self._PROTO_NAME_MAP_[protocol]['per_port']
        drill_name = self._PROTO_NAME_MAP_[protocol]['drill_down']
        column_names = self._RESULT_COLUMNS.get(protocol)
        row_lst = list()
        for row in range(table_len):
            try:
                v = v.find(Caption=per_port)
                v.DrillDown.find().TargetRowIndex = row
                v.DrillDown.find().TargetDrillDownOption = drill_option
                v.DrillDown.find().DoDrillDown()
                v.find(Caption=drill_name).Refresh()
                v.find(Caption=drill_name).Refresh()
                time.sleep(0.5)
                drill = self._api.assistant.StatViewAssistant(
                    drill_name, self.metric_timeout
                )
            except Exception as e:
                msg = """"
                Could not retrive drill down view at row index {} {}""".format(
                    row, e
                )
                raise Exception(msg)
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
