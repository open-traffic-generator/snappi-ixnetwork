import json
import re
import time
import logging
from collections import namedtuple

import snappi
from ixnetwork_restpy import TestPlatform, SessionAssistant

from snappi_ixnetwork.logger import setup_ixnet_logger
from snappi_ixnetwork.capture import Capture
from snappi_ixnetwork.device.ngpf import Ngpf
from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.lag import Lag
from snappi_ixnetwork.objectdb import IxNetObjects
from snappi_ixnetwork.ping import Ping
from snappi_ixnetwork.protocolmetrics import ProtocolMetrics
from snappi_ixnetwork.resourcegroup import ResourceGroup
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.trafficitem import TrafficItem
from snappi_ixnetwork.validation import Validation
from snappi_ixnetwork.vport import Vport
from snappi_ixnetwork.ixnetworkconfig import IxNetworkConfig
from snappi_ixnetwork.device.mka import Mka
from snappi_ixnetwork.device.macsec import Macsec


class Api(snappi.Api):
    """IxNetwork implementation of the abstract-open-traffic-generator package

    Args
    ----
    - address (str): The address of the IxNetwork API Server
    - port (str): The rest port of the IxNetwork API Server
    - username (str): The username for Linux IxNetwork API Server
        This is not required when connecting to single session environments
    - password (str): The password for Linux IxNetwork API Server
        This is not required when connecting to single session environments
    """

    _CONVERGENCE = {
        ("data_plane_convergence_us", "DP/DP Convergence Time (us)", float),
        (
            "control_plane_data_plane_convergence_us",
            "CP/DP Convergence Time (us)",
            float,
        ),
    }

    _DP_CONVERGENCE = {
        ("data_plane_convergence_us", "DP/DP Convergence Time (us)", float),
    }

    _EVENT = {
        ("begin_timestamp_ns", "Event Start Timestamp", int),
        ("end_timestamp_ns", "Event End Timestamp", int),
    }

    _TRIGGERED_EVENT = ""

    def __init__(self, **kwargs):
        """Create a session
        - address (str): The ip address of the TestPlatform to connect to
        where test sessions will be created or connected to.
        - port (str): The rest port of the TestPlatform to connect to.
        - username (str): The username to be used for authentication
        - password (str): The password to be used for authentication
        """
        super(Api, self).__init__()
        location = kwargs.get("location")
        username = kwargs.get("username")
        password = kwargs.get("password")
        license_servers = kwargs.get("license_servers")
        self._log_level = (
            logging.INFO
            if kwargs.get("loglevel") is None
            else kwargs.get("loglevel")
        )
        self.logger = setup_ixnet_logger(self.log_level, module_name=__name__)
        location = "https://127.0.0.1:11009" if location is None else location
        self._address, self._port = self._get_addr_port(location)
        self._username = "admin" if username is None else username
        self._password = "admin" if password is None else password
        self._license_servers = (
            [] if license_servers is None else license_servers
        )
        self._running_config = None
        self._config = None
        self._assistant = None
        self._ixn_errors = list()
        self._config_objects = {}
        self._device_traffic_endpoint = {}
        self._device_encap = {}
        self.ixn_objects = None
        self._config_type = self.config()
        self._control_state = self.control_state()
        self._control_action = self.control_action()
        self._flows_update = self.config_update()
        self._flows_delete = self.config_delete()
        self._flows_append = self.config_append()
        self._capture_request = self.capture_request()
        self.ixn_routes = []
        self.validation = Validation(self)
        self.vport = Vport(self)
        self.lag = Lag(self)
        self.ngpf = Ngpf(self)
        self.traffic_item = TrafficItem(self)
        self.capture = Capture(self)
        self.ping = Ping(self)
        self.protocol_metrics = ProtocolMetrics(self)
        self.resource_group = ResourceGroup(self)
        self.do_compact = False
        self._dev_compacted = {}
        self._previous_errors = []
        self._initial_flows_config = None
        self._flow_tracking = False
        self._convergence_timeout = 3
        self._event_info = None
        self._ixnet_specific_config = None
        self._mka = Mka(self)
        self._macsec = Macsec(self)

        self._ixn_route_info = namedtuple(
            "IxnRouteInfo", ["ixn_obj", "index", "multiplier"]
        )

    def _get_addr_port(self, host):
        items = host.split("/")
        items = items[-1].split(":")

        addr = items[0]
        if len(items) == 2:
            return addr, items[-1]
        else:
            if host.startswith("https"):
                return addr, "443"
            else:
                return addr, "80"

    @property
    def log_level(self):
        return self._log_level

    def enable_scaling(self, do_compact=False):
        self.do_compact = do_compact

    def _enable_flow_tracking(self, _flow_tracking=False):
        self._flow_tracking = _flow_tracking

    @property
    def snappi_config(self):
        return self._config

    def get_config_object(self, name):
        try:
            return self._config_objects[name]
        except KeyError:
            raise NameError("snappi object named {0} not found".format(name))

    def get_device_encap(self, name):
        try:
            return self._device_encap[name]
        except KeyError:
            raise NameError("snappi object named {0} not found".format(name))

    def set_device_encap(self, name, type):
        self._device_encap[name] = type

    def get_device_traffic_endpoint(self, name):
        try:
            value = self._device_traffic_endpoint[name]
        except KeyError:
            value = None
        return value

    def set_device_traffic_endpoint(self, name, value):
        self._device_traffic_endpoint[name] = value

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        self._username = value

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = value

    @property
    def assistant(self):
        return self._assistant

    @property
    def dev_compacted(self):
        return self._dev_compacted

    @property
    def ixnet_specific_config(self):
        if self._ixnet_specific_config is None:
            self._ixnet_specific_config = IxNetworkConfig(self)

        return self._ixnet_specific_config

    def set_dev_compacted(self, dev_name, name_list):
        for index, name in enumerate(name_list):
            self._dev_compacted[name] = {"dev_name": dev_name, "index": index}

    def _dict_to_obj(self, source):
        """Returns an object given a dict"""
        if isinstance(source, list):
            source = [self._dict_to_obj(x) for x in source]
        if not isinstance(source, dict):
            return source
        o = lambda: None
        for k, v in source.items():
            o.__dict__[k] = self._dict_to_obj(v)
        return o

    def _request_detail(self):
        request_detail = snappi.Warning()
        errors = self._errors
        warnings = list()
        app_errors = self._globals.AppErrors.find()
        if len(app_errors) > 0:
            current_errors = app_errors[0].Error.find()
            if len(current_errors) > 0:
                for error in current_errors:
                    # Add loop as sequence are not sorted
                    match = [
                        o
                        for o in self._ixn_errors
                        if o.Name == error.Name
                        and o.LastModified == error.LastModified
                    ]
                    if len(match) == 0:
                        if error.ErrorLevel == "kWarning":
                            warning = "IxNet - {0}".format(
                                error.Name
                                if error.Description == ""
                                else error.Description
                            )
                            self.info(warning)
                            warnings.append(warning)
                        if error.ErrorLevel == "kError":
                            error = "IxNet - {0}".format(
                                error.Name
                                if error.Description == ""
                                else error.Description
                            )
                            self.info(error)
                            errors.append(error)

        # Need to add this hack as dumping json config throws this exception
        # Traffic regeneration will be part of set_transmit_state
        errors = [
            error
            for error in errors
            if "before trying to generate BGP EVPN traffic" not in error
        ]

        if len(errors) > 0:
            self._errors = []
            raise SnappiIxnException(500, errors)
        request_detail.warnings = warnings
        return request_detail

    def set_config(self, config):
        """Set, update, append or delete the configuration"""
        try:
            if isinstance(config, (type(self._config_type), str)) is False:
                raise TypeError(
                    "The content must be of type Union[Config, str]"
                )

            if isinstance(config, str) is True:
                config = self._config_type.deserialize(config)
            self.config_ixnetwork(config)
            # CP-DP Convergence config
            ixn_cpdpconvergence = self._traffic.Statistics.CpdpConvergence
            ixn_cpdpconvergence.Enabled = False
            cfg = config.get("events")
            if cfg is not None:
                cp_events = cfg.get("cp_events")
                if cp_events is not None:
                    cp_events_enable = cp_events.get("enable")
                else:
                    cp_events_enable = False
                dp_events = cfg.get("dp_events")
                if dp_events is not None:
                    dp_events_enable = dp_events.get("enable")
                    rx_rate_threshold = dp_events.get("rx_rate_threshold")
                else:
                    dp_events_enable = False
                # Enable cp-dp convergence if any one of cp or dp is true
                if cp_events_enable or dp_events_enable:
                    ixn_cpdpconvergence.Enabled = True
                    # For CP events
                    if cp_events_enable:
                        ixn_cpdpconvergence.EnableControlPlaneEvents = True
                    # For DP events
                    if dp_events_enable:
                        if self.traffic_item.has_latency is True:
                            raise Exception(
                                "We are supporting either latency or dp convergence"
                            )
                        ixn_cpdpconvergence.EnableDataPlaneEventsRateMonitor = (
                            True
                        )
                        ixn_cpdpconvergence.DataPlaneThreshold = (
                            rx_rate_threshold
                        )

                for ixn_traffic_item in self._traffic_item.find():
                    ixn_traffic_item.Tracking.find()[0].TrackBy = [
                        "destEndpoint0",
                        "destSessionDescription0",
                    ]
            else:
                ixn_cpdpconvergence.Enabled = False

        except Exception as err:
            raise SnappiIxnException(err)

        bad_requests = self.get_json_import_errors()
        if bad_requests != []:
            bad_requests.insert(0, "bad request errors from Ixn:")
            raise SnappiIxnException(400, bad_requests)
        return self._request_detail()

    def get_json_import_errors(self):
        app_errors = self._globals.AppErrors.find()
        bad_requests = []
        if len(app_errors) > 0:
            current_errors = app_errors[0].Error.find()
            if len(current_errors) > 0:
                for error in current_errors:
                    if error.Name != "JSON Import Issues":
                        continue
                    for instance in error.Instance.find():
                        if instance.SourceValues in self._previous_errors:
                            continue
                        bad_requests.append(instance.SourceValues[0])
                        # this is for linux as it is retaining errors from
                        # previous run and raising exception in the latest
                        # script run
                        self._previous_errors.append(instance.SourceValues)
        return bad_requests

    def config_ixnetwork(self, config):
        self._config_objects = {}
        self._device_encap = {}
        self._device_traffic_endpoint = {}
        self.ixn_objects = IxNetObjects(self)
        self.ixn_routes = IxNetObjects(self)
        self._dev_compacted = {}
        self._connect()
        self.capture.reset_capture_request()
        self._config = self._validate_instance(config)
        with Timer(self, "Config validation"):
            self.validation.validate_config()
        self._ixnetwork.Traffic.UseRfc5952 = True
        if len(self._config._properties) == 0:
            self._ixnetwork.NewConfig()
        else:
            self.vport.config()
            self.lag.config()
            with Timer(self, "Devices configuration"):
                self.ngpf.config()
            self.traffic_item.config()
        self._running_config = self._config
        self._apply_change()
        with Timer(self, "Start interfaces"):
            # Start all protocols is workaround for pCPU crash reported by
            # Microsoft, need to revert once fix is available for pCPU crash
            if self._protocols_exists():
                for device in self._config.devices:
                    # After the config is pushed in IxNetwork, only then we can do ClearOverlays() in MKA Globals.
                    # That is why it cannot be done from within MKA module itself.

                    # Check if MACsec/MKA exists in topology
                    macsec = device.get("macsec")
                    if macsec:
                        if self._macsec._is_dynamic_key(macsec):
                            # it is MKA
                            self._mka._clear_overlays_in_globals(macsec)
                self._start_interface()
            else:
                if len(self._ixnetwork.Topology.find()) > 0:
                    self._ixnetwork.StartAllProtocols()
        if len(self.lag._lags_config) > 0:
            for lag in self.lag._lags_config:
                if lag.min_links > len(lag.ports):
                    self.warning(
                        "ports in {0} are less than configured minimum links {1} so {0} is inactive ".format(
                            lag.name, lag.min_links
                        )
                    )
                    self._ixnetwork.Lag.find(Name=lag.name).Stop()

    def _protocols_exists(self):
        total_dev = len(self._ixnetwork.GetTopologyStatus())
        topos = self._ixnetwork.Topology.find()
        ethv4v6_dev_count = 0
        if len(topos) > 0:
            dgs = topos.DeviceGroup.find()
            if len(dgs) > 0:
                eth_dev = len(
                    self._ixnetwork.Topology.find()
                    .DeviceGroup.find()
                    .Ethernet.find()
                )
                ethv4v6_dev_count = ethv4v6_dev_count + eth_dev
                if eth_dev > 0:
                    v4_dev = len(
                        self._ixnetwork.Topology.find()
                        .DeviceGroup.find()
                        .Ethernet.find()
                        .Ipv4.find()
                    )
                    ethv4v6_dev_count = ethv4v6_dev_count + v4_dev
                    v6_dev = len(
                        self._ixnetwork.Topology.find()
                        .DeviceGroup.find()
                        .Ethernet.find()
                        .Ipv6.find()
                    )
                    ethv4v6_dev_count = ethv4v6_dev_count + v6_dev
        if total_dev > ethv4v6_dev_count:
            return True
        else:
            return False

    def set_control_state(self, payload):
        try:
            control_option = payload.choice
            control_obj = getattr(payload, control_option)
            control_choice = control_obj.get("choice")
            request_payload = getattr(control_obj, control_choice)
            self._connect()
            event_names = []
            event_state = None
            event_type = control_choice
            EventInfo = namedtuple(
                "EventInfo", ["event_type", "event_state", "event_names"]
            )
            if control_option == "port":
                if control_choice == "capture":
                    self.capture.set_capture_state(request_payload)
                elif control_choice == "link":
                    self._TRIGGERED_EVENT = "link"
                    if request_payload.port_names is not None:
                        event_names = request_payload.port_names
                        event_state = request_payload.state
                    self.vport.set_link_state(request_payload)
            elif control_option == "protocol":
                if control_choice == "all":
                    self.ngpf.set_protocol_state(request_payload)
                elif control_choice == "route":
                    event_state = request_payload.state
                    with Timer(self, "Setting route state"):
                        event_names = self.ngpf.set_route_state(
                            request_payload
                        )
                elif control_choice == "lacp":
                    self.ngpf.set_device_state(request_payload)
            elif control_option == "traffic":
                self.traffic_item.transmit(request_payload)
            elif control_option is not None:
                msg = "{} is not a supported choice for metrics; \
                the supported choices are \
                ['port', 'protocol', traffic]".format(
                    control_option
                )
                raise SnappiIxnException(400, msg)
            self._event_info = EventInfo(event_type, event_state, event_names)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def set_control_action(self, payload):
        try:
            control_option = payload.choice
            control_obj = getattr(payload, control_option)
            control_choice = control_obj.get("choice")
            choice_obj = getattr(control_obj, control_choice)
            if control_choice == "ipv4":
                choice = choice_obj.get("choice")
                request_payload = getattr(choice_obj, choice)
                if choice == "ping":
                    res = self.control_action_response()
                    self._connect()
                    res.response.protocol.ipv4.ping.responses.deserialize(
                        self.ping.results(request_payload, control_choice)
                    )
            elif control_choice == "ipv6":
                choice = choice_obj.get("choice")
                request_payload = getattr(choice_obj, choice)
                if choice == "ping":
                    res = self.control_action_response()
                    self._connect()
                    res.response.protocol.ipv6.ping.responses.deserialize(
                        self.ping.results(request_payload, control_choice)
                    )
            elif control_option is not None:
                msg = "{} is not a supported choice for metrics; \
                the supported choices are \
                ['ipv4', 'ipv6']".format(
                    control_option
                )
                raise SnappiIxnException(400, msg)
            res.warnings = snappi.Warning()
            return res
        except Exception as err:
            raise SnappiIxnException(err)

    def get_capture(self, request):
        """Gets capture file and returns it as a byte stream"""
        try:
            if (
                isinstance(request, (type(self._capture_request), str))
                is False
            ):
                raise TypeError(
                    "The content must be of type Union[CaptureRequest, str]"
                )
            if isinstance(request, str) is True:
                request = self._capture_request.deserialize(request)
            self._connect()
        except Exception as err:
            raise SnappiIxnException(err)
        return self.capture.results(request)

    def get_states(self, request):
        try:
            states_request = self.states_request()
            if isinstance(request, (type(states_request), str)) is False:
                raise TypeError(
                    "The content must be of type Union[StatesRequest, str]"
                )
            if isinstance(request, str) is True:
                request = states_request.deserialize(request)
            self._connect()
            response = self.ngpf.get_states(request)
            states_response = self.states_response()
            states_response.deserialize(response)
            return states_response
        except Exception as err:
            raise SnappiIxnException(err)

    def get_metrics(self, request):
        """
        Gets port, flow and protocol metrics.

        Args
        ----
        - request (Union[MetricsRequest, str]): A request for Port, Flow and
          protocol metrics.
          The request content MUST be vase on the OpenAPI model,
          #/components/schemas/Result.MetricsRequest
          See the docs/openapi.yaml document for all model details
        """
        try:
            self._connect()
            metric_req = self.metrics_request()
            if isinstance(request, (type(metric_req), str)) is False:
                raise TypeError(
                    "The content must be of type Union[MetricsRequest, str]"
                )
            if isinstance(request, str) is True:
                request = metric_req.deserialize(request)
            # Need to change the code style when the choice Enum grows big
            if request.get("choice") == "port":
                response = self.vport.results(request.port)
                metric_res = self.metrics_response()
                metric_res.port_metrics.deserialize(response)
                return metric_res
            if request.get("choice") == "flow":
                response = self.traffic_item.results(request.flow)
                metric_res = self.metrics_response()
                metric_res.flow_metrics.deserialize(response)
                return metric_res
            if request.get("choice") == "egress_only_tracking":
                response = self.traffic_item.results_egress_only_tracking(
                    request.egress_only_tracking
                )
                metric_res = self.metrics_response()
                metric_res.egress_only_tracking_metrics.deserialize(response)
                return metric_res
            if request.get("choice") == "lag":
                response = self.traffic_item.results(request.lag)
                metric_res = self.metrics_response()
                metric_res.lag_metrics.deserialize(response)
                return metric_res
            if request.get("choice") == "lacp":
                response = self.traffic_item.results(request.lacp)
                metric_res = self.metrics_response()
                metric_res.lacp_metrics.deserialize(response)
                return metric_res
            if request.get("choice") == "convergence":
                response = self._result(request.convergence)
                metric_res = self.metrics_response()
                metric_res.convergence_metrics.deserialize(response)
                return metric_res
            if request.get("choice") == "rocev2_flow":
                response = self.traffic_item.rocev2_flow_results(
                    request.rocev2_flow
                )  # noqa
                metric_res = self.metrics_response()
                metric_res.rocev2_flow_per_qp_metrics.deserialize(response)
                return metric_res
            if (
                request.get("choice")
                in self.protocol_metrics.get_supported_protocols()
            ):
                response = self.protocol_metrics.results(request)
                metric_res = self.metrics_response()
                if (
                    request.choice == "rocev2_ipv4"
                    or request.choice == "rocev2_ipv6"
                ):
                    getattr(
                        metric_res, request.choice + "_per_peer" + "_metrics"
                    ).deserialize(response)
                else:
                    getattr(
                        metric_res, request.choice + "_metrics"
                    ).deserialize(response)
                return metric_res
        except Exception as err:
            raise SnappiIxnException(err)
        if request.get("choice") is not None:
            msg = "{} is not a supported choice for metrics; \
            the supported choices are \
            ['port', 'flow']".format(
                request.choice
            )
            raise SnappiIxnException(400, msg)

    def update_flows(self, payload):
        """
        Update Flows for property size and rate

        Args
        ----
        - request (Union[UpdateFlows, str]): A request for Flow property update.
          The request content MUST be vase on the OpenAPI model,
          #/components/schemas/Control.FlowsUpdate
          See the docs/openapi.yaml document for all model details
        """
        try:
            if isinstance(payload, str) is True:
                payload = self._flows_update.deserialize(payload)
            self._connect()
            self.traffic_item.update_flows(payload)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def delete_config(self, payload):
        """
        Delete Flows from config
        Args
        ----
        - request (Union[ConfigDeleteResources, str]): A request for Flow name for deletion.  # noqa
          The request content MUST be vase on the OpenAPI model,
          #/components/schemas/Config.Delete
          See the docs/openapi.yaml document for all model details
        """
        try:
            if isinstance(payload, str) is True:
                payload = self._flows_delete.deserialize(payload)
            self._connect()
            self.traffic_item.delete_configs(payload)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def append_config(self, payload):
        """
        Append Flows for config
        Args
        ----
        - request (Union[ConfigAppendResources, str]): A request for Flow name for append.  # noqa
          The request content MUST be vase on the OpenAPI model,
          #/components/schemas/Config.Append
          See the docs/openapi.yaml document for all model details
        """
        try:
            if isinstance(payload, str) is True:
                payload = self._flows_append.deserialize(payload)
            self._connect()
            self.traffic_item.append_configs(payload)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def _get_max_convergence(self, rows):
        # We are extracting max value for multiple destination
        rows_len = len(rows)
        if rows_len > 1:
            for (
                _,
                internal_name,
                external_type,
            ) in self._CONVERGENCE:
                if external_type not in ["float", "int"]:
                    continue
                max_value = rows[0][internal_name]
                for idx in range(1, rows_len):
                    tmp_value = rows[idx][internal_name]
                    if max_value < tmp_value:
                        max_value = tmp_value
                rows[0][internal_name] = max_value
        return rows[0]

    def _result(self, request):
        # get convergence result
        flow_names = request.get("flow_names")
        if not isinstance(flow_names, list):
            msg = "Invalid format of flow_names passed {},\
                                                expected list".format(
                flow_names
            )
            raise Exception(msg)
        if flow_names is None or len(flow_names) == 0:
            flow_names = [flow.name for flow in self.snappi_config.flows]
        flow_rows = self._get_flow_rows(flow_names)
        traffic_stat = self._assistant.StatViewAssistant(
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
            traffic_stat = self._assistant.StatViewAssistant(
                "Traffic Item Statistics"
            )
            convergence = {"name": flow_name}
            if flow_name not in traffic_index.keys():
                raise Exception("Somehow flow %s is missing" % flow_name)

            drill_down_options = traffic_stat.DrillDownOptions()
            drilldown_index = drill_down_options.index(drill_down_option)
            drill_down = traffic_stat.Drilldown(
                drilldown_index,
                drill_down_option,
                traffic_stat.TargetRowFilters()[traffic_index[flow_name]],
            )
            if drill_down.Rows is not None:
                drill_down_result = self._get_max_convergence(drill_down.Rows)
            ixn_cpdpconvergence = self._traffic.Statistics.CpdpConvergence
            if (
                ixn_cpdpconvergence.EnableDataPlaneEventsRateMonitor
                and ixn_cpdpconvergence.EnableControlPlaneEvents
            ):  # noqa
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
                    event_name = flow_result["Event Name"]
                    if event_name == "":
                        continue
                    event = self._get_event(event_name)
                    for (
                        external_name,
                        internal_name,
                        external_type,
                    ) in self._EVENT:
                        value = int(flow_result[internal_name].split(".")[-1])
                        self._set_result_value(
                            event, external_name, value * 1000, external_type
                        )
                    events.append(event)
                    if interruption_time is None:
                        if flow_result["DP Above Threshold Timestamp"] != "":
                            att = flow_result[
                                "DP Above Threshold Timestamp"
                            ].split(":")[-1]
                        else:
                            att = 0
                        if flow_result["DP Below Threshold Timestamp"] != "":
                            btt = flow_result[
                                "DP Below Threshold Timestamp"
                            ].split(":")[-1]
                        else:
                            btt = 0
                        interruption_time = float(att) - float(btt)
                        self._set_result_value(
                            convergence,
                            "service_interruption_time_us",
                            interruption_time,
                            float,
                        )
                convergence["events"] = events

            # for DP only metric
            if (
                ixn_cpdpconvergence.EnableDataPlaneEventsRateMonitor
                and not ixn_cpdpconvergence.EnableControlPlaneEvents
            ):  # noqa
                for (
                    external_name,
                    internal_name,
                    external_type,
                ) in self._DP_CONVERGENCE:
                    self._set_result_value(
                        convergence,
                        external_name,
                        drill_down_result[internal_name],
                        external_type,
                    )
            response.append(convergence)
        return response

    def _get_event(self, event_name):
        event = {}
        if re.search(r"Port Link Up", event_name):
            if self._event_info.event_state == "up":
                event["type"] = "link_up"
            else:
                event["type"] = "link_down"
        else:
            for route_name in self.ixn_routes.names:
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
            drill_down_options = traffic_stat.DrillDownOptions()
            if drill_down_option in drill_down_options:
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
        flow_stat = self.assistant.StatViewAssistant("Flow Statistics")

        if self._TRIGGERED_EVENT == "link":
            if "Show Physical Ports in LAG" in flow_stat.DrillDownOptions():
                flow_index = {}
                drill_down_option = "Show Physical Ports in LAG"
                for index, row in enumerate(
                    self._get_traffic_rows(flow_stat, drill_down_option)
                ):
                    flow_index[row["Traffic Item"]] = index
                drill_down_options = flow_stat.DrillDownOptions()
                drilldown_index = drill_down_options.index(drill_down_option)
                flow_stat.Drilldown(
                    0,
                    drill_down_option,
                    flow_stat.TargetRowFilters()[drilldown_index],
                )
                flow_stat = self.assistant.StatViewAssistant("Flow Statistics")
        has_flow = False
        while True:
            flow_rows = flow_stat.Rows
            has_event = False
            ixn_cpdpconvergence = self._traffic.Statistics.CpdpConvergence
            for row in flow_rows:
                if row["Traffic Item"] in flow_names:
                    has_flow = True
                    if (
                        ixn_cpdpconvergence.EnableDataPlaneEventsRateMonitor
                        and ixn_cpdpconvergence.EnableControlPlaneEvents
                    ):  # noqa
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
                    self.info("event is not reflected in stat")
                    break
            time.sleep(sleep_time)
            count += 1
        return flow_rows

    def add_error(self, error):
        """Add an error to the global errors"""
        if isinstance(error, str) is False:
            self._errors.append("%s %s" % (type(error), str(error)))
        else:
            self._errors.append(error)

    def get_errors(self):
        return self._errors

    def parse_location_info(self, location):
        """It will return (chassis,card,port)
        set card as 0 where that is not applicable"""
        if re.search("/|;", location) is None:
            raise Exception(
                "Invalid port location format, expected ["
                "chassis_ip;card_id;port_id or chassis_ip/port_id]"
            )
        LocationInfo = namedtuple(
            "LocationInfo", ["chassis_info", "card_info", "port_info"]
        )
        if ";" in location:
            try:
                (chassis_info, card_info, port_info) = location.split(";")
            except Exception:
                raise Exception("Please specify <chassis>;<card>;<port>")
        else:
            try:
                card_info = 0
                (chassis_info, port_info) = location.split("/")
            except Exception:
                raise Exception("Please specify <chassis>/<port>")
        return LocationInfo(chassis_info, card_info, port_info)

    def special_char(self, names):
        is_names = True
        if not isinstance(names, list):
            is_names = False
            names = [names]

        ret_list = []
        for name in names:
            if name is None:
                ret_list.append(name)
            else:
                ret_list.append(
                    name.replace("(", "\\(")
                    .replace(")", "\\)")
                    .replace("[", "\\[")
                    .replace("]", "\\]")
                    .replace(".", "\\.")
                    .replace("*", "\\*")
                    .replace("+", "\\+")
                    .replace("?", "\\?")
                    .replace("{", "\\{")
                    .replace("}", "\\}")
                )
        if is_names is True:
            return ret_list
        else:
            return ret_list[0]

    def _get_restpy_trace(self, log_level):
        if log_level == logging.DEBUG:
            return SessionAssistant.LOGLEVEL_ALL
        elif log_level == logging.WARNING:
            return SessionAssistant.LOGLEVEL_WARNING
        return SessionAssistant.LOGLEVEL_INFO

    def _connect(self):
        """Connect to an IxNetwork API Server."""
        self._errors = []
        self.logger = setup_ixnet_logger(self.log_level, module_name=__name__)
        if self._assistant is None:
            platform = TestPlatform(self._address, rest_port=self._port)
            platform.Authenticate(self._username, self._password)
            url = "%s://%s:%s/ixnetworkweb/api/v1/usersettings/ixnrest" % (
                platform.Scheme,
                platform.Hostname,
                platform.RestPort,
            )
            platform._connection._session.request(
                "put",
                url,
                data=json.dumps({"enableClassicProtocols": True}),
                verify=False,
            )
            self._assistant = SessionAssistant(
                IpAddress=self._address,
                RestPort=self._port,
                UserName=self._username,
                Password=self._password,
                LogLevel=self._get_restpy_trace(self._log_level),
            )
            self._ixnetwork = self._assistant.Session.Ixnetwork
            self._vport = self._ixnetwork.Vport
            self._lag = self._ixnetwork.Lag
            self._topology = self._ixnetwork.Topology
            self._traffic = self._ixnetwork.Traffic
            self._traffic_item = self._ixnetwork.Traffic.TrafficItem
            self._globals = self._ixnetwork.Globals
            if not self._ixn_version_check():
                raise Exception(
                    "IxNetwork 9.10 or newer is required for snappi[ixnetwork]"
                )
            if len(self._license_servers) > 0:
                self._ixnetwork.Globals.Licensing.LicensingServers = (
                    self._license_servers
                )
            try:
                import pkg_resources

                snappi_ver = (
                    "snappi-"
                    + pkg_resources.get_distribution("snappi").version
                )
                self.info(snappi_ver)
                snappi_ixn = (
                    "snappi_ixnetwork-"
                    + pkg_resources.get_distribution(
                        "snappi_ixnetwork"
                    ).version
                )
                self.info(snappi_ixn)
                restpy = (
                    "ixnetwork_restpy-"
                    + pkg_resources.get_distribution(
                        "ixnetwork_restpy"
                    ).version
                )
                self.info(restpy)
            except pkg_resources.DistributionNotFound as e:
                version = "Could not determine version for pkg {}".format(
                    e.req.project_name
                )
                self.info(version)
            except Exception as e:
                self.warning("{}".format(e))
        self._backup_errors()

    def _ixn_version_check(self):
        major, minor = self._globals.BuildNumber.split(".")[0:2]
        if int(major) < 9:
            return False
        if int(major) == 9 and int(minor) < 10:
            return False
        return True

    def _backup_errors(self):
        app_errors = self._globals.AppErrors.find()
        if len(app_errors) > 0:
            self._ixn_errors = app_errors[0].Error.find()

    def _validate_instance(self, config):
        """Validate current IxNetwork instance:
        1. Stop everything if local config is None
        2. Otherwise add warning message"""
        traffic_state = self._traffic.State
        if self.snappi_config is None:
            if traffic_state == "started":
                self._traffic_item.find()
                if len(self._traffic_item) > 0:
                    self._traffic_item.StopStatelessTrafficBlocking()
            glob_topo = self._globals.Topology.refresh()
            if glob_topo.Status == "started":
                self._ixnetwork.StopAllProtocols("sync")
        else:
            if traffic_state == "started":
                msg = (
                    "Flows are in running state. "
                    "Please stop those using set_transmit_state"
                )
                self.add_error(msg)
                self.warning(msg)
        self._initial_flows_config = self.config().flows.deserialize(
            config.flows.serialize(config.flows.DICT)
        )

        if "UHD" in self._ixnetwork.Globals.ProductVersion:
            chassis_info = "localuhd"
            for port in config.ports:
                if port.location is None:
                    continue
                if ";" in port.location:
                    (_, card, port_info) = port.location.split(";")
                    port_info = "{}.{}".format(card, port_info)
                elif "/" in port.location:
                    (_, port_info) = port.location.split("/")
                else:
                    raise SnappiIxnException(400, "port location is not valid")
                port.location = chassis_info + "/" + port_info
        return config

    def _apply_change(self):
        """Apply on the fly only applicable for Device object"""
        glob_topo = self._globals.Topology.refresh()
        if glob_topo.ApplyOnTheFlyState == "allowed":
            url = (
                "%s/globals/topology/operations/applyonthefly"
                % self._ixnetwork.href
            )
            payload = {"arg1": glob_topo.href}
            # todo: Sometime it redirect to some unknown loaction
            try:
                self._request("POST", url, payload)
            except Exception:
                pass

    def _start_interface(self):
        topos = self._ixnetwork.Topology.find()
        if len(topos) > 0:
            dgs = topos.DeviceGroup.find()
            if len(dgs) > 0:
                eth_list = dgs.Ethernet.find()
                if len(eth_list) > 0:
                    ip4_list = eth_list.Ipv4.find()
                    ip6_list = eth_list.Ipv6.find()
                    if len(eth_list) == max(len(ip4_list), len(ip6_list)):
                        if len(ip4_list) > 0:
                            ip4_list.Start()
                        if len(ip6_list) > 0:
                            ip6_list.Start()
                    else:
                        eth_list.Start()
                        if len(ip4_list) > 0:
                            ip4_list.Start()
                        if len(ip6_list) > 0:
                            ip6_list.Start()

    def _request(self, method, url, payload=None):
        self.debug("Request and Response ...")
        connection, url = self._assistant.Session._connection._normalize_url(
            url
        )
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._assistant.Session._connection.x_api_key,
        }
        if payload is not None:
            payload = json.dumps(payload)
        self.debug("%s %s %s" % (method, url, payload))
        response = self._assistant.Session._connection._session.request(
            method, url, headers=headers, data=payload, verify=False
        )
        response.raise_for_status()
        self.debug("Response %s" % response)
        if response.status_code == 202:
            content = response.json()
            while content["state"] == "IN_PROGRESS":
                time.sleep(0.2)
                response = self._request("GET", content["url"])
        if response.headers.get("Content-Type"):
            if response.headers["Content-Type"] == "application/json":
                return response.json()
            elif (
                response.headers["Content-Type"] == "application/octet-stream"
            ):
                return response.content
        return response

    def _remove(self, ixn_obj, items):
        """Remove any ixnetwork objects that are not found in the items list.
        If the items list does not exist remove everything.
        """
        valid_names = []
        for item in items:
            if isinstance(item, dict):
                name = item.get("name")
            else:
                name = item.name
            if name is not None:
                valid_names.append(name)
        invalid_names = []
        for item in ixn_obj.find():
            if item.Name not in valid_names:
                invalid_names.append(item.Name)
        self.debug("Removing these %s" % invalid_names)
        if len(invalid_names) > 0:
            if ixn_obj._SDM_NAME == "trafficItem":
                # can't remove traffic items that are started
                start_states = [
                    "txStopWatchExpected",
                    "locked",
                    "started",
                    "startedWaitingForStats",
                    "startedWaitingForStreams",
                    "stoppedWaitingForStats",
                ]
                for item in ixn_obj.find(
                    Name="^(%s)$" % "|".join(self.special_char(invalid_names))
                ):
                    if item.State in start_states:
                        item.StopStatelessTraffic()
                if len(ixn_obj) > 0:
                    poll = True
                    while poll:
                        poll = False
                        for v in self.select_traffic_items().values():
                            if v["state"] not in [
                                "error",
                                "stopped",
                                "unapplied",
                            ]:
                                poll = True
            ixn_obj.find(
                Name="^(%s)$" % "|".join(self.special_char(invalid_names))
            )
            if len(ixn_obj) > 0:
                ixn_obj.remove()

    # def _get_topology_name(self, port_name):
    #     return "Topology %s" % port_name

    def select_card_aggregation(self, location):
        (hostname, cardid, portid) = location.split(";")
        payload = {
            "selects": [
                {
                    "from": "/availableHardware",
                    "properties": [],
                    "children": [
                        {
                            "child": "chassis",
                            "properties": [],
                            "filters": [
                                {
                                    "property": "hostname",
                                    "regex": "^%s$" % hostname,
                                }
                            ],
                        },
                        {
                            "child": "card",
                            "properties": ["*"],
                            "filters": [
                                {
                                    "property": "cardId",
                                    "regex": "^%s$" % abs(int(cardid)),
                                }
                            ],
                        },
                        {
                            "child": "aggregation",
                            "properties": ["*"],
                            "filters": [],
                        },
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]["chassis"][0]["card"][0]

    def select_chassis_card(self, vport):
        pieces = vport["connectionStatus"].split(";")
        payload = {
            "selects": [
                {
                    "from": "/availableHardware",
                    "properties": [],
                    "children": [
                        {
                            "child": "chassis",
                            "properties": [],
                            "filters": [
                                {
                                    "property": "hostname",
                                    "regex": "^%s$" % pieces[0],
                                }
                            ],
                        },
                        {
                            "child": "card",
                            "properties": ["*"],
                            "filters": [
                                {
                                    "property": "cardId",
                                    "regex": "^%s$" % int(pieces[1]),
                                }
                            ],
                        },
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]["chassis"][0]["card"][0]

    def select_vports(self, port_name_filters=[]):
        """Select all vports.
        Return them in a dict keyed by vport name.
        """
        payload = {
            "selects": [
                {
                    "from": "/",
                    "properties": [],
                    "children": [
                        {
                            "child": "vport",
                            "properties": [
                                "name",
                                "type",
                                "location",
                                "connectionState",
                                "connectionStatus",
                                "assignedTo",
                                "connectedTo",
                            ],
                            "filters": port_name_filters,
                        },
                        {
                            "child": "l1Config",
                            "properties": ["currentType"],
                            "filters": [],
                        },
                        {
                            "child": "capture",
                            "properties": [
                                "hardwareEnabled",
                                "softwareEnabled",
                            ],
                            "filters": [],
                        },
                        {
                            "child": "^(eth.*|novus.*|uhd.*|atlas.*|ares.*|star.*|ten.*)$",
                            "properties": ["*"],
                            "filters": [],
                        },
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        vports = {}
        if "vport" in results[0]:
            for vport in results[0]["vport"]:
                vports[vport["name"]] = vport
        return vports

    def select_traffic_items(self, traffic_item_filters=[]):
        """Select all traffic items.
        Return them in a dict keyed by traffic item name.

        Args
        ----
        - filters (list(dict(property:'', 'regex':''))): A list of filters for the select.
            A filter is a dict with a property name and a regex match
        """
        payload = {
            "selects": [
                {
                    "from": "/traffic",
                    "properties": [],
                    "children": [
                        {
                            "child": "trafficItem",
                            "properties": ["name", "state", "enabled"],
                            "filters": traffic_item_filters,
                        },
                        {
                            "child": "highLevelStream",
                            "properties": [
                                "txPortName",
                                "rxPortNames",
                                "state",
                                "name",
                            ],
                            "filters": [],
                        },
                        {
                            "child": "tracking",
                            "properties": ["trackBy"],
                            "filters": [],
                        },
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        traffic_items = {}
        try:
            for traffic_item in results[0]["trafficItem"]:
                traffic_items[traffic_item["name"]] = traffic_item
        except Exception:
            pass
        return traffic_items

    def select_chassis_card_port(self, location):
        """Select all availalehardware.
        Return them in a dict keyed by vport name.
        """
        (hostname, cardid, portid) = location.split(";")
        payload = {
            "selects": [
                {
                    "from": "/availableHardware",
                    "properties": [],
                    "children": [
                        {
                            "child": "chassis",
                            "properties": [],
                            "filters": [
                                {
                                    "property": "hostname",
                                    "regex": "^%s$" % hostname,
                                }
                            ],
                        },
                        {
                            "child": "card",
                            "properties": [],
                            "filters": [
                                {
                                    "property": "cardId",
                                    "regex": "^%s$" % abs(int(cardid)),
                                }
                            ],
                        },
                        {
                            "child": "port",
                            "properties": [],
                            "filters": [
                                {
                                    "property": "portId",
                                    "regex": "^%s$" % abs(int(portid)),
                                }
                            ],
                        },
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]["chassis"][0]["card"][0]["port"][0]["xpath"]

    def clear_ownership(self, available_hardware_hrefs, location_hrefs):
        self.debug(
            "Clearing ownership %s from %s"
            % (available_hardware_hrefs, location_hrefs)
        )
        hrefs = list(available_hardware_hrefs.values()) + list(
            location_hrefs.values()
        )
        if len(hrefs) == 0:
            return
        names = list(available_hardware_hrefs.keys()) + list(
            location_hrefs.keys()
        )
        with Timer(self, "Location preemption [%s]" % ", ".join(names)):
            payload = {"arg1": [href for href in hrefs]}
            url = "%s/operations/clearownership" % payload["arg1"][0]
            self._ixnetwork._connection._execute(url, payload)

    def get_config(self):
        return self._config

    def check_protocol_statistics(self):
        start = time.time()
        url = "%s/operations/gettopologystatus" % self._ixnetwork.href
        check = True
        while check is True and time.time() - start < 90:
            check = False
            results = self._ixnetwork._connection._execute(url, None)
            for result in results:
                if result["arg2"][0]["arg2"] != result["arg2"][3]["arg2"]:
                    check = True

    def info(self, message):
        self.logger.info(message)

    def debug(self, message):
        self.logger.debug(message)

    def warning(self, message):
        logging.warning(message)

    def get_version(self):
        try:
            import pkg_resources

            sdk_version = (
                "snappi-" + pkg_resources.get_distribution("snappi").version
            )
            app_version = (
                "snappi_ixnetwork-"
                + pkg_resources.get_distribution("snappi_ixnetwork").version
            )

            return {
                "api_spec_version": "open-api-models-"
                + snappi.Api.get_local_version(self).api_spec_version,
                "sdk_version": sdk_version,
                "app_version": app_version,
            }
        except:
            raise SnappiIxnException("unable to get version")
