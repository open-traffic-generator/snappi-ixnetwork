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
        'one_thousand_mbps': 'speed1000',
        'one_hundred_fd_mbps': 'speed100fd',
        'one_hundred_hd_mbps': 'speed100hd',
        'one_hundred_gbps': 'speed100g',
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
        ixn_vport = self._api._vport
        for vport in ixn_vport.find():
            if self._api.find_item(self._api.config.ports, 'name', vport.Name) is None:
                vport.remove()
        ixn_vport.find()
        for port in self._api.config.ports:
            args = {
                'Name': port.name
            }
            ixn_vport.find(Name=port.name)
            if len(ixn_vport) == 0:
                ixn_vport.add(**args)
            else:
                ixn_vport.update(**args)
            self._api.ixn_objects[port.name] = ixn_vport.href

    def config_layer1(self):
        resource_manager = self._api._ixnetwork.ResourceManager
        vports = json.loads(resource_manager.ExportConfig(['/vport'], True, 'json'))
        imports = []
        for port in self._api.config.ports:
            vport = {
                'xpath': parse('$.vport[?(@.name="%s")].xpath' % port.name).find(vports)[0].value,
                'location': port.location,
                'rxMode': 'capture',
                'txMode': 'interleaved'
            }
            imports.append(vport)
        for layer1 in self._api.config.layer1:
            for port_name in layer1.ports:
                vport = parse('$.vport[?(@.name="%s")]' % port_name).find(vports)[0].value
                if layer1.choice == 'ethernet':
                    imports.append(self._configure_ethernet(vport, layer1.ethernet))
                elif layer1.choice == 'one_hundred_gbe':
                    imports.append(self._configure_uhd(vport, layer1.one_hundred_gbe))
        resource_manager.ImportConfig(json.dumps(imports), False)

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
            'xpath': vport['xpath'] + '/l1Config/ethernet',
            'speed': Vport._SPEED_MAP[ethernet.speed],
            'media': ethernet.media,
            'autoNegotiate': ethernet.auto_negotiate,
            'speedAuto': advertise
        }

    def _configure_uhd(self, vport, one_hundred_gbe):
        return {
            'xpath': vport['xpath'] + '/l1Config/uhdOneHundredGigLan',
            'ieeeL1Defaults': one_hundred_gbe.ieee_media_defaults,
            'speed': Vport._SPEED_MAP[one_hundred_gbe.speed],
            'enableAutoNegotiation': one_hundred_gbe.auto_negotiate,
            'enableRsFec': one_hundred_gbe.rs_fec,
            'linkTraining': one_hundred_gbe.link_training,
        }
