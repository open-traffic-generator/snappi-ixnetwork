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
    def __init__(self, address='127.0.0.1', port='11009'):
        super(IxNetworkApi, self)
        self._address = address
        self._port = port
        self._running_config = None
        self._config = None
        self._assistant = None

    def set_config(self, config):
        if isinstance(config, (Config, type(None))) is False:
            raise TypeError('The content must be of type (Config, type(None))' % Config.__class__)
        self._config = config
        
        self._unique_names = {}
        self._unique_name_errors = []
        self.__check_unique_names(self._config)
        if len(self._unique_name_errors) > 0:
            raise NameError(', '.join(self._unique_name_errors))

        self.__connect()
        if self._config is None:
            self._ixnetwork.NewConfig()
        else:
            self._ixn_ngpf_objects = {}
            self.__configure_vports()
            self.__configure_topology()
            self.__configure_flows()
            # self.__connect_ports()
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

    def __check_unique_names(self, config_item):
        if config_item is None:
            return
        for attr_name in dir(config_item):
            if attr_name.startswith('_'):
                continue
            attr_value = getattr(config_item, attr_name, None)
            if callable(attr_value) is True:
                continue
            if attr_name == 'name':
                if attr_value in self._unique_names:
                    self._unique_name_errors.append('%s.name: "%s" is not unique' % (config_item.__class__.__name__, attr_value))
                if attr_value is None:
                    self._unique_name_errors.append('%s.name: "None" is not allowed' % (config_item.__class__.__name__))
                else:
                    self._unique_names[attr_value] = config_item
            elif isinstance(attr_value, list):
                for item in attr_value:
                    self.__check_unique_names(item)
            elif '__module__' in dir(attr_value):
                if attr_value.__module__.startswith('abstract_open_traffic_generator'):
                    self.__check_unique_names(attr_value)

    def __configure_vports(self):
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
        """Resolve abstract device_groups with ixnetwork topologies
        """
        # DELETE use case 
        # a src config has items removed from arrays 
        # the dst config must have those items removed
        for topology in self._topology.find():
            if self.__find_item(self._config.devices, 'name', topology.Name) is None:
                topology.remove()
        self._topology.find()

        # CREATE use case
        # src config has items that do not exist in the dst config and should be created
        # UPDATE use case
        # src config has items that exist in the dst config and should be updated
        for device_group in self._config.devices:
            # TBD: translate the remaining abstract args to ixnetwork args
            args = {
                'Name': device_group.name
            }
            topology = self.__find_item(self._topology, 'Name', device_group.name)
            if topology is None:
                topology = self._topology.add(**args)[-1]
            else:
                topology.update(**args)
            self.__configure_device_group(topology.DeviceGroup, device_group.devices)

    def __find(self, name):
        """ use select to find a specific object
        """
        pass

    def __configure_device_group(self, ixn_device_groups, devices):
        """Resolve abstract devices with ixnetwork device_groups 
        """
        for ixn_device_group in ixn_device_groups.find():
            if self.__find_item(devices, 'name', ixn_device_group.Name) is None:
                ixn_device_group.remove()
        ixn_device_groups.find()

        for device in devices:
            # TBD: translate the remaining abstract args to ixnetwork args
            args = {
                'Name': device.name
            }
            ixn_device_group = self.__find_item(ixn_device_groups, 'Name', device.name)
            if ixn_device_group is None:
                ixn_device_group = ixn_device_groups.add(**args)[-1]
            else:
                ixn_device_group.update(**args)
           
            self._ixn_ngpf_objects[ixn_device_group.Name] = ixn_device_group
            self.__stack_protocols(ixn_device_group.Name, device.protocols)

    def __stack_protocols(self, parent, items):
        for protocol in self.__get_child_protocols(parent, items):
            if protocol.choice == 'ethernet':
                protocol_name = protocol.ethernet.name
                self.__configure_ethernet(protocol)
            elif protocol.choice == 'vlan':
                protocol_name = protocol.vlan.name
                self.__configure_vlan(protocol, items)
            elif protocol.choice == 'ipv4':
                protocol_name = protocol.ipv4.name
                self.__configure_ipv4(protocol)
            self.__stack_protocols(protocol_name, items)

    def __get_child_protocols(self, parent, items):
        """Find all the chidren of the current_items and return them
        An item.parent is the top of hierarchy
        current_item is the position in the hierarchy
        find all items whose parent is current_item
        Return an empty list if there are no other child items
        """
        children = []
        for item in items:
            if item.parent == parent:
                children.append(item)
        return children

    def __configure_ethernet(self, protocol):
        ethernet = protocol.ethernet
        ixn_ethernets = self._ixn_ngpf_objects[protocol.parent].Ethernet.find(Name=ethernet.name)
        if len(ixn_ethernets) == 1 and ixn_ethernets.Name != ethernet.name:
            ixn_ethernets.remove()

        # TBD: translate the remaining abstract args to ixnetwork args
        args = {
            'Name': ethernet.name
        }
        ixn_ethernet = self.__find_item(ixn_ethernets, 'Name', ethernet.name)
        if ixn_ethernet is None:
            ixn_ethernet = ixn_ethernets.add(**args)[-1]
        else:
            ixn_ethernet.update(**args)
        self._ixn_ngpf_objects[ixn_ethernet.Name] = ixn_ethernet

    def __configure_vlan(self, protocol, protocol_stack):
        # vlan = protocol.vlan
        # ixn_ethernet = self._ixn_ngpf_objects[protocol.parent].parent
        # args = {
        #     'Name': vlan.name
        # }
        # ixn_vlan = self.__find_item(ixn_vlan, 'Name', vlan.name)
        # if ixn_vlan is None:
        #     ixn_ethernet = ixn_ethernet.add(**args)[-1]
        # else:
        #     ixn_ethernet.update(**args)
        pass

    def __configure_ipv4(self, protocol):
        ipv4 = protocol.ipv4

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


