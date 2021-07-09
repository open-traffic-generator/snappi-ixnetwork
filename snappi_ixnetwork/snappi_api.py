import json
import time, re
from collections import namedtuple
from ixnetwork_restpy import TestPlatform, SessionAssistant
import snappi
from snappi_ixnetwork.validation import Validation
from snappi_ixnetwork.vport import Vport
from snappi_ixnetwork.lag import Lag
from snappi_ixnetwork.ngpf import Ngpf
from snappi_ixnetwork.trafficitem import TrafficItem
from snappi_ixnetwork.capture import Capture
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.protocolmetrics import ProtocolMetrics
from snappi_ixnetwork.resourcegroup import ResourceGroup
from snappi_ixnetwork.exceptions import SnappiIxnException


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
        log_level = kwargs.get("log_level")
        location = "https://127.0.0.1:11009" if location is None else location
        self._address, self._port = self._get_addr_port(location)
        self._username = "admin" if username is None else username
        self._password = "admin" if password is None else password
        self._license_servers = (
            [] if license_servers is None else license_servers
        )
        self._log_level = "info" if log_level is None else log_level
        self._running_config = None
        self._config = None
        self._assistant = None
        self._ixn_errors = list()
        self._config_objects = {}
        self._device_encap = {}
        self._config_type = self.config()
        self._transmit_state = self.transmit_state()
        self._link_state = self.link_state()
        self._capture_state = self.capture_state()
        self._capture_request = self.capture_request()
        self._ixn_route_objects = {}
        self.validation = Validation(self)
        self.vport = Vport(self)
        self.lag = Lag(self)
        self.ngpf = Ngpf(self)
        self.traffic_item = TrafficItem(self)
        self.capture = Capture(self)
        self.protocol_metrics = ProtocolMetrics(self)
        self.resource_group = ResourceGroup(self)

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

    @property
    def ixn_objects(self):
        """A dict of all model unique names to ixn hrefs"""
        return self._ixn_objects

    def get_ixn_object(self, name):
        """Returns an ixnetwork_restpy object given a unique configuration name"""
        href = self.get_ixn_href(name)
        return self._assistant.Session.GetObjectFromHref(href)

    def get_ixn_href(self, name):
        """Returns an href given a unique configuration name"""
        return self._ixn_objects[name]

    @property
    def ixn_route_objects(self):
        return self._ixn_route_objects

    def get_route_object(self, name):
        if name not in self._ixn_route_objects.keys():
            raise Exception("%s not within configure routes" % name)
        return self._ixn_route_objects[name]

    @property
    def assistant(self):
        return self._assistant

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
        request_detail = snappi.ResponseWarning()
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
                            warnings.append(
                                "IxNet - {0}".format(error.Description)
                            )
                        if error.ErrorLevel == "kError":
                            errors.append(
                                "IxNet - {0}".format(error.Description)
                            )
        # request_detail.errors = errors
        if len(errors) > 0:
            self._errors = []
            raise SnappiIxnException(500, errors)
        request_detail.warnings = warnings
        return request_detail

    def set_config(self, config):
        """Set or update the configuration"""
        try:
            if isinstance(config, (type(self._config_type), str)) is False:
                raise TypeError(
                    "The content must be of type Union[Config, str]"
                )

            if isinstance(config, str) is True:
                config = self._config_type.deserialize(config)
            self.config_ixnetwork(config)
        except Exception as err:
            raise SnappiIxnException(err)
        app_errors = self._globals.AppErrors.find()
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

    def config_ixnetwork(self, config):
        self._config_objects = {}
        self._device_encap = {}
        self._ixn_objects = {}
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
            with Timer(self, "Flows configuration"):
                self.traffic_item.config()
        self._running_config = self._config
        self._apply_change()

    def set_transmit_state(self, payload):
        """Set the transmit state of flows"""
        try:
            if isinstance(payload, (type(self._transmit_state), str)) is False:
                raise TypeError(
                    "The content must be of type Union[TransmitState, str]"
                )
            if isinstance(payload, str) is True:
                payload = self._transmit_state.deserialize(payload)
            self._connect()
            self.traffic_item.transmit(payload)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def set_link_state(self, link_state):
        try:
            if isinstance(link_state, (type(self._link_state), str)) is False:
                raise TypeError(
                    "The content must be of type Union[LinkState, str]"
                )
            if isinstance(link_state, str):
                link_state = self._link_state.deserialize(link_state)
            self._connect()
            if link_state.port_names is not None:
                self.vport.set_link_state(link_state)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def set_capture_state(self, payload):
        """Starts capture on all ports that have capture enabled."""
        try:
            if isinstance(payload, (type(self._capture_state), str)) is False:
                raise TypeError(
                    "The content must be of type Union[CaptureState, str]"
                )
            if isinstance(payload, str) is True:
                payload = self._capture_state.deserialize(payload)
            self._connect()
            self.capture.set_capture_state(payload)
        except Exception as err:
            raise SnappiIxnException(err)
        return self._request_detail()

    def set_route_state(self, payload):
        try:
            route_state = self.route_state()
            if isinstance(payload, (type(route_state), str)) is False:
                raise TypeError(
                    "The content must be of type Union[RouteState, str]"
                )
            if isinstance(payload, str) is True:
                payload = route_state.deserialize(payload)
            self._connect()
            with Timer(self, "Setting route state"):
                self.ngpf.set_route_state(payload)
            return self._request_detail()
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
            if (
                request.get("choice")
                in self.protocol_metrics.get_supported_protocols()
            ):
                response = self.protocol_metrics.results(request)
                metric_res = self.metrics_response()
                getattr(metric_res, request.choice + "_metrics").deserialize(
                    response
                )
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

    def add_error(self, error):
        """Add an error to the global errors"""
        if isinstance(error, str) is False:
            self._errors.append("%s %s" % (type(error), str(error)))
        else:
            self._errors.append(error)

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

    def _connect(self):
        """Connect to an IxNetwork API Server."""
        self._errors = []
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
                LogLevel=self._log_level,
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

    def _request(self, method, url, payload=None):
        connection, url = self._assistant.Session._connection._normalize_url(
            url
        )
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._assistant.Session._connection.x_api_key,
        }
        if payload is not None:
            payload = json.dumps(payload)
        response = self._assistant.Session._connection._session.request(
            method, url, headers=headers, data=payload, verify=False
        )
        response.raise_for_status()
        if response.status_code == 202:
            content = response.json()
            while content["state"] == "IN_PROGRESS":
                time.sleep(1)
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
        valid_names = [item.name for item in items if item.name is not None]
        invalid_names = []
        for item in ixn_obj.find():
            if item.Name not in valid_names:
                invalid_names.append(item.Name)
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

    def _get_topology_name(self, port_name):
        return "Topology %s" % port_name

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
                            "child": "^(eth.*|novus.*|uhd.*|atlas.*|ares.*|star.*)$",
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
                            ],
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
        self._ixnetwork.info("[ixn-otg] %s" % message)

    def warning(self, message):
        self._ixnetwork.warn("[ixn-otg] %s" % message)
