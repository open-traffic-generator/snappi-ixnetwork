import json
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
    """
    def __init__(self, address='127.0.0.1', port='11009'):
        super(IxNetworkApi, self).__init__()
        self._address = address
        self._port = port
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
    def assistant(self):
        return self._assistant

    def set_config(self, config):
        if isinstance(config, (Config, type(None))) is False:
            raise TypeError('The content must be of type (Config, type(None))' % Config.__class__)
        self._config = config
        self.validation.validate_config()        
        self.__connect()
        if self._config is None:
            self._ixnetwork.NewConfig()
        else:
            self._ixn_ngpf_objects = {}
            self.vport.config()
            self.ngpf.config()
            self.traffic_item.config()
        self._running_config = self._config

    def get_results(self, content):
        pass

    def __connect(self):
        if self._assistant is None:
            self._assistant = SessionAssistant(IpAddress=self._address,
                RestPort=self._port,
                LogLevel=SessionAssistant.LOGLEVEL_INFO) 
            self._ixnetwork = self._assistant.Ixnetwork
            self._vport = self._ixnetwork.Vport
            self._topology = self._ixnetwork.Topology
            self._traffic = self._ixnetwork.Traffic
            self._traffic_item = self._ixnetwork.Traffic.TrafficItem

    def __resolve_lists(self, dst_obj, src_list):
        dst_list = dst_obj.find()
        for dst_item in dst_list:
            if self.find_item(self._config.devices, 'name', topology.Name) is None:
                topology.remove()
        topologies = self._topology.find()

    def find_item(self, items, property_name, value):
        """Find an item in a list

        Args
        ----
        - items (list): an iterable list of config items
        - property_name (str): the name of a property that exists on each item in the list
        - value (str): the value to be compared against each items property_name
        """
        if items is not None:
            for item in items:
                property_value = getattr(item, property_name)
                if property_value == value:
                    return item
        return None



