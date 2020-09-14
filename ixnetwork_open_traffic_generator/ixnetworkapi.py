import json
from collections import namedtuple
from jsonpath_ng.ext import parse
from ixnetwork_restpy import SessionAssistant
from abstract_open_traffic_generator.api import Api
from abstract_open_traffic_generator.config import Config
from ixnetwork_open_traffic_generator.validation import Validation
from ixnetwork_open_traffic_generator.vport import Vport
from ixnetwork_open_traffic_generator.ngpf import Ngpf
from ixnetwork_open_traffic_generator.trafficitem import TrafficItem


class IxNetworkApi(Api):
    """IxNetwork implementation of the abstract-open-traffic-generator package

    Args
    ----
    - address (str): The address of the IxNetwork API Server
    - port (str): The rest port of the IxNetwork API Server
    - username (str): The username for Linux IxNetwork API Server multi session environments
        This is not required when connecting to single session environments
    - password (str): The username for Linux IxNetwork API Server multi session environments
        This is not required when connecting to single session environments
    """
    def __init__(self, address='127.0.0.1', port='11009', username='admin', password='admin'):
        """Create a session
        - address (str): The ip address of the TestPlatform to connect to where test sessions will be created or connected to.
        - port (str): The rest port of the TestPlatform to connect to.
        - username (str): The username to be used for authentication
        - password (str): The password to be used for authentication
        """
        super(IxNetworkApi, self).__init__()
        self._address = address
        self._port = port
        self._username = username
        self._password = password
        self._running_config = None
        self._config = None
        self._assistant = None
        self.validation = Validation(self)
        self.vport = Vport(self)
        self.ngpf = Ngpf(self)
        self.traffic_item = TrafficItem(self)

    @property
    def config(self):
        return self._config

    @property
    def config_objects(self):
        """A dict of all unique names to abstract config objects
        """
        return self._config_objects

    @property
    def ixn_objects(self):
        """A dict of all model unique names to ixn hrefs
        """
        return self._ixn_objects 

    def get_ixn_object(self, name):
        """Returns a ixnetwork_restpy object given a unique configuration name
        """
        href = self._ixn_objects[name]
        return self._assistant.Session.GetObjectFromHref(href)

    @property
    def assistant(self):
        return self._assistant

    def set_config(self, config):
        """Abstract API implementation
        """
        if isinstance(config, (Config, str, dict, type(None))) is False:
            raise TypeError('The content must be of type (Config, str, dict, type(None))' % Config.__class__)
        if isinstance(config, str) is True:
            config = json.loads(config, object_hook = lambda otg : namedtuple('otg', otg.keys()) (*otg.values())) 
        elif isinstance(config, dict) is True:
            config = namedtuple('otg', config.keys())(*config.values())
        self._config = config
        self._config_objects = {}
        self._ixn_objects = {}
        self._errors = []
        self.validation.validate_config()        
        self.__connect()
        if self._config is None:
            self._ixnetwork.NewConfig()
        else:
            self.vport.config()
            self.ngpf.config()
            self.traffic_item.config()
        self._running_config = self._config

    def set_flow_transmit(self, request):
        """Abstract API implementation
        """
        return self.traffic_item.transmit(request)

    def get_port_results(self, request):
        """Abstract API implementation
        """
        return self.vport.results(request)

    def get_flow_results(self, request):
        """Abstract API implementation

        Args
        ----
        - request (Union[FlowRequest, str, dict]): A request for flow results.
            The request content MUST be based on the OpenAPI #/components/schemas/Result.FlowRequest model.
            See the docs/openapi.yaml document for all model details.
        """
        from abstract_open_traffic_generator.result import FlowRequest
        if isinstance(request, (FlowRequest, str, dict)) is False:
            raise TypeError('The content must be of type Union[FlowRequest, str, dict]')
        if isinstance(request, str) is True:
            request = json.loads(request, object_hook = lambda otg : namedtuple('otg', otg.keys()) (*otg.values())) 
        elif isinstance(request, dict) is True:
            request = namedtuple('otg', request.keys())(*request.values())
        return self.traffic_item.results(request)

    def add_error(self, error):
        """Add an error to the global errors
        """
        if isinstance(error, str) is False:
            self._errors.append(str(error))
        else:
            self._errors.append(error)

    def __connect(self):
        """Connect to an IxNetwork API Server.
        """
        if self._assistant is None:
            self._assistant = SessionAssistant(IpAddress=self._address,
                RestPort=self._port,
                UserName=self._username,
                Password=self._password,
                LogLevel=SessionAssistant.LOGLEVEL_INFO) 
            self._ixnetwork = self._assistant.Ixnetwork
            self._vport = self._ixnetwork.Vport
            self._topology = self._ixnetwork.Topology
            self._traffic = self._ixnetwork.Traffic
            self._traffic_item = self._ixnetwork.Traffic.TrafficItem

    def _remove(self, ixn_obj, items):
        """Remove any ixnetwork items that are not found in the configuration list.
        If the list does not exist remove everything.
        """
        if items is not None:  
            item_names = [item.name for item in items]
            for obj in ixn_obj.find():
                if obj.Name not in item_names:
                    obj.remove()
        else:
            ixn_obj.find().remove()

    def select_vports(self):
        """Select all vports.
        Return them in a dict keyed by vport name.
        """
        payload = {
            'selects': [
                {
                    'from': '/',
                    'properties': [],
                    'children': [
                        {
                            'child': 'vport',
                            'properties': ['name', 'type', 'location', 'connectionState'],
                            'filters': []
                        }
                    ],
                    'inlines': []
                }
            ]
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
            'selects': [
                {
                    'from': '/traffic',
                    'properties': [],
                    'children': [
                        {
                            'child': 'trafficItem',
                            'properties': ['name', 'state', 'enabled'],
                            'filters': traffic_item_filters
                        },
                        {
                            'child': 'highLevelStream',
                            'properties': ['txPortName', 'rxPortNames'],
                            'filters': []
                        }
                    ],
                    'inlines': []
                }
            ]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        traffic_items = {}
        try:
            for traffic_item in results[0]['trafficItem']:
                traffic_items[traffic_item['name']] = traffic_item
        except:
            pass
        return traffic_items
