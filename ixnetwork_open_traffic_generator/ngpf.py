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
        self._ixn_ngpf_objects = {}
        self._configure_topology(self._api.assistant.Ixnetwork.Topology, self._api.config.devices)

    def _remove(self, ixn_obj, items):
        """Remove any items that are not found
        """
        item_names = [item.name for item in items]
        for obj in ixn_obj.find():
            if obj.Name not in item_names:
                obj.remove()

    def _configure_topology(self, ixn_topology, device_groups):
        """Resolve abstract device_groups with ixnetwork topologies
        """
        self._remove(ixn_topology, device_groups)
        for device_group in device_groups:
            port_regex = '^(%s)$' % '|'.join(device_group.ports)
            args = {
                'Name': device_group.name,
                'Ports': self._api.assistant.Ixnetwork.Vport.find(Name=port_regex)
            }
            ixn_topology.find(Name=device_group.name)
            if len(ixn_topology) == 0:
                ixn_topology.add(**args)[-1]
            else:
                ixn_topology.update(**args)
            self._configure_device_group(ixn_topology.DeviceGroup, device_group.devices)

    def _configure_device_group(self, ixn_device_group, devices):
        """Resolve abstract devices with ixnetwork device_groups 
        """
        self._remove(ixn_device_group, devices)
        for device in devices:
            args = {
                'Name': device.name,
                'Multiplier': device.devices_per_port
            }
            ixn_device_group.find(Name=device.name)
            if len(ixn_device_group) == 0:
                ixn_device_group.add(**args)[-1]
            else:
                ixn_device_group.update(**args)
            self._configure_ethernet(ixn_device_group.Ethernet, device.ethernets)

    def _configure_ethernet(self, ixn_ethernet, ethernets):
        self._remove(ixn_ethernet, ethernets)
        for ethernet in ethernets:
            # TBD: translate the remaining abstract args to ixnetwork args
            args = {
                'Name': ethernet.name,
            }
            ixn_ethernet.find(Name=ethernet.name)
            if len(ixn_ethernet) == 0:
                ixn_ethernet.add(**args)
            else:
                ixn_ethernet.update(**args)
            # configure vlans
            ixn_ethernet.VlanCount = len(ethernet.vlans)
            ixn_ethernet.EnableVlans.Single(ixn_ethernet.VlanCount > 0)
            self._configure_vlan(ixn_ethernet.Vlan, ethernet.vlans)
            self._configure_ipv4(ixn_ethernet.Ipv4, ethernet.ipv4)
            self._configure_ipv6(ixn_ethernet.Ipv6, ethernet.ipv6)

    def _configure_vlan(self, ixn_vlans, vlans):
        """
        """
        for i in range(0, len(ixn_vlans.find())):
            args = {
                'Name': vlans[i].name
            }
            ixn_vlan = ixn_vlans[i]
            ixn_vlan.update(**args)

    def _configure_ipv4(self, ixn_ipv4, ipv4):
        if ipv4 is None:
            return
        ixn_ipv4.find('^((?!%s).)*$' % ipv4.name).remove()
        args = {
            'Name': ipv4.name,
        }
        ixn_ipv4.find(Name=ipv4.name)
        if len(ixn_ipv4) == 0:
            ixn_ipv4.add(**args)[-1]
        else:
            ixn_ipv4.update(**args)
        self._configure_bgpv4(ixn_ipv4.BgpIpv4Peer, ipv4.bgpv4)

    def _configure_ipv6(self, ixn_ipv6, ipv6):
        if ipv6 is None:
            return
        ixn_ipv6.find('^((?!%s).)*$' % ipv6.name).remove()
        args = {
            'Name': ipv6.name,
        }
        ixn_ipv6.find(Name=ipv6.name)
        if len(ixn_ipv6) == 0:
            ixn_ipv6.add(**args)[-1]
        else:
            ixn_ipv6.update(**args)

    def _configure_bgpv4(self, ixn_bgpv4, bgpv4):
        if bgpv4 is None:
            return
        ixn_bgpv4.find('^((?!%s).)*$' % bgpv4.name).remove()
        args = {
            'Name': bgpv4.name,
        }
        ixn_bgpv4.find(Name=bgpv4.name)
        if len(ixn_bgpv4) == 0:
            ixn_bgpv4.add(**args)[-1]
        else:
            ixn_bgpv4.update(**args)
