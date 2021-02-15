import re

class ResourceGroup(object):
    """"""
    _SPEED_MODE_MAP = {
        'speed_1_gbps': 'normal',
        'speed_10_gbps': 'tengig',
        'speed_25_gbps': 'twentyfivegig',
        'speed_40_gbps': 'fortygig',
        'speed_50_gbps': 'fiftygig',
        'speed_100_gbps':
            '^(?!.*(twohundredgig|fourhundredgig)).*hundredgig.*$',
        'speed_200_gbps': 'twohundredgig',
        'speed_400_gbps': 'fourhundredgig'
    }
    
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._store_properties = []
        self._layer1_conf = None
        self.layer1_check = []
        
    def set_group(self):
        self.layer1_check = []
        self._store_properties = []
        self._layer1_conf = self._api.snappi_config.layer1
        if self._layer1_conf  is None or len(
                self._layer1_conf ) == 0:
            return
        
        response = None
        try:
            payload = {"arg1": "/availableHardware", "arg2" : []}
            url = '%s/availableHardware/operations/getChassisWithDetailedResouceGroupsInfo' \
                  % self._api._ixnetwork.href
            response = self._api._request('POST', url, payload)
        except Exception:
            raise Exception("Not able to fetch chassis details. Unable to execute L1 setting")
        
        self._process_property()
        try:
            chassis_id = 1
            result = response['result'][0]
            self._process_groups(result['cards'], chassis_id)
        except Exception:
            raise Exception("Problem to parse chassis details")
        
        final_arg2 = []
        error_ports = []
        ixn_href = self._api._ixnetwork.href
        for property in self._store_properties:
            args = [arg['arg1'] for arg in final_arg2]
            url = property.get_url(ixn_href)
            if property.group_mode is None:
                error_ports.append(property.port_name)
                continue
            if url is not None and url not in args:
                arg2 = {
                    "arg1" : url,
                    "arg2" : property.group_mode
                }
                final_arg2.append(arg2)
        
        if len(error_ports) > 0:
            raise Exception("Please check the speed of these ports ",
                            error_ports)
        if len(final_arg2) > 0:
            url = "{0}/availableHardware/operations/" \
                  "setresourcegroupsinfo".format(ixn_href)
            payload = {
                "arg1": "/availableHardware",
                "arg2": final_arg2,
                "arg3": True,
                "arg4": True
            }
            try:
                self._api._request('POST', url, payload)
            except:
                # todo: redirect to unknown page. Probable IxNetwork issue
                pass
        
        return self.layer1_check

    def _process_property(self):
        chassis_list = []
        port_list = []
        ports = self._api.snappi_config.ports
        for layer1 in self._layer1_conf:
            if layer1.port_names is None or len(
                    layer1.port_names) == 0:
                return
            for port in ports:
                if port in port_list:
                    return
                if port.name in layer1.port_names:
                    if ';' in port.location:
                        (chassis, cardid, portid) = port.location.split(';')
                    else:
                        cardid = 0
                        (chassis, portid) = port.location.split('/')
                    if chassis not in chassis_list:
                        chassis_list.append(chassis)
                    property = StoreProperty(chassis,
                                  cardid,
                                  portid,
                                  port.name,
                                  layer1)
                    self._store_properties.append(
                            property)
        return chassis_list
                    
    def _get_property(self, display_name):
        for property in self._store_properties:
            if property.port == display_name:
                return property
        return None
    
    def _process_groups(self, cards, chassis_id):
        for card in cards:
            if card['cardAggregationMode'] == 'notSupported':
                return
            card_id = card['cardId']
            for supported_group in card['supportedGroups']:
                group_id = supported_group['id']
                current_mode = supported_group['currentSetting'][
                        'resourceGroupMode']
                for avialable_setting in supported_group[
                        'availableSettings']:
                    group_mode = avialable_setting[
                            'resourceGroupMode']
                    for panel_info in avialable_setting[
                            'panelInfo']:
                        for display_name in panel_info[
                                'activePortsDisplayNames']:
                            property = self._get_property(display_name)
                            if property is not None:
                                l1_name = property.set_property(chassis_id,
                                                      card_id,
                                                      group_id,
                                                      current_mode,
                                                      group_mode)
                                if l1_name is not None \
                                        and l1_name not in self.layer1_check:
                                    self.layer1_check.append(l1_name)
                                    
class StoreProperty(object):
    def __init__(self, chassis, card, port, port_name, layer1):
        self._chassis = chassis
        self._card = card
        self._port = port
        self._port_name = port_name
        self._map_speed = self._set_speed(layer1.speed)
        self._l1name = layer1.name
        self._chassis_id = None
        self._card_id = None
        self._group_id = None
        self._current_mode = None
        self._group_mode = None
        
    @property
    def port(self):
        return self._port
    
    @property
    def group_mode(self):
        return self._group_mode
    
    @property
    def port_name(self):
        return self._port_name
    
    @property
    def l1name(self):
        return self._l1name
    
    def _set_speed(self, speed):
        speed_mode_map = ResourceGroup._SPEED_MODE_MAP
        if speed in speed_mode_map:
            return speed_mode_map[speed]
        else:
            raise Exception("Speed %s not avialable within internal map" %
                              speed)
    
    def set_property(self, chassis_id, card_id, group_id, current_mode, group_mode):
        if re.search(self._map_speed, group_mode.lower()) \
                is not None:
            self._chassis_id = chassis_id
            self._card_id = card_id
            self._group_id = group_id
            self._current_mode = current_mode
            self._group_mode = group_mode
            return self._l1name
        return None
    
    def get_url(self, ixn_href):
        if self._current_mode == self._group_mode:
            return None
        url = "{0}/availableHardware/chassis/{1}" \
              "/card/{2}/aggregation/{3}".format(ixn_href,
                             self._chassis_id,
                             self._card_id,
                             self._group_id)
        return url