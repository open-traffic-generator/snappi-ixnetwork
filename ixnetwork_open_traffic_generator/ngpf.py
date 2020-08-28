import json


class Ngpf(object):
    """Ngpf configuration

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    """
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        
    def config(self):
        """Configure config.devices onto Ixnetwork.Topology
        
        CRUD
        ----
        - DELETE any ngpf object that does not exist in config.devices
        - CREATE ngpf object for any config.devices...name that does not exist
        - UPDATE ngpf object for any config...name that exists
        """
        self._configure_topology()

    def _configure_topology(self):
        """Resolve abstract device_groups with ixnetwork topologies
        """
        self._topology = self._api.assistant.Ixnetwork.Topology
        for topology in self._topology.find():
            if self._api.find_item(self._api.config.devices, 'name', topology.Name) is None:
                topology.remove()
        self._topology.find()

        for device_group in self._api.config.devices:
            # TBD: translate the remaining abstract args to ixnetwork args
            args = {
                'Name': device_group.name
            }
            topology = self._api.find_item(self._topology, 'Name', device_group.name)
            if topology is None:
                topology = self._topology.add(**args)[-1]
            else:
                topology.update(**args)
            self._configure_device_group(topology.DeviceGroup, device_group.devices)

    def _find(self, name):
        """ use select to find a specific object
        """
        pass

    def _configure_device_group(self, ixn_device_groups, devices):
        """Resolve abstract devices with ixnetwork device_groups 
        """
        for ixn_device_group in ixn_device_groups.find():
            if self.find_item(devices, 'name', ixn_device_group.Name) is None:
                ixn_device_group.remove()
        ixn_device_groups.find()

        for device in devices:
            # TBD: translate the remaining abstract args to ixnetwork args
            args = {
                'Name': device.name
            }
            ixn_device_group = self._api.find_item(ixn_device_groups, 'Name', device.name)
            if ixn_device_group is None:
                ixn_device_group = ixn_device_groups.add(**args)[-1]
            else:
                ixn_device_group.update(**args)
           
            self._api._ixn_ngpf_objects[ixn_device_group.Name] = ixn_device_group
            self._stack_protocols(ixn_device_group.Name, device.protocols)

    def _stack_protocols(self, parent, items):
        for protocol in self._get_child_protocols(parent, items):
            if protocol.choice == 'ethernet':
                protocol_name = protocol.ethernet.name
                self._configure_ethernet(protocol)
            elif protocol.choice == 'vlan':
                protocol_name = protocol.vlan.name
                self._configure_vlan(protocol, items)
            elif protocol.choice == 'ipv4':
                protocol_name = protocol.ipv4.name
                self._configure_ipv4(protocol)
            self._stack_protocols(protocol_name, items)

    def _get_child_protocols(self, parent, items):
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

    def _configure_ethernet(self, protocol):
        ethernet = protocol.ethernet
        ixn_ethernets = self._api._ixn_ngpf_objects[protocol.parent].Ethernet.find(Name=ethernet.name)
        if len(ixn_ethernets) == 1 and ixn_ethernets.Name != ethernet.name:
            ixn_ethernets.remove()

        # TBD: translate the remaining abstract args to ixnetwork args
        args = {
            'Name': ethernet.name
        }
        ixn_ethernet = self._api.find_item(ixn_ethernets, 'Name', ethernet.name)
        if ixn_ethernet is None:
            ixn_ethernet = ixn_ethernets.add(**args)[-1]
        else:
            ixn_ethernet.update(**args)
        self._api._ixn_ngpf_objects[ixn_ethernet.Name] = ixn_ethernet

    def _configure_vlan(self, protocol, protocol_stack):
        # vlan = protocol.vlan
        # ixn_ethernet = self._ixn_ngpf_objects[protocol.parent].parent
        # args = {
        #     'Name': vlan.name
        # }
        # ixn_vlan = self.find_item(ixn_vlan, 'Name', vlan.name)
        # if ixn_vlan is None:
        #     ixn_ethernet = ixn_ethernet.add(**args)[-1]
        # else:
        #     ixn_ethernet.update(**args)
        pass

    def _configure_ipv4(self, protocol):
        ipv4 = protocol.ipv4

