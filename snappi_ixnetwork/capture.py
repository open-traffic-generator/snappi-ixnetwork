import json

class Capture(object):
    """Transforms OpenAPI objects into IxNetwork objects

    Args
    ----
    - ixnetworkapi (Api): instance of the Api class

    Transformations
    ---------------
    - /components/schemas/Capture to /vport/capture

    Process
    -------
    - Configure capture according to Filter

    Notes
    -----

    """
    _IPV4_OFFSET_MAP = {
        'version': '14',
        'headeer_length': '14',
        'priority': '15',
        'total_length': '16',
        'identification': '18',
        'reserved': '20',
        'dont_fragment': '20',
        'more_fragments': '20',
        'fragment_offset': '20',
        'time_to_live': '22',
        'protocol': '23',
        'header_checksum': '24',
        'src': '26',
        'dst': '30',
    }
    
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
    
    def _import(self, imports):
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False)
            for item in errata:
                self._api.warning(item)
            return len(errata) == 0
        return True
    
    def config(self):
        """Overwrite any capture settings
        """
        self._resource_manager = self._api._ixnetwork.ResourceManager
        imports = []
        vports = self._api.select_vports()
        for vport in vports.values():
            if vport['capture']['hardwareEnabled'] is True or vport['capture'][
                    'softwareEnabled'] is True:
                capture = {
                    'xpath': vport['capture']['xpath'],
                    'captureMode': 'captureTriggerMode',
                    'hardwareEnabled': False,
                    'softwareEnabled': False
                }
                imports.append(capture)
        for capture_item in self._api.snappi_config.captures:
            if capture_item.port_names is None:
                continue
            for port_name in capture_item.port_names:
                capture_mode = 'captureTriggerMode'
                if capture_item.overwrite:
                    capture_mode = 'captureContinuousMode'
                    reset = {'xpath': vports[port_name]['xpath'] + '/capture/trigger'}
                    reset['captureTriggerEnable'] = False
                    self._import(reset)
                capture = {
                    'xpath': vports[port_name]['xpath'] + '/capture',
                    'captureMode': capture_mode,
                    'hardwareEnabled': True,
                    'softwareEnabled': False
                }
                pallette = {'xpath': capture['xpath'] + '/filterPallette'}
                filter = {'xpath': capture['xpath'] + '/filter'}
                trigger = {'xpath': capture['xpath'] + '/trigger'}
                if len(capture_item.filters) > 0:
                    filter['captureFilterEnable'] = True
                    trigger['captureTriggerEnable'] = True
                    filter['captureFilterEnable'] = True
                    for cap_filter in capture_item.filters:
                        if cap_filter.parent.choice is 'ethernet':
                            self._config_ethernet_pallette(cap_filter,
                                                           pallette,
                                                           trigger,
                                                           filter)
                        elif cap_filter.parent.choice is 'custom':
                            self._config_custom_pallete(cap_filter,
                                                        pallette,
                                                        trigger,
                                                        filter)
                        else:
                            self._config_missing_pallete(cap_filter,
                                                        pallette,
                                                        trigger,
                                                        filter)
                imports.append(capture)
                imports.append(pallette)
                imports.append(filter)
                imports.append(trigger)
        self._import(imports)

    def _config_missing_pallete(self, cap_filter, pallette, trigger, filter):
        pallete_map = getattr(self, '_{0}_OFFSET_MAP'.format(
                                cap_filter.parent.choice.upper()))
        for field_name in dir(cap_filter):
            if field_name in pallete_map:
                cap_field = getattr(cap_filter, field_name)
                if cap_field.value is not None:
                    new_pattern = GetPattern(filter.get(
                                        'captureFilterPattern'))
                    pallette[new_pattern.pattern] = cap_field.value
                    pallette[new_pattern.pattern_offset] = pallete_map[
                                field_name]
                    if cap_field.mask is not None:
                        pallette[new_pattern.pattern_mask] = cap_field.mask
                    if cap_field.negate is not None and \
                        cap_field.negate is True:
                        filter['captureFilterPattern'] = 'notPattern1'
                    else:
                        filter['captureFilterPattern'] = new_pattern.filter_pattern
                    trigger['triggerFilterPattern'] = filter[
                        'captureFilterPattern']
                
                    
    def _config_custom_pallete(self, cap_filter, pallette, trigger, filter):
        if cap_filter.value is not None:
            pallette['pattern1'] = cap_filter.value
            if cap_filter.mask is not None:
                pallette['patternMask1'] = cap_filter.mask
            if cap_filter.offset is not None:
                pallette['patternOffset1'] = cap_filter.offset
            if cap_filter.negate is not None and \
                    cap_filter.negate is True:
                filter['captureFilterPattern'] = 'notPattern1'
            else:
                filter['captureFilterPattern'] = 'pattern1'
            trigger['triggerFilterPattern'] = filter[
                'captureFilterPattern']

    def _config_ethernet_pallette(self, cap_filter, pallette, trigger, filter):
        if cap_filter.src.value is not None:
            pallette['SA1'] = cap_filter.src.value
            if cap_filter.src.mask is not None:
                pallette['SAMask1'] = cap_filter.src.mask
            if cap_filter.src.negate is not None and \
                    cap_filter.src.negate is True:
                filter['captureFilterSA'] = 'notAddr1'
            else:
                filter['captureFilterSA'] = 'addr1'
            trigger['triggerFilterSA'] = filter[
                'captureFilterSA']
        if cap_filter.dst.value is not None:
            pallette['DA1'] = cap_filter.dst.value
            if cap_filter.dst.mask is not None:
                pallette['DAMask1'] = cap_filter.dst.mask
            if cap_filter.dst.negate is not None and \
                    cap_filter.dst.negate is True:
                filter['captureFilterDA'] = 'notAddr1'
            else:
                filter['captureFilterDA'] = 'addr1'
            trigger['triggerFilterDA'] = filter[
                'captureFilterDA']
            
class GetPattern(object):
    """ This is validating captureFilterPattern and return expected patterns
    """
    def __init__(self, cap_filter_pattern):
        self._new_count = 1
        self.cap_filter_pattern = cap_filter_pattern
        self._validate_pattern(cap_filter_pattern)
    
    def _validate_pattern(self, cap_filter_pattern):
        if cap_filter_pattern is not None:
            self._new_count = 2
    
    @property
    def pattern(self):
        return 'pattern{0}'.format(self._new_count)
    
    @property
    def pattern_mask(self):
        return 'patternMask{0}'.format(self._new_count)
    
    @property
    def pattern_offset(self):
        return 'patternOffset{0}'.format(self._new_count)
    
    @property
    def filter_pattern(self):
        if self._new_count is 1:
            return 'pattern{0}'.format(self._new_count)
        else:
            return '{0}AndPattern{1}'.format(self.cap_filter_pattern,
                                             self._new_count)
        
        