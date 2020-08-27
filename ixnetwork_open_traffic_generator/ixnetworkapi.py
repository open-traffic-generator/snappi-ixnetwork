import json
from jsonpath_ng.ext import parse
from ixnetwork_restpy import SessionAssistant
from abstract_open_traffic_generator.api import Api
from abstract_open_traffic_generator.config import Config


class IxNetworkApi(Api):
    """IxNetwork implementation of the abstract-open-traffic-generator package

    Args
    ----
    - address (str): The address of the IxNetwork API Server
    - port (str): The rest port of the IxNetwork API Server
    """
    def __init__(self, address, port=None):
        super(IxNetworkApi, self)
        self._address = address
        self._port = port
        self._running_config = None
        self._config = None

    def set_config(self, config):
        if isinstance(config, Config) is False:
            raise TypeError('The content must be of type(%s)' % Config.__class__)
        self._config = config
        self._unique_names = {}
        self.__check_unique_names(self._config)

        self._assistant = SessionAssistant(IpAddress=self._address,
            RestPort=self._port,
            LogLevel=SessionAssistant.LOGLEVEL_INFO) 
        self._ixnetwork = self._assistant.Ixnetwork
        self._vport = self._ixnetwork.Vport
        self._topology = self._ixnetwork.Topology
        self._traffic_item = self._ixnetwork.Traffic.TrafficItem

        self.__configure_ports()
        self.__configure_topology()
        self.__configure_flows()
        # self.__connect_ports()
        self._running_config = self._config
        print(json.dumps(self._running_config, indent=2, default=lambda x: x.__dict__))

    def get_results(self, content):
        pass

    def __check_unique_names(self, config_item):
        for attr_name in dir(config_item):
            if attr_name.startswith('_'):
                continue
            attr_value = getattr(config_item, attr_name, None)
            if callable(attr_value) is True:
                continue
            if attr_name == 'name':
                if attr_value in self._unique_names:
                    raise NameError('%s.name: %s is not unique' % (config_item.__class__, attr_value))
                else:
                    self._unique_names[attr_value] = config_item
            elif attr_value is None:
                pass
            elif isinstance(attr_value, list):
                for item in attr_value:
                    self.__check_unique_names(item)
            elif '__module__' in dir(attr_value):
                if attr_value.__module__.startswith('abstract_open_traffic_generator'):
                    self.__check_unique_names(attr_value)


    def __configure_ports(self):
        """Resolve src config with dst config
        """
        # DELETE use case 
        # a src config has items removed from arrays 
        # the dst config must have those items removed
        vports = self._vport.find()
        for vport in vports:
            if self.__find_item(self._config.ports, 'name', vport.Name) is None:
                vport.remove()
        vports = self._vport.find()

        # CREATE use case
        # src config has items that do not exist in the dst config and should be created
        # UPDATE use case
        # src config has items that exist in the dst config and should be updated
        for port in self._config.ports:
            args = {
                'Name': port.name
            }
            vport = self.__find_item(vports, 'Name', port.name)
            if vport is None:
                vports.add(**args)
            else:
                vport.update(**args)

    def __configure_topology(self):
        """Resolve src config with dst config
        """
        # DELETE use case 
        # a src config has items removed from arrays 
        # the dst config must have those items removed
        topologies = self._topology.find()
        for topology in topologies:
            if self.__find_item(self._config.devices, 'name', topology.Name) is None:
                topology.remove()
        topologies = self._topology.find()

        # for topology in topologies:
        #     for dst_device_group in topology.DeviceGroup.find():
        #         for src_device_group in self._config.devices:
        #             if self.__find_item(src_device_group.devices, 'name', topology.Name) is None:
        #                 src_device_group.remove()

        # CREATE use case
        # src config has items that do not exist in the dst config and should be created
        # UPDATE use case
        # src config has items that exist in the dst config and should be updated
        for device_group in self._config.devices:
            args = {
                'Name': device_group.name
            }
            topology = self.__find_item(topologies, 'Name', device_group.name)
            if topology is None:
                topologies.add(**args)
            else:
                topology.update(**args)

    def __configure_device_group(self, parent, device_group):
        pass

    def __configure_ethernet(self, parent, ethernet):
        pass

    def __configure_vlan(self, parent, vlan):
        pass

    def __configure_ipv4(self, parent, ipv4):
        pass

    def __resolve_lists(self, dst_obj, src_list):
        dst_list = dst_obj.find()
        for dst_item in dst_list:
            if self.__find_item(self._config.devices, 'name', topology.Name) is None:
                topology.remove()
        topologies = self._topology.find()


    def __configure_flows(self):
        # DELETE use case 
        # a src config has items removed from arrays 
        # the dst config must have those items removed
        traffic_items = self._traffic_item.find()
        for traffic_item in traffic_items:
            if self.__find_item(self._config.flows, 'name', traffic_items.Name) is None:
                traffic_item.remove()
        traffic_items = self._traffic_item.find()

        # CREATE use case
        # src config has items that do not exist in the dst config and should be created
        # UPDATE use case
        # src config has items that exist in the dst config and should be updated
        for flow in self._config.flows:
            args = {
                'Name': flow.name
            }
            traffic_item = self.__find_item(traffic_items, 'Name', flow.name)
            if traffic_item is None:
                traffic_items.add(**args)
            else:
                traffic_item.update(**args)

    def __find_item(self, items, property_name, value):
        """Find an item in a list

        Args
        ----
        - items (list): an iterable list of items
        - property_name (str): the name of a property that exists on each item in the list
        - value (str): the value to be compared against each items property_name
        """
        if items is not None:
            for item in items:
                property_value = getattr(item, property_name)
                if property_value == value:
                    return item
        return None

    def __connect_ports(self):
        vports = json.loads(self._ixnetwork.ResourceManager.ExportConfig(['/vport'], True, 'json'))
        for port in self._config.ports:
            vport = parse("$.vport[?(@.name='%s')]" % port.name).find(vports)
            vport.location = port.location.physical


