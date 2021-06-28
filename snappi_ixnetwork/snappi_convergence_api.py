import re
import time
from collections import namedtuple
from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.timer import Timer

try:
    import snappi_convergence
except Exception:
    raise SnappiIxnException(500, "snappi_convergence not installed")
from snappi_ixnetwork.snappi_api import Api as snappiApi


class Api(snappi_convergence.Api):
    _CONVERGENCE = {
        ("data_plane_convergence_us", "DP/DP Convergence Time (us)", float),
        (
            "control_plane_data_plane_convergence_us",
            "CP/DP Convergence Time (us)",
            float,
        ),
    }

    _EVENT = {
        ("begin_timestamp_ns", "Event Start Timestamp", int),
        ("end_timestamp_ns", "Event End Timestamp", int),
    }

    def __init__(self, **kwargs):

        self._convergence_timeout = 10
        self._api = snappiApi(**kwargs)
        self._event_info = None

    def set_config(self, payload):
        try:
            cvg_config = self.convergence_config()
            if isinstance(payload, (type(cvg_config), str)) is False:
                raise TypeError(
                    "The content must be of type Union[Config, str]"
                )

            if isinstance(payload, str) is True:
                payload = cvg_config.deserialize(payload)
            config = payload.get("config")
            if config is None:
                raise Exception("config should not None")
            self._api.config_ixnetwork(config)
            rx_rate_threshold = payload.get("rx_rate_threshold")
            ixn_CpdpConvergence = self._api._traffic.Statistics.CpdpConvergence
            if rx_rate_threshold is not None:
                if self._api.traffic_item.has_latency is True:
                    raise Exception(
                        "We are supporting either latency or rx_rate_threshold"
                    )
                ixn_CpdpConvergence.Enabled = True
                ixn_CpdpConvergence.EnableControlPlaneEvents = True
                ixn_CpdpConvergence.EnableDataPlaneEventsRateMonitor = True
                ixn_CpdpConvergence.DataPlaneThreshold = rx_rate_threshold
            else:
                ixn_CpdpConvergence.Enabled = False
            for ixn_traffic_item in self._api._traffic_item.find():
                ixn_traffic_item.Tracking.find()[0].TrackBy = [
                    "destEndpoint0",
                    "destSessionDescription0",
                ]
        except Exception as err:
            raise SnappiIxnException(err)
        app_errors = self._api._globals.AppErrors.find()
        bad_requests = []
        if len(app_errors) > 0:
            current_errors = app_errors[0].Error.find()
            if len(current_errors) > 0:
                for error in current_errors:
                    if error.Name == "JSON Import Issues":
                        bad_requests = [
                            instance.SourceValues[0]
                            for instance in error.Instance.find()
                        ]
        if bad_requests:
            if len(bad_requests) == 1:
                raise SnappiIxnException(
                    400, "Bad request error: {}".format(bad_requests[0])
                )
            raise SnappiIxnException(400, "Bad request errors:", bad_requests)
        return self._request_detail()

    def set_state(self, payload):
        try:
            cvg_state = self.convergence_state()
            if isinstance(payload, (type(cvg_state), str)) is False:
                raise TypeError(
                    "The content must be of type Union[LinkState, str]"
                )
            if isinstance(payload, str):
                payload = cvg_state.deserialize(payload)
            self._api._connect()
            if payload.choice is None:
                raise Exception("state [transmit/ link/ route] must configure")
            event_names = []
            event_state = None
            event_type = payload.choice
            EventInfo = namedtuple(
                "EventInfo", ["event_type", "event_state", "event_names"]
            )
            if payload.choice == "transmit":
                transmit = payload.transmit
                self._api.traffic_item.transmit(transmit)
            elif payload.choice == "link":
                link = payload.link
                if link.port_names is not None:
                    event_names = link.port_names
                    event_state = link.state
                    self._api.vport.set_link_state(link)
            elif payload.choice == "route":
                route = payload.route
                event_state = route.state
                with Timer(self._api, "Setting route state"):
                    event_names = self._api.ngpf.set_route_state(route)
            else:
                raise Exception(
                    "These[transmit/ link/ route] are valid convergence_state"
                )
            self._event_info = EventInfo(event_type, event_state, event_names)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def get_results(self, payload):
        try:
            self._api._connect()
            cvg_req = self.convergence_request()
            if isinstance(payload, (type(cvg_req), str)) is False:
                raise TypeError(
                    "The content must be of type Union[MetricsRequest, str]"
                )
            if isinstance(payload, str) is True:
                payload = cvg_req.deserialize(payload)
            if payload.choice is None:
                raise Exception("state [metrics/ convergence] must configure")
            cvg_res = self.convergence_response()
            if payload.choice == "metrics":
                response = self._api.traffic_item.results(payload.metrics)
                cvg_res.flow_metric.deserialize(response)
            elif payload.choice == "convergence":
                response = self._result(payload.convergence)
                cvg_res.flow_convergence.deserialize(response)
            elif (
                payload.choice
                in self._api.protocol_metrics.get_supported_protocols()
            ):
                response = self._api.protocol_metrics.results(payload)
                getattr(cvg_res, payload.choice + "_metrics").deserialize(
                    response
                )
            else:
                raise Exception(
                    "These[metrics/ convergence] are valid convergence_request"
                )
            return cvg_res
        except Exception as err:
            raise SnappiIxnException(err)

    def _request_detail(self):
        request_detail = self.response_warning()
        errors = self._api._errors
        warnings = list()
        app_errors = self._api._globals.AppErrors.find()
        if len(app_errors) > 0:
            current_errors = app_errors[0].Error.find()
            if len(current_errors) > 0:
                for error in current_errors:
                    # Add loop as sequence are not sorted
                    match = [
                        o
                        for o in self._api._ixn_errors
                        if o.Name == error.Name
                        and o.LastModified == error.LastModified
                    ]
                    if len(match) == 0:
                        if error.ErrorLevel == "kWarning":
                            warnings.append(
                                "IxNet - {0}".format(error.Description)
                            )
                        if error.ErrorLevel == "kError":
                            errors.append(
                                "IxNet - {0}".format(error.Description)
                            )
        # request_detail.errors = errors
        if len(errors) > 0:
            self._api._errors = []
            raise SnappiIxnException(500, errors)
        request_detail.warnings = warnings
        return request_detail

    def _result(self, request):
        flow_names = request.get("flow_names")
        if not isinstance(flow_names, list):
            msg = "Invalid format of flow_names passed {},\
                                                expected list".format(
                flow_names
            )
            raise Exception(msg)
        if flow_names is None or len(flow_names) == 0:
            flow_names = [flow.name for flow in self._api.snappi_config.flows]
        flow_rows = self._get_flow_rows(flow_names)
        traffic_stat = self._api.assistant.StatViewAssistant(
            "Traffic Item Statistics"
        )
        traffic_index = {}
        drill_down_option = "Drill down per Dest Endpoint"
        for index, row in enumerate(
            self._get_traffic_rows(traffic_stat, drill_down_option)
        ):
            traffic_index[row["Traffic Item"]] = index
        response = []
        for flow_name in flow_names:
            convergence = {"name": flow_name}
            if flow_name not in traffic_index.keys():
                raise Exception("Somehow flow %s is missing" % flow_name)

            drill_down_options = traffic_stat.DrillDownOptions()
            drilldown_index = drill_down_options.index(drill_down_option)
            drill_down = traffic_stat.Drilldown(
                traffic_index[flow_name],
                drill_down_option,
                traffic_stat.TargetRowFilters()[drilldown_index],
            )
            drill_down_result = drill_down.Rows[0]
            for (
                external_name,
                internal_name,
                external_type,
            ) in self._CONVERGENCE:
                self._set_result_value(
                    convergence,
                    external_name,
                    drill_down_result[internal_name],
                    external_type,
                )

            events = []
            interruption_time = None
            for flow_result in flow_rows:
                if flow_result["Traffic Item"] != flow_name:
                    continue
                convergence["port_tx"] = flow_result["Tx Port"]
                convergence["port_rx"] = flow_result["Rx Port"]
                event_name = flow_result["Event Name"]
                if event_name == "":
                    continue
                event = self._get_event(event_name, flow_result)
                for external_name, internal_name, external_type in self._EVENT:
                    value = int(flow_result[internal_name].split(".")[-1])
                    self._set_result_value(
                        event, external_name, value * 1000, external_type
                    )
                events.append(event)
                if interruption_time is None:
                    interruption_time = float(
                        flow_result["DP Above Threshold Timestamp"].split(":")[
                            -1
                        ]
                    ) - float(
                        flow_result["DP Below Threshold Timestamp"].split(":")[
                            -1
                        ]
                    )
                    self._set_result_value(
                        convergence,
                        "service_interruption_time_us",
                        interruption_time,
                        float,
                    )
            convergence["events"] = events
            response.append(convergence)
        return response

    def _get_event(self, event_name, flow_result):
        event = {}
        if re.search(r"Port Link Up", event_name):
            if flow_result["Tx Port"] in self._event_info.event_names:
                event["source"] = flow_result["Tx Port"]
            elif flow_result["Rx Port"] in self._event_info.event_names:
                event["source"] = flow_result["Rx Port"]
            else:
                self._api.warning("Not find any event source")
                event["source"] = ""
            if self._event_info.event_state == "up":
                event["type"] = "link_up"
            else:
                event["type"] = "link_down"
        else:
            for route_name in self._api.ixn_route_objects.keys():
                if re.search(route_name, event_name) is not None:
                    event["source"] = route_name
                    event_type = event_name.split(route_name)[-1]
                    if event_type.strip().lower() == "disable":
                        event_type = "route_withdraw"
                    else:
                        event_type = "route_advertise"
                    event["type"] = event_type
                    break
        return event

    def _set_result_value(
        self, row, column_name, column_value, column_type=str
    ):
        try:
            row[column_name] = column_type(column_value)
        except:
            if column_type.__name__ in ["float", "int"]:
                row[column_name] = 0
            else:
                row[column_type] = column_value

    def _get_traffic_rows(self, traffic_stat, drill_down_option):
        count = 0
        sleep_time = 0.5
        while True:
            has_event = False
            drill_down_options = traffic_stat.DrillDownOptions()
            if drill_down_option in drill_down_options:
                has_event = True
                break
            if has_event is True:
                break
            if count * sleep_time > self._convergence_timeout:
                raise Exception(
                    "Somehow 'Drill down per Dest Endpoint' not available"
                )
            time.sleep(sleep_time)
            count += 1
        return traffic_stat.Rows

    def _get_flow_rows(self, flow_names):
        count = 0
        sleep_time = 0.5
        flow_stat = self._api.assistant.StatViewAssistant("Flow Statistics")
        has_flow = False
        while True:
            flow_rows = flow_stat.Rows
            has_event = False
            for row in flow_rows:
                if row["Traffic Item"] in flow_names:
                    has_flow = True
                    if row["Event Name"] != "":
                        has_event = True
                        break
            if has_event is True:
                break
            if count * sleep_time > self._convergence_timeout:
                if has_flow is not True:
                    raise Exception(
                        "flow_names must present within in config.flows"
                    )
                else:
                    raise Exception("Somehow event is not reflected in stat")
            time.sleep(sleep_time)
            count += 1
        return flow_rows
