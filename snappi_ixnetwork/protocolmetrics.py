from snappi_ixnetwork.timer import Timer
import time


class ProtocolMetrics(object):
    # Currently paging of the statistic view is not handled
    # TODO Need to enhance when device groups statistics reach
    # more than one page.

    _SUPPORTED_PROTOCOLS_ = ["bgpv4", "bgpv6"]
    _SKIP = True

    _TOPO_STATS = {
        "name": "name",
        "total": "sessions_total",
        "up": "sessions_up",
        "down": "sessions_down",
        "notStarted": "sessions_not_started",
    }

    _RESULT_COLUMNS = {
        "bgpv4": [
            ("name", "Device Group", str),
            ("session_state", "Status", str),
            # TODO session_flap_count can't be added now
            # it needs to be added by creating new view.
            # currently facing an issue in protocol view creation.
            ("session_flap_count", "Session Flap Count", int, _SKIP),
            ("routes_advertised", "Routes Advertised", int),
            ("routes_received", "Routes Rx", int),
            ("route_withdraws_sent", "Routes Withdrawn", int),
            ("route_withdraws_received", "Route Withdraws Rx", int),
            ("updates_sent", "Updates Tx", int),
            ("updates_received", "Updates Rx", int),
            ("opens_sent", "Opens Tx", int),
            ("opens_received", "Opens Rx", int),
            ("keepalives_sent", "KeepAlives Tx", int),
            ("keepalives_received", "KeepAlives Rx", int),
            ("notifications_sent", "Notifications Tx", int),
            ("notifications_received", "Notifications Rx", int),
        ],
        "bgpv6": [
            ("name", "Device Group", str),
            ("session_state", "Status", str),
            # TODO session_flap_count can't be added now
            ("session_flap_count", "Session Flap Count", int, _SKIP),
            ("routes_advertised", "Routes Advertised", int),
            ("routes_received", "Routes Rx", int),
            ("route_withdraws_sent", "Routes Withdrawn", int),
            ("route_withdraws_received", "Route Withdraws Rx", int),
            ("updates_sent", "Updates Tx", int),
            ("updates_received", "Updates Rx", int),
            ("opens_sent", "Opens Tx", int),
            ("opens_received", "Opens Rx", int),
            ("keepalives_sent", "KeepAlives Tx", int),
            ("keepalives_received", "KeepAlives Rx", int),
            ("notifications_sent", "Notifications Tx", int),
            ("notifications_received", "Notifications Rx", int),
        ],
    }

    _PROTO_NAME_MAP_ = {
        "bgpv4": {
            "per_port": "BGP Peer Per Port",
            "drill_down": "BGP Peer Drill Down",
            "drill_down_options": [
                "BGP Peer:Per Device Group",
                "BGP Peer:Per Session",
            ],
            "supported_stats": [s[0] for s in _RESULT_COLUMNS["bgpv4"]],
            "ixn_name": "bgpIpv4Peer",
        },
        "bgpv6": {
            "per_port": "BGP\+ Peer Per Port",
            "drill_down": "BGP\+ Peer Drill Down",
            "drill_down_options": [
                "BGP+ Peer:Per Device Group",
                "BGP+ Peer:Per Session",
            ],
            "supported_stats": [s[0] for s in _RESULT_COLUMNS["bgpv6"]],
            "ixn_name": "bgpIpv6Peer",
        },
    }

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self.ixn = None
        self.columns = []
        self.device_names = []
        self.metric_timeout = 90
        self.interval = 1

    def _get_search_payload(self, parent, child, properties, filters):
        payload = {
            "selects": [
                {
                    "from": parent,
                    "properties": [],
                    "children": [
                        {
                            "child": child,
                            "properties": properties,
                            "filters": filters,
                        }
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "{}/operations/select?xpath=true".format(self.ixn.href)
        return (url, payload)

    def _select_view(self, view_filters=[]):
        url, payload = self._get_search_payload(
            "/statistics", "view", ["caption"], view_filters
        )
        result = self.ixn._connection._execute(url, payload)[0]
        return result.get("view")

    def _wait_for(self, func, exp_msg, interval, timeout):
        end_time = round(time.time()) + timeout
        while True:
            res = func()
            if round(time.time()) >= end_time:
                raise Exception(exp_msg)
            if res is not None:
                return res
            time.sleep(interval)

    def get_supported_protocols(self):
        """
        Return the protocols that are supported currently
        """
        return self._SUPPORTED_PROTOCOLS_

    def _port_list_in_per_port(self, protocol):
        self.ixn = self._api.assistant._ixnetwork
        protocol_name = self._PROTO_NAME_MAP_.get(protocol)
        if protocol_name is None:
            raise NotImplementedError("{} is Not Implemented".format(protocol))
        filter = [
            {
                "property": "caption",
                "regex": "^%s$" % protocol_name["per_port"],
            }
        ]
        view = self._wait_for(
            lambda: self._select_view(filter),
            "could not retrieve the view for %s" % protocol,
            self.interval,
            self.metric_timeout,
        )
        res = self._get_column_values(view[0]["href"], "Port")
        if res is None or len(res) == 0:
            raise Exception("Could not retrieve the Port column")
        return (res, view[0])

    def _get_column_values(self, href, value):
        payload = {"arg1": href, "arg2": value}
        url = "{}/statistics/view/operations/getcolumnvalues".format(
            self.ixn.href
        )
        res = self._api._request("POST", url, payload)
        return res.get("result")

    def _get_value(self, href, row_label, column_label):
        payload = {"arg1": href, "arg2": row_label, "arg3": column_label}
        url = "{}/statistics/view/operations/getvalue".format(self.ixn.href)
        res = self._api._request("POST", url, payload)
        return res.get("result")

    def _check_if_page_ready(self, view):
        count = 0
        while True:
            view.Refresh()
            if view.Data.IsReady:
                break
            if count >= self.metric_timeout:
                raise Exception("View Page is not ready")
            time.sleep(0.5)
            count += 1

    def _port_names_from_devices(self):
        config = self._api.snappi_config
        if len(self.device_names) == 0:
            port_list = [p.name for p in config.ports]
            lag_list = [lag.name for lag in config.lags]
            port_list = port_list + lag_list
            return port_list
        port_list = [
            d.container_name
            for d in config.devices
            if d.name in self.device_names
        ]
        return port_list

    def _do_drill_down(self, view, per_port, row_index, drill_option):
        url, payload = self._get_search_payload(
            view["href"],
            "drillDown",
            ["targetDrillDownOption", "targetRowIndex"],
            [],
        )
        result = self.ixn._connection._execute(url, payload)[0]
        if result.get("drillDown") is None:
            raise Exception("Could not fetch drill down node")

        payload = {
            "targetDrillDownOption": drill_option,
            "targetRowIndex": row_index,
        }
        url = result["drillDown"]["href"]
        count = 0
        while count < 5:
            # retrying as the linux api server throws error for first 2
            # consecutive executions
            try:
                self._api._request("PATCH", url, payload)
                break
            except Exception:
                self._check_if_page_ready(
                    self.ixn.Statistics.View.find(Caption=per_port)
                )
                time.sleep(0.3)
                count += 1

        url = "{}/statistics/view/drillDown/operations/dodrilldown".format(
            self.ixn.href
        )
        payload = {"arg1": result["drillDown"]["href"]}
        self._api._request("POST", url, payload)
        return

    def _get_per_device_group_stats(self, protocol):
        ports, v = self._port_list_in_per_port(protocol)
        config_ports = self._port_names_from_devices()
        indices = set(
            [ports.index(p) for p in list(set(config_ports)) if p in ports]
        )
        drill_option = self._PROTO_NAME_MAP_[protocol]["drill_down_options"][0]
        drill_option2 = self._PROTO_NAME_MAP_[protocol]["drill_down_options"][
            1
        ]
        drill_name = self._PROTO_NAME_MAP_[protocol]["drill_down"]
        per_port = self._PROTO_NAME_MAP_[protocol]["per_port"]
        column_names = self._RESULT_COLUMNS.get(protocol, [])
        row_lst = list()
        for i in indices:
            try:
                drill = self.ixn.Statistics.View.find(Caption=drill_name)
                self._do_drill_down(v, per_port, i, drill_option)
                self._do_drill_down(v, per_port, i, drill_option2)
                self._check_if_page_ready(drill)
            except Exception as e:
                msg = """
                Could not retrive drill down view \
                at row index {} {}""".format(
                    i, e
                )
                raise Exception(msg)
            columns = drill.Data.ColumnCaptions
            drill.Data.PageSize = drill.Data.TotalRows
            values = drill.Data.PageValues
            for value in values:
                row_dt = dict()
                data = dict(zip(columns, value[0]))
                for col in column_names:
                    sn, ixn, typ = col[:3]
                    skip = False if len(col) <= 3 else col[-1]
                    self._set_result_value(row_dt, data, sn, ixn, typ, skip)
                if row_dt != {}:
                    row_lst.append(row_dt)
        return row_lst

    def _update_actual_dev_name(self, data):
        keys = self._api._dev_compacted.keys()
        if data["Device Group"] in keys:
            for k, v in self._api._dev_compacted.items():
                if (
                    data["Device Group"] == v["dev_name"]
                    and int(data["Device#"]) == v["index"] + 1
                ):
                    data["Device Group"] = k
        return data

    def _set_result_value(
        self, row_dt, data, stat_name, ix_name, stat_type=str, skip=False
    ):
        data = self._update_actual_dev_name(data)
        if self.device_names == []:
            self.device_names = [
                d.name for d in self._api.snappi_config.devices
            ]
        if data["Device Group"] not in self.device_names:
            return
        if skip:
            warn = stat_name in self.columns
            self._api.warning(
                "{} metric has no implementation".format(stat_name)
            ) if warn else None
            row_dt[stat_name] = (
                0 if stat_type.__name__ in ["float", "int"] else "na"
            )
        if len(self.columns) == 0 or stat_name in self.columns:
            try:
                row_dt[stat_name] = stat_type(data[ix_name])
                if isinstance(row_dt[stat_name], str):
                    row_dt[stat_name] = row_dt[stat_name].lower()
            except Exception:
                row_dt[stat_name] = (
                    0
                    if stat_type.__name__ in ["float", "int"]
                    else data[ix_name]
                )

    def _topo_stats(self, protocol):
        url = "%s/operations/gettopologystatus" % self.ixn.href
        res = self._api._request("POST", url)
        stats_map = {}
        for d in res["result"]:
            if self._PROTO_NAME_MAP_[protocol]["ixn_name"] not in d["arg1"]:
                continue
            stats_map[d["arg1"]] = {
                self._TOPO_STATS[i["arg1"]]: i["arg2"] for i in d["arg2"]
            }
        myfilter = [
            {
                "property": "name",
                "regex": ".*"
                if len(self.device_names) == 0
                else "^%s$"
                % "|".join(self._api.special_char(self.device_names)),
            }
        ]
        url, payload = self._get_search_payload(
            "/topology", "(?i)^(deviceGroup)$", ["name"], myfilter
        )
        result = self.ixn._connection._execute(url, payload)
        for t in result:
            if t.get("deviceGroup") is None:
                continue
            for d in t["deviceGroup"]:
                for p in stats_map:
                    if d["href"] not in p:
                        continue
                    stats_map[p]["name"] = d["name"]
        if self.device_names == []:
            return [stats_map[p] for p in stats_map]
        return [
            stats_map[p]
            for p in stats_map
            if stats_map["name"] in self.device_names
        ]

    def _filter_stats(self, protocol):
        self.ixn = self._api.assistant._ixnetwork
        f = [
            i
            for i in filter(
                lambda y: y not in self._TOPO_STATS.values(), self.columns
            )
        ]
        if len(f) > 0:
            return self._get_per_device_group_stats(protocol)
        else:
            return self._topo_stats(protocol)

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
        self.device_names = request.get("peer_names")
        if self.device_names is None:
            self.device_names = []
        self.columns = request.get("column_names")
        if self.columns is None or self.columns == []:
            self.columns = self._PROTO_NAME_MAP_[protocol]["supported_stats"]
        if len(self.columns) > 0:
            self.columns.append("name") if "name" not in self.columns else None
            self.columns = list(set(self.columns))
        with Timer(self._api, "Fetching {} Metrics".format(protocol)):
            return self._filter_stats(protocol)
