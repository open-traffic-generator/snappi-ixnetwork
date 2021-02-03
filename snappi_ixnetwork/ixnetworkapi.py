import json
import time
from collections import namedtuple
from ixnetwork_restpy import TestPlatform, SessionAssistant
import snappi
from snappi_ixnetwork.validation import Validation
from snappi_ixnetwork.vport import Vport
from snappi_ixnetwork.ngpf import Ngpf
from snappi_ixnetwork.trafficitem import TrafficItem
from snappi_ixnetwork.capture import Capture
from snappi_ixnetwork.timer import Timer


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
    def __init__(self,
                 host=None,
                 username='admin',
                 password='admin',
                 license_servers=[],
                 log_level='info'):
        """Create a session
        - address (str): The ip address of the TestPlatform to connect to
        where test sessions will be created or connected to.
        - port (str): The rest port of the TestPlatform to connect to.
        - username (str): The username to be used for authentication
        - password (str): The password to be used for authentication
        """
        super(Api, self).__init__(
            host='https://127.0.0.1:11009' if host is None else host
        )
        self._address, self._port = self._get_addr_port(self.host)
        self._username = username
        self._password = password
        self._license_servers = license_servers
        self._log_level = log_level
        self._running_config = None
        self._config = None
        self._assistant = None
        self._ixn_errors = list()
        self._config_objects = {}
        self._device_encap = {}
        self.validation = Validation(self)
        self.vport = Vport(self)
        self.ngpf = Ngpf(self)
        self.traffic_item = TrafficItem(self)
        self.capture = Capture(self)

    def _get_addr_port(self, host):
        items = host.split('/')
        items = items[-1].split(':')

        addr = items[0]
        if len(items) == 2:
            return addr, items[-1]
        else:
            if host.startswith('https'):
                return addr, '443'
            else:
                return addr, '80'

    @property
    def snappi_config(self):
        return self._config

    def get_config_object(self, name):
        return self._config_objects[name]

    def get_device_encap(self, name):
        return self._device_encap[name]

    @property
    def ixn_objects(self):
        """A dict of all model unique names to ixn hrefs
        """
        return self._ixn_objects

    def get_ixn_object(self, name):
        """Returns an ixnetwork_restpy object given a unique configuration name
        """
        href = self.get_ixn_href(name)
        return self._assistant.Session.GetObjectFromHref(href)

    def get_ixn_href(self, name):
        """Returns an href given a unique configuration name
        """
        return self._ixn_objects[name]

    @property
    def assistant(self):
        return self._assistant

    def _dict_to_obj(self, source):
        """Returns an object given a dict
        """
        if isinstance(source, list):
            source = [self._dict_to_obj(x) for x in source]
        if not isinstance(source, dict):
            return source
        o = lambda: None
        for k, v in source.items():
            o.__dict__[k] = self._dict_to_obj(v)
        return o

    # def _request_detail(self):
    #     request_detail = RequestDetail()
    #     errors = self._errors
    #     warnings = list()
    #     app_errors = self._globals.AppErrors.find()
    #     if len(app_errors) > 0:
    #         current_errors = app_errors[0].Error.find()
    #         if len(current_errors) > 0:
    #             for error in current_errors:
    #                 match = [o for o in self._ixn_errors if o.Name == error.Name
    #                                                 and o.LastModified == error.LastModified]
    #                 if len(match) == 0:
    #                     if error.ErrorLevel == 'kWarning':
    #                         warnings.append("IxNet - {0}".format(error.Description))
    #                     if error.ErrorLevel == 'kError':
    #                         errors.append("IxNet - {0}".format(error.Description))
    #     request_detail.errors = errors
    #     request_detail.warnings = warnings
    #     return request_detail
    
    def set_config(self, config):
        """Set or update the configuration
        """
        if isinstance(config, str) is True:
            config = self.config().deserialize(config)
        self._config = config
        self._config_objects = {}
        self._device_encap = {}
        self._ixn_objects = {}
        self._errors = []
        self._connect()
        with Timer(self, 'Config validation'):
            self.validation.validate_config()
        if self._config is None:
            self._ixnetwork.NewConfig()
        else:
            self.vport.config()
            with Timer(self, 'Devices configuration'):
                self.ngpf.config()
            with Timer(self, 'Flows configuration'):
                self.traffic_item.config()
        self._running_config = self._config

    def set_transmit_state(self, flow_transmit_state):
        """Set the transmit state of flows
        """
        if isinstance(flow_transmit_state, str) is True:
            flow_transmit_state = self.transmit_state().deserialize(
                                    flow_transmit_state)
        self._connect()
        return self.traffic_item.transmit(flow_transmit_state)

    def set_link_state(self, link_state):
        if link_state.port_names is not None:
            self.vport.set_link_state(link_state)
    
    def set_capture_state(self, request):
        """Starts capture on all ports that have capture enabled.
        """
        self._connect()
        self.capture.set_capture_state(request)

    def get_capture(self, request):
        """Gets capture file and returns it as a byte stream
        """
        self._errors = []
        if isinstance(request, (type(self.capture_request()),
                                str)) is False:
            raise TypeError(
                'The content must be of type Union[CaptureRequest, str]')
        if isinstance(request, str) is True:
            request = self.capture_request().deserialize(
                request)
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
        self._errors = []
        metric_req = self.metrics_request()
        if isinstance(request, (type(metric_req),
                                str)) is False:
            raise TypeError(
                'The content must be of type Union[MetricsRequest, str]')
        if isinstance(request, str) is True:
            request = metric_req.deserialize(request)
        # Need to change the code style when the choice Enum grows big
        if request.choice == 'port':
            response = self.vport.results(request.port)
            return self.metrics_response().port_metrics.\
                deserialize(response)
        if request.choice == 'flow':
            response = self.traffic_item.results(request.flow)
            return self.metrics_response().flow_metrics.\
                deserialize(response)
        if request.choice == 'bgpv4':
            return

    def add_error(self, error):
        """Add an error to the global errors
        """
        if isinstance(error, str) is False:
            self._errors.append('%s %s' % (type(error), str(error)))
        else:
            self._errors.append(error)

    def _connect(self):
        """Connect to an IxNetwork API Server.
        """
        if self._assistant is None:
            platform = TestPlatform(self._address, rest_port=self._port)
            platform.Authenticate(self._username, self._password)
            url = '%s://%s:%s/ixnetworkweb/api/v1/usersettings/ixnrest' % \
                (platform.Scheme, platform.Hostname, platform.RestPort)
            platform._connection._session.request(
                'put',
                url,
                data=json.dumps({'enableClassicProtocols': True}),
                verify=False)
            self._assistant = SessionAssistant(IpAddress=self._address,
                                               RestPort=self._port,
                                               UserName=self._username,
                                               Password=self._password,
                                               LogLevel=self._log_level)
            self._ixnetwork = self._assistant.Session.Ixnetwork
            self._vport = self._ixnetwork.Vport
            self._topology = self._ixnetwork.Topology
            self._traffic = self._ixnetwork.Traffic
            self._traffic_item = self._ixnetwork.Traffic.TrafficItem
            self._globals = self._ixnetwork.Globals
            if len(self._license_servers) > 0:
                self._ixnetwork.Globals.Licensing \
                    .LicensingServers = self._license_servers
            try:
                version = pkg_resources.get_distribution(
                    "snappi_ixnetwork").version
            except Exception:
                version = "snappi_ixnetwork not installed " \
                    "using pip, unable to determine version"
            self.info(version)
        self._backup_errors()
    
    def _backup_errors(self):
        app_errors = self._globals.AppErrors.find()
        if len(app_errors) > 0:
            self._ixn_errors = app_errors[0].Error.find()

    def _request(self, method, url, payload=None):
        connection, url = self._assistant.Session._connection._normalize_url(
            url)
        headers = {}
        if payload is not None:
            payload = json.dumps(payload)
            headers['Content-Type'] = 'application/json'
        response = self._assistant.Session._connection._session.request(
            method, url, headers=headers, data=payload, verify=False)
        response.raise_for_status()
        if response.status_code == 202:
            content = response.json()
            while content['state'] == 'IN_PROGRESS':
                time.sleep(1)
                response = self._request('GET', content['url'])
        if response.headers.get('Content-Type'):
            if response.headers['Content-Type'] == 'application/json':
                return response.json()
            elif response.headers[
                    'Content-Type'] == 'application/octet-stream':
                return response.content
        return response

    def _remove(self, ixn_obj, items):
        """Remove any ixnetwork objects that are not found in the items list.
        If the items list does not exist remove everything.
        """
        valid_names = [item.name for item in items
                       if item.name is not None]
        invalid_names = []
        for item in ixn_obj.find():
            if item.Name not in valid_names:
                invalid_names.append(item.Name)
        if len(invalid_names) > 0:
            if ixn_obj._SDM_NAME == 'trafficItem':
                # can't remove traffic items that are started
                start_states = [
                    'txStopWatchExpected', 'locked', 'started',
                    'startedWaitingForStats', 'startedWaitingForStreams',
                    'stoppedWaitingForStats'
                ]
                for item in ixn_obj.find(Name='^(%s)$' %
                                         '|'.join(invalid_names)):
                    if item.State in start_states:
                        item.StopStatelessTraffic()
                if len(ixn_obj) > 0:
                    poll = True
                    while poll:
                        poll = False
                        for v in self.select_traffic_items().values():
                            if v['state'] not in [
                                    'error', 'stopped', 'unapplied'
                            ]:
                                poll = True
            ixn_obj.find(Name='^(%s)$' % '|'.join(invalid_names))
            if len(ixn_obj) > 0:
                ixn_obj.remove()

    def _get_topology_name(self, port_name):
        return 'Topology %s' % port_name

    def select_card_aggregation(self, location):
        (hostname, cardid, portid) = location.split(';')
        payload = {
            'selects': [{
                'from':
                '/availableHardware',
                'properties': [],
                'children': [{
                    'child':
                    'chassis',
                    'properties': [],
                    'filters': [{
                        'property': 'hostname',
                        'regex': '^%s$' % hostname
                    }]
                }, {
                    'child':
                    'card',
                    'properties': ['*'],
                    'filters': [{
                        'property': 'cardId',
                        'regex': '^%s$' % abs(int(cardid))
                    }]
                }, {
                    'child':
                    'aggregation',
                    'properties': ['*'],
                    'filters': []
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]['chassis'][0]['card'][0]

    def select_chassis_card(self, vport):
        pieces = vport['connectionStatus'].split(';')
        payload = {
            'selects': [{
                'from':
                '/availableHardware',
                'properties': [],
                'children': [{
                    'child':
                    'chassis',
                    'properties': [],
                    'filters': [{
                        'property': 'hostname',
                        'regex': '^%s$' % pieces[0]
                    }]
                }, {
                    'child':
                    'card',
                    'properties': ['*'],
                    'filters': [{
                        'property': 'cardId',
                        'regex': '^%s$' % int(pieces[1])
                    }]
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]['chassis'][0]['card'][0]

    def select_vports(self, port_name_filters=[]):
        """Select all vports.
        Return them in a dict keyed by vport name.
        """
        payload = {
            'selects': [{
                'from':
                '/',
                'properties': [],
                'children': [{
                    'child':
                    'vport',
                    'properties': [
                        'name', 'type', 'location', 'connectionState',
                        'connectionStatus', 'assignedTo', 'connectedTo'
                    ],
                    'filters': port_name_filters
                }, {
                    'child': 'l1Config',
                    'properties': ['currentType'],
                    'filters': []
                }, {
                    'child':
                    'capture',
                    'properties': ['hardwareEnabled', 'softwareEnabled'],
                    'filters': []
                }, {
                    'child': '^(eth.*|novus.*|uhd.*|atlas.*|ares.*|star.*)$',
                    'properties': ['*'],
                    'filters': []
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        vports = {}
        if 'vport' in results[0]:
            for vport in results[0]['vport']:
                vports[vport['name']] = vport
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
            'selects': [{
                'from':
                '/traffic',
                'properties': [],
                'children': [{
                    'child': 'trafficItem',
                    'properties': ['name', 'state', 'enabled'],
                    'filters': traffic_item_filters
                }, {
                    'child':
                    'highLevelStream',
                    'properties': ['txPortName', 'rxPortNames', 'state'],
                    'filters': []
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        traffic_items = {}
        try:
            for traffic_item in results[0]['trafficItem']:
                traffic_items[traffic_item['name']] = traffic_item
        except Exception:
            pass
        return traffic_items

    def select_chassis_card_port(self, location):
        """Select all availalehardware.
        Return them in a dict keyed by vport name.
        """
        (hostname, cardid, portid) = location.split(';')
        payload = {
            'selects': [{
                'from':
                '/availableHardware',
                'properties': [],
                'children': [{
                    'child':
                    'chassis',
                    'properties': [],
                    'filters': [{
                        'property': 'hostname',
                        'regex': '^%s$' % hostname
                    }]
                }, {
                    'child':
                    'card',
                    'properties': [],
                    'filters': [{
                        'property': 'cardId',
                        'regex': '^%s$' % abs(int(cardid))
                    }]
                }, {
                    'child':
                    'port',
                    'properties': [],
                    'filters': [{
                        'property': 'portId',
                        'regex': '^%s$' % abs(int(portid))
                    }]
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]['chassis'][0]['card'][0]['port'][0]['xpath']

    def clear_ownership(self, available_hardware_hrefs, location_hrefs):
        hrefs = list(available_hardware_hrefs.values()) + list(
            location_hrefs.values())
        if len(hrefs) == 0:
            return
        names = list(available_hardware_hrefs.keys()) + list(
            location_hrefs.keys())
        with Timer(self, 'Location preemption [%s]' % ', '.join(names)):
            payload = {'arg1': [href for href in hrefs]}
            url = '%s/operations/clearownership' % payload['arg1'][0]
            self._ixnetwork._connection._execute(url, payload)

    def get_config(self):
        return self._config

    def check_protocol_statistics(self):
        start = time.time()
        url = '%s/operations/gettopologystatus' % self._ixnetwork.href
        check = True
        while check is True and time.time() - start < 90:
            check = False
            results = self._ixnetwork._connection._execute(url, None)
            for result in results:
                if result['arg2'][0]['arg2'] != result['arg2'][3]['arg2']:
                    check = True

    def info(self, message):
        self._ixnetwork.info('[ixn-otg] %s' % message)

    def warning(self, message):
        self._ixnetwork.warn('[ixn-otg] %s' % message)
