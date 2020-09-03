import json
from jsonpath_ng.ext import parse


class Vport(object):
    """Vport configuration

    Transforms OpenAPI Port.Port, Port.Layer1 objects into IxNetwork 
    /vport and /vport/l1Config/... objects

    Uses resourcemanager to set the vport location and l1Config as it is the
    most efficient way. DO NOT use the AssignPorts API as it is too slow. 

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    """
    _SPEED_MAP = {
        'one_hundred_gbps': 'speed100g', 
        'fifty_gbps': 'speed50g', 
        'forty_gbps': 'speed40g', 
        'twenty_five_gpbs': 'speed25g', 
        'ten_gbps': 'speed10g',
        'one_thousand_mbps': 'speed1000',
        'one_hundred_fd_mbps': 'speed100fd',
        'one_hundred_hd_mbps': 'speed100hd',
        'ten_fd_mbps': 'speed10fd', 
        'ten_hd_mbps': 'speed10hd'        
    }
    _ADVERTISE_MAP = {
        'advertise_one_thousand_mbps': 'speed1000',
        'advertise_one_hundred_fd_mbps': 'speed100fd',
        'advertise_one_hundred_hd_mbps': 'speed100hd', 
        'advertise_ten_fd_mbps': 'speed10fd', 
        'advertise_ten_hd_mbps': 'speed10hd'        
    }
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        
    def config(self):
        """Transform config.ports into Ixnetwork.Vport
        
        CRUD
        ----
        - DELETE any Ixnetwork.Vport.Name that does not exist in config.ports
        - CREATE vport for any config.ports[*].name that does not exist
        - UPDATE vport for any config.ports[*].name that does exist
        """
        self._resource_manager = self._api._ixnetwork.ResourceManager
        ixn_vport = self._api._vport
        for vport in ixn_vport.find():
            if self._api.find_item(self._api.config.ports, 'name', vport.Name) is None:
                vport.remove()
        port_map = self._api.assistant.PortMapAssistant()
        for port in self._api.config.ports:
            ixn_vport.find(Name=port.name)
            if len(ixn_vport) == 0:
                ixn_vport.add(Name=port.name)
            self._api.ixn_objects[port.name] = ixn_vport.href
        for port in self._api.config.ports:
            if port.location is not None:
                port_map.Map(Name=port.name, Location=port.location)
        if len(port_map._map) > 0:
            port_map.Connect()
        vports = self._api.select_vports()
        for port in self._api.config.ports:
            if port.location is None:
                continue
            vport = vports[port.name]
            if vport['connectionState'] not in ['connectedLinkUp', 'connectedLinkDown']:
                print(
                    {
                        'name': vport['name'],
                        'error': 'Unable to connect port %s to test port location %s [%s]' % (port.name, port.location, vport['connectionState'])
                    }
                )
        self._config_layer1()

    def _config_layer1(self):
        """Set the /vport/l1Config/... properties
        """
        vports = self._api.select_vports()
        imports = []
        for layer1 in self._api.config.layer1:
            for port_name in layer1.ports:
                vport = vports[port_name]
                if vport['connectionState'] in ['connectedLinkUp', 'connectedLinkDown']:
                    if layer1.choice == 'ethernet':
                        imports.append(self._configure_ethernet(vport, layer1.ethernet))
                    elif layer1.choice == 'one_hundred_gbe':
                        imports.append(self._configure_100gbe(vport, layer1.one_hundred_gbe))
        if len(imports) > 0:
            self._resource_manager.ImportConfig(json.dumps(imports), False)

    def _configure_ethernet(self, vport, ethernet):
        advertise = []
        if ethernet.advertise_one_thousand_mbps is True:
            advertise.append(Vport._ADVERTISE_MAP['advertise_one_thousand_mbps'])
        if ethernet.advertise_one_hundred_fd_mbps is True:
            advertise.append(Vport._ADVERTISE_MAP['advertise_one_hundred_fd_mbps'])
        if ethernet.advertise_one_hundred_hd_mbps is True:
            advertise.append(Vport._ADVERTISE_MAP['advertise_one_hundred_hd_mbps'])
        if ethernet.advertise_ten_fd_mbps is True:
            advertise.append(Vport._ADVERTISE_MAP['advertise_ten_fd_mbps'])
        if ethernet.advertise_ten_hd_mbps is True:
            advertise.append(Vport._ADVERTISE_MAP['advertise_ten_hd_mbps'])
        return {
            'xpath': vport['xpath'] + '/l1Config/' + vport['type'],
            'speed': Vport._SPEED_MAP[ethernet.speed],
            'media': ethernet.media,
            'autoNegotiate': ethernet.auto_negotiate,
            'speedAuto': advertise
        }

    def _configure_100gbe(self, vport, one_hundred_gbe):
        return {
            'xpath': vport['xpath'] + '/l1Config/' + vport['type'],
            'ieeeL1Defaults': one_hundred_gbe.ieee_media_defaults,
            'speed': Vport._SPEED_MAP[one_hundred_gbe.speed],
            'enableAutoNegotiation': one_hundred_gbe.auto_negotiate,
            'enableRsFec': one_hundred_gbe.rs_fec,
            'linkTraining': one_hundred_gbe.link_training,
        }

    def control_link_state(self, port_names, link_state):
        pass

    def control_capture_state(self, port_names, capture_state):
        pass

    def results(self):
        stats = self._api.assistant.StatViewAssistant('Port Statistics')
        # add location state, link state, capture state into each port result