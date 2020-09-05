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
        1) delete any vport that is not part of the config
        2) create a vport for every config.ports[] that is not present in IxNetwork
        3) set config.ports[].location to /vport -location using resourcemanager
        4) set /vport/l1Config/... properties using the corrected /vport -type
        5) connectPorts to use new l1Config settings and clearownership
        """
        self._ixn_vport = self._api._vport
        self._delete_vports()
        self._create_vports()
        self._set_location()
        self._set_layer1()
        self._connect()

    def _delete_vports(self):
        self._api._remove(self._ixn_vport, self._api.config.ports)
    
    def _create_vports(self):
        vports = self._api.select_vports()
        for port in self._api.config.ports:
            if port.name not in vports.keys():
                self._ixn_vport.add(Name=port.name)
    
    def _set_location(self):
        vports = self._api.select_vports()
        imports = []
        for port in self._api.config.ports:
            self._api.ixn_objects[port.name] = vports[port.name]['href']
            vport = {
                'xpath': vports[port.name]['xpath'],
                'location': getattr(port, 'location', None),
                'rxMode': 'capture',
                'txMode': 'interleaved'
            }
            imports.append(vport)
        self._resource_manager = self._api._ixnetwork.ResourceManager
        self._resource_manager.ImportConfig(json.dumps(imports), False)

    def _set_layer1(self):
        """Set the /vport/l1Config/... properties
        """
        vports = self._api.select_vports()
        imports = []
        if hasattr(self._api.config, 'layer1') is True:
            for layer1 in self._api.config.layer1:
                for port_name in layer1.port_names:
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

    def _connect(self):
        self._ixn_vport.find()
        self._ixn_vport.ConnectPorts(True)

    def control_link_state(self, port_names, link_state):
        pass

    def control_capture_state(self, port_names, capture_state):
        pass

    def results(self, request):
        results = {
            'ports': []
        }
        stats = self._api.assistant.StatViewAssistant('Port Statistics')
        # add location state, link state, capture state into each port result