import json
from jsonpath_ng.ext import parse
import time
import re
from ixnetwork_open_traffic_generator.timer import Timer


class Vport(object):
    """Transforms OpenAPI objects into IxNetwork objects

    - Port to /vport
    - Port.Capture to /vport/capture
    - Port.Layer1 to /vport/l1Config/...

    Uses resourcemanager to set the vport location and l1Config as it is the
    most efficient way.  
    DO NOT use the AssignPorts API as it is too slow. 

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the IxNetworkApi class
    """
    _SPEED_MAP = {
        'speed_100_gbps': 'speed100g',
        'speed_50_gbps': 'speed50g',
        'speed_40_gbps': 'speed40g',
        'speed_25_gbps': 'speed25g',
        'speed_10_gbps': 'speed10g',
        'speed_1_gbps': 'speed1000',
        'speed_100_fd_mbps': 'speed100fd',
        'speed_100_hd_mbps': 'speed100hd',
        'speed_10_fd_mbps': 'speed10fd',
        'speed_10_hd_mbps': 'speed10hd'
    }
    _ADVERTISE_MAP = {
        'advertise_one_thousand_mbps': 'speed1000',
        'advertise_one_hundred_fd_mbps': 'speed100fd',
        'advertise_one_hundred_hd_mbps': 'speed100hd',
        'advertise_ten_fd_mbps': 'speed10fd',
        'advertise_ten_hd_mbps': 'speed10hd'
    }
    _FLOW_CONTROL_MAP = {
        'ieee_802_1qbb': 'ieee802.1Qbb',
        'ieee_802_3x': 'ieee_802_3x'
    }
    _RESULT_COLUMNS = [
        'name', 'location', 'link', 'capture', 'frames_tx', 'frames_rx',
        'frames_tx_rate', 'frames_rx_rate', 'bytes_tx', 'bytes_rx',
        'bytes_tx_rate', 'bytes_rx_rate', 'pfc_class_0_frames_rx',
        'pfc_class_1_frames_rx', 'pfc_class_2_frames_rx',
        'pfc_class_3_frames_rx', 'pfc_class_4_frames_rx',
        'pfc_class_5_frames_rx', 'pfc_class_6_frames_rx',
        'pfc_class_7_frames_rx'
    ]

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
        self._resource_manager = self._api._ixnetwork.ResourceManager
        self._ixn_vport = self._api._vport
        with Timer(self._api, 'Ports configuration'):
            self._delete_vports()
            self._create_vports()
        with Timer(self._api, 'Captures configuration'):
            self._create_capture()
        with Timer(self._api, 'Location configuration'):
            self._set_location()
        with Timer(self._api, 'Layer1 configuration'):
            self._set_layer1()

    def _import(self, imports):
        if len(imports) > 0:
            self._resource_manager.ImportConfig(json.dumps(imports), False)

    def _delete_vports(self):
        """Delete any vports from the api server that do not exist in the new config
        """
        self._api._remove(self._ixn_vport, self._api.config.ports)

    def _create_vports(self):
        """Add any vports to the api server that do not already exist
        """
        vports = self._api.select_vports()
        imports = []
        for port in self._api.config.ports:
            if port.name not in vports.keys():
                index = len(vports) + len(imports) + 1
                imports.append({
                    'xpath': '/vport[%i]' % index,
                    'name': port.name,
                    'rxMode': 'captureAndMeasure',
                    'txMode': 'interleaved'
                })
        self._import(imports)
        for name, vport in self._api.select_vports().items():
            self._api.ixn_objects[name] = vport['href']

    def _create_capture(self):
        """Overwrite any capture settings
        """
        if self._api.config.captures is None:
            self._api.config.captures = []
        imports = []
        vports = self._api.select_vports()
        for vport in vports.values():
            if vport['capture']['hardwareEnabled'] is True or vport['capture']['softwareEnabled'] is True:
                capture = {
                    'xpath': vport['capture']['xpath'],
                    'captureMode': 'captureTriggerMode',
                    'hardwareEnabled': False,
                    'softwareEnabled': False
                }
                imports.append(capture)
        for capture_item in self._api.config.captures:
            for port_name in capture_item.port_names:
                capture = {
                    'xpath': vports[port_name]['xpath'] + '/capture',
                    'captureMode': 'captureTriggerMode',
                    'hardwareEnabled': False,
                    'softwareEnabled': False
                }
                pallette = {'xpath': capture['xpath'] + '/filterPallette'}
                filter = {'xpath': capture['xpath'] + '/filter'}
                trigger = {'xpath': capture['xpath'] + '/trigger'}
                if capture_item.basic is not None:
                    capture['hardwareEnabled'] = True
                    filter['captureFilterEnable'] = True
                    trigger['captureTriggerEnable'] = True
                    filter['captureFilterEnable'] = True
                    for basic in capture_item.basic:
                        if basic.choice == 'mac_address' and basic.mac_address.mac == 'source':
                            pallette['SA1'] = basic.mac_address.filter
                            pallette['SAMask1'] = basic.mac_address.mask
                            filter[
                                'captureFilterSA'] = 'notAddr1' if basic.not_operator is True else 'addr1'
                            trigger['triggerFilterSA'] = filter[
                                'captureFilterSA']
                        elif basic.choice == 'mac_address' and basic.mac_address.mac == 'destination':
                            pallette['DA1'] = basic.mac_address.filter
                            pallette['DAMask1'] = basic.mac_address.mask
                            filter[
                                'captureFilterDA'] = 'notAddr1' if basic.not_operator is True else 'addr1'
                            trigger['triggerFilterDA'] = filter[
                                'captureFilterDA']
                        elif basic.choice == 'custom':
                            pallette['pattern1'] = basic.custom.filter
                            pallette['patternMask1'] = basic.custom.mask
                            pallette['patternOffset1'] = basic.custom.offset
                            filter[
                                'captureFilterPattern'] = 'notPattern1' if basic.not_operator is True else 'pattern1'
                            trigger['triggerFilterPattern'] = filter[
                                'captureFilterPattern']
                imports.append(capture)
                imports.append(pallette)
                imports.append(filter)
                imports.append(trigger)
        self._import(imports)

    def _add_hosts(self, HostReadyTimeout):
        chassis = self._api._ixnetwork.AvailableHardware.Chassis
        add_addresses = []
        check_addresses = []
        for port in self._api.config.ports:
            if port.location is not None and ';' in port.location:
                chassis_address = port.location.split(';')[0]
                chassis.find(Hostname='^(%s)$' % chassis_address)
                if len(chassis) == 0:
                    add_addresses.append(chassis_address)
                check_addresses.append(chassis_address)
        add_addresses = set(add_addresses)
        check_addresses = set(check_addresses)
        if len(add_addresses) > 0:
            with Timer(self._api, 'Add location hosts [%s]' % ', '.join(add_addresses)):      
                for add_address in add_addresses:
                    chassis.add(Hostname=add_address)
        if len(check_addresses) > 0:
            with Timer(self._api, 'Location hosts check [%s]' % ', '.join(check_addresses)):      
                start_time = time.time()
                while True:
                    chassis.find(Hostname='^(%s)$' % '|'.join(check_addresses),
                                State='^ready$')
                    if len(chassis) == len(check_addresses):
                        break
                    if time.time() - start_time > HostReadyTimeout:
                        raise RuntimeError(
                            'After %s seconds, not all location hosts [%s] are reachable'
                            % (HostReadyTimeout, ', '.join(check_addresses)))
                    time.sleep(2)

    def _set_location(self):
        location_supported = True
        try:
            self._api._ixnetwork._connection._options(self._api._ixnetwork.href + '/locations')
        except:
            location_supported = False

        locations = []
        self._add_hosts(10)
        vports = self._api.select_vports()
        imports = []
        clear_locations = []
        for port in self._api.config.ports:
            vport = vports[port.name]
            location = getattr(port, 'location', None)
            if location_supported is True:
                if vport['location'] == location and vport[
                        'connectionState'].startswith('connectedLink'):
                    continue
            else:
                if len(vport['connectedTo']) > 0 and vport[
                        'connectionState'].startswith('connectedLink'):
                    continue
            self._api.ixn_objects[port.name] = vport['href']
            vport = {'xpath': vports[port.name]['xpath']}
            if location_supported is True:
                vport['location'] = location
            else:
                if location is not None:
                    xpath = self._api.select_chassis_card_port(location)
                    vport['connectedTo'] = xpath
                else:
                    vport['connectedTo'] = ''
            imports.append(vport)
            if location is not None and len(location) > 0:
                clear_locations.append(location)
                locations.append(port.name)
        if len(locations) == 0:
            return
        self._clear_ownership(clear_locations)
        with Timer(self._api, 'Location connect [%s]' % ', '.join(locations)):
            self._import(imports)
        with Timer(self._api, 'Location state check [%s]' % ', '.join(locations)):
            self._api._vport.find(ConnectionState='^(?!connectedLink).*$')
            if len(self._api._vport) > 0:
                self._api._vport.ConnectPorts()
            start = time.time()
            timeout = 30
            while True:
                self._api._vport.find(Name='^(%s)$' % '|'.join(locations),
                                    ConnectionState='^connectedLink')
                if len(self._api._vport) == len(locations):
                    break
                if time.time() - start > timeout:
                    raise RuntimeError(
                        'After %s seconds, not all locations [%s] are reachable' %
                        (timeout, ', '.join([vport.Name for vport in self._api._vport])))
                time.sleep(2)
            for vport in self._api._vport.find(ConnectionState='^(?!connectedLinkUp).*$'):
                self._api.warning('%s %s' % (vport.Name, vport.ConnectionState))

    def _set_layer1(self):
        """Set the /vport/l1Config/... properties
        This should only happen if the vport connectionState is connectedLink...
        as it determines the ./l1Config child node.
        """
        if hasattr(self._api.config, 'layer1') is False:
            return
        if self._api.config.layer1 is None:
            return
        vports = self._api.select_vports()
        imports = []
        reset_auto_negotiation = dict()
        for layer1 in self._api.config.layer1:
            for port_name in layer1.port_names:
                vport = vports[port_name]
                self._set_l1config_properties(vport, layer1, imports)
        self._import(imports)
        # Due to dependency attribute (ieeeL1Defaults) resetting enableAutoNegotiation
        imports = []
        for layer1 in self._api.config.layer1:
            for port_name in layer1.port_names:
                vport = vports[port_name]
                if port_name in reset_auto_negotiation and reset_auto_negotiation[
                        port_name]:
                    self._reset_auto_negotiation(vport, layer1, imports)
        self._import(imports)

    def _set_l1config_properties(self, vport, layer1, imports):
        """Set vport l1config properties
        """
        if vport['connectionState'] not in [
                'connectedLinkUp', 'connectedLinkDown'
        ]:
            return
        self._set_vport_type(vport, layer1, imports)
        self._set_card_resource_mode(vport, layer1, imports)
        self._set_auto_negotiation(vport, layer1, imports)

    def _set_card_resource_mode(self, vport, layer1, imports):
        """If the card has an aggregation mode set it according to the speed
        """
        speed_mode_map = {
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
        aggregation_mode = None
        if layer1.speed in speed_mode_map:
            mode = speed_mode_map[layer1.speed]
            card = self._api.select_chassis_card(vport)
            for available_mode in card['availableModes']:
                if re.search(mode, available_mode.lower()) is not None:
                    aggregation_mode = available_mode
                    break
        if aggregation_mode is not None and aggregation_mode != card[
                'aggregationMode']:
            self._api.info('Setting %s layer1 mode' % aggregation_mode)
            imports.append({
                'xpath': card['xpath'],
                'aggregationMode': aggregation_mode
            })

    def _set_auto_negotiation(self, vport, layer1, imports):
        if layer1.speed.endswith('_mbps') or layer1.speed == 'speed_1_gbps':
            self._set_ethernet_auto_negotiation(vport, layer1, imports)
        else:
            self._set_gigabit_auto_negotiation(vport, layer1, imports)

    def _set_vport_type(self, vport, layer1, imports):
        """Set the /vport -type
        
        If flow_control is not None then the -type attribute should 
        be switched to a type with the Fcoe extension if it is allowed.

        If flow_control is None then the -type attribute should 
        be switched to a type without the Fcoe extension.
        """
        fcoe = False
        if hasattr(layer1, 'flow_control') and layer1.flow_control is not None:
            fcoe = True
        vport_type = vport['type']
        elegible_fcoe_vport_types = [
            'ethernet', 'tenGigLan', 'fortyGigLan', 'tenGigWan',
            'hundredGigLan', 'tenFortyHundredGigLan', 'novusHundredGigLan',
            'novusTenGigLan', 'krakenFourHundredGigLan', 'aresOneHundredGigLan'
        ]
        if fcoe is True and vport_type in elegible_fcoe_vport_types:
            vport_type = vport_type + 'Fcoe'
        if fcoe is False and vport_type.endswith('Fcoe'):
            vport_type = vport_type.replace('Fcoe', '')
        if vport_type != vport['type']:
            imports.append({'xpath': vport['xpath'], 'type': vport_type})
        if fcoe is True and vport_type.endswith('Fcoe'):
            self._configure_fcoe(vport, layer1.flow_control, imports)
        return vport_type

    def _set_ethernet_auto_negotiation(self, vport, layer1, imports):
        advertise = []
        if layer1.speed == 'speed_1_gbps':
            advertise.append(
                Vport._ADVERTISE_MAP['advertise_one_thousand_mbps'])
        if layer1.speed == 'speed_100_fd_mbps':
            advertise.append(
                Vport._ADVERTISE_MAP['advertise_one_hundred_fd_mbps'])
        if layer1.speed == 'speed_100_hd_mbps':
            advertise.append(
                Vport._ADVERTISE_MAP['advertise_one_hundred_hd_mbps'])
        if layer1.speed == 'speed_10_fd_mbps':
            advertise.append(Vport._ADVERTISE_MAP['advertise_ten_fd_mbps'])
        if layer1.speed == 'speed_10_hd_mbps':
            advertise.append(Vport._ADVERTISE_MAP['advertise_ten_hd_mbps'])
        proposed_import = {
            'xpath':
            vport['xpath'] + '/l1Config/' + vport['type'].replace('Fcoe', ''),
            'speed':
            Vport._SPEED_MAP[layer1.speed],
            'media':
            layer1.media,
            'autoNegotiate':
            layer1.auto_negotiate,
            'speedAuto':
            advertise
        }
        self._add_l1config_import(vport, proposed_import, imports)

    def _add_l1config_import(self, vport, proposed_import, imports):
        type = vport['type'].replace('Fcoe', '')
        l1config = vport['l1Config'][type]
        for key in proposed_import:
            if key == 'xpath':
                continue
            if key in l1config and l1config[key] != proposed_import[key]:
                imports.append(proposed_import)
                return

    def _set_gigabit_auto_negotiation(self, vport, layer1, imports):
        proposed_import = {
            'xpath':
            vport['xpath'] + '/l1Config/' + vport['type'].replace('Fcoe', ''),
            'ieeeL1Defaults':
            layer1.ieee_media_defaults,
            'speed':
            Vport._SPEED_MAP[layer1.speed],
            'enableAutoNegotiation': layer1.auto_negotiate,
            'enableRsFec': None if layer1.auto_negotiation is None else layer1.auto_negotiation.rs_fec,
            'linkTraining': None if layer1.auto_negotiation is None else layer1.auto_negotiation.link_training
        }
        self._add_l1config_import(vport, proposed_import, imports)

    def _reset_auto_negotiation(self, vport, layer1, imports):
        if layer1.speed.endswith(
                '_mbps') is False and layer1.speed != 'speed_1_gbps':
            imports.append({
                'xpath':
                vport['xpath'] + '/l1Config/' +
                vport['type'].replace('Fcoe', ''),
                'enableAutoNegotiation':
                layer1.auto_negotiate,
            })

    def _configure_fcoe(self, vport, flow_control, imports):
        if flow_control is not None and flow_control.choice == 'ieee_802_1qbb':
            pfc = flow_control.ieee_802_1qbb
            fcoe = {
                'xpath':
                vport['xpath'] + '/l1Config/' + vport['type'] + '/fcoe',
                'enablePFCPauseDelay':
                True,
                'flowControlType':
                Vport._FLOW_CONTROL_MAP[flow_control.choice],
                'pfcPauseDelay':
                pfc.pfc_delay,
                'pfcPriorityGroups': [
                    -1 if pfc.pfc_class_0 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_1 is None else pfc.pfc_class_1,
                    -1 if pfc.pfc_class_2 is None else pfc.pfc_class_2,
                    -1 if pfc.pfc_class_3 is None else pfc.pfc_class_3,
                    -1 if pfc.pfc_class_4 is None else pfc.pfc_class_4,
                    -1 if pfc.pfc_class_5 is None else pfc.pfc_class_5,
                    -1 if pfc.pfc_class_6 is None else pfc.pfc_class_6,
                    -1 if pfc.pfc_class_7 is None else pfc.pfc_class_7,
                ],
                'priorityGroupSize':
                'priorityGroupSize-8',
                'supportDataCenterMode':
                True
            }
            imports.append(fcoe)

    def _clear_ownership(self, locations):
        try:
            force_ownership = self._api.config.options.port_options.location_preemption
        except:
            force_ownership = False
        if force_ownership is True:
            available_hardware_hrefs = {}
            location_hrefs = {}
            for location in locations:
                if ';' in location:
                    clp = location.split(';')
                    chassis = self._api._ixnetwork.AvailableHardware.Chassis.find(Hostname=clp[0])
                    if len(chassis) > 0:
                        available_hardware_hrefs[location] = '%s/card/%s/port/%s' % (
                            chassis.href, abs(int(clp[1])), abs(int(clp[2])))
                elif '/' in location:
                    appliance = location.split('/')[0]
                    locations = self._api._ixnetwork.Locations
                    locations.find(Hostname=appliance)  
                    if len(locations) == 0:    
                        locations.add(Hostname=appliance)
                    ports = locations.Ports.find(Location='^%s$' % location)
                    if len(ports) > 0:
                        location_hrefs[location] = ports.href
            self._api.clear_ownership(available_hardware_hrefs, location_hrefs)

    def _set_result_value(self,
                          row,
                          column_name,
                          column_value,
                          column_type=str):
        if len(self._column_names
               ) > 0 and column_name not in self._column_names:
            return
        try:
            row[column_name] = column_type(column_value)
        except:
            if column_type.__name__ in ['float', 'int']:
                row[column_name] = 0
            else:
                row[column_type] = column_value

    def results(self, request):
        """Return port results
        """
        if request.column_names is None:
            self._column_names = []
        else:
            self._column_names = request.column_names
        port_rows = {}
        for vport in self._api.select_vports().values():
            port_row = {}
            self._set_result_value(port_row, 'name', vport['name'])
            location = vport['location']
            if vport['connectionState'].startswith('connectedLink') is True:
                location += ';connected'
            elif len(location) > 0:
                location += ';' + vport['connectionState']
            else:
                location = vport['connectionState']
            self._set_result_value(port_row, 'location', location)
            self._set_result_value(
                port_row, 'link', 'up'
                if vport['connectionState'] == 'connectedLinkUp' else 'down')
            self._set_result_value(port_row, 'capture', 'stopped')
            port_rows[vport['name']] = port_row
        try:
            table = self._api.assistant.StatViewAssistant('Port Statistics')
            for row in table.Rows:
                port_row = port_rows[row['Port Name']]
                self._set_result_value(port_row, 'frames_tx',
                                       row['Frames Tx.'], int)
                self._set_result_value(port_row, 'frames_rx',
                                       row['Valid Frames Rx.'], int)
                self._set_result_value(port_row, 'frames_tx_rate',
                                       row['Frames Tx. Rate'], float)
                self._set_result_value(port_row, 'frames_rx_rate',
                                       row['Valid Frames Rx. Rate'], float)
                self._set_result_value(port_row, 'bytes_tx', row['Bytes Tx.'],
                                       int)
                self._set_result_value(port_row, 'bytes_rx', row['Bytes Rx.'],
                                       int)
                self._set_result_value(port_row, 'bytes_tx_rate',
                                       row['Bytes Tx. Rate'], float)
                self._set_result_value(port_row, 'bytes_rx_rate',
                                       row['Bytes Rx. Rate'], float)
                self._set_result_value(port_row, 'pfc_class_0_frames_rx',
                                       row['Rx Pause Priority Group 0 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_1_frames_rx',
                                       row['Rx Pause Priority Group 1 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_2_frames_rx',
                                       row['Rx Pause Priority Group 2 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_3_frames_rx',
                                       row['Rx Pause Priority Group 3 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_4_frames_rx',
                                       row['Rx Pause Priority Group 4 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_5_frames_rx',
                                       row['Rx Pause Priority Group 5 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_6_frames_rx',
                                       row['Rx Pause Priority Group 6 Frames'],
                                       int)
                self._set_result_value(port_row, 'pfc_class_7_frames_rx',
                                       row['Rx Pause Priority Group 7 Frames'],
                                       int)
        except:
            pass
        return port_rows.values()
