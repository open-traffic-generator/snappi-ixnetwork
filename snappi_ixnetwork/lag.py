import json
from jsonpath_ng.ext import parse


class Lag(object):
    """Transforms OpenAPI objects into IxNetwork objects

    - Lag to /lag

    Args
    ----
    - ixnetworkapi (Api): instance of the Api class
    """
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
        self._ixn_vport = self._api._lag
        self._delete_lags()
        # self._create_vports()
        # self._create_capture()
        # self._set_location()
        # self._set_layer1()
        # self._connect()

    def _import(self, imports):
        if len(imports) > 0:
            self._resource_manager.ImportConfig(json.dumps(imports), False)

    def _delete_vports(self):
        """Delete any vports from the api server that do not exist in the new config
        """
        self._api._remove(self._ixn_lag, self._api.snappi_config.lags)
    
    def _create_vports(self):
        """Add any vports to the api server that do not already exist
        """
        vports = self._api.select_vports()
        imports = []
        for port in self._api.snappi_config.ports:
            if port.name not in vports.keys():
                index = len(vports) + len(imports) + 1
                imports.append(
                    {
                        'xpath': '/vport[%i]' % index,
                        'name': port.name,
                        'rxMode': 'captureAndMeasure',
                        'txMode': 'interleaved'
                    }
                )
        self._import(imports)
    
    def _create_capture(self):
        """Overwrite any capture settings
        """
        vports = self._api.select_vports()
        imports = []
        for port in self._api.snappi_config.ports:
            capture = {
                'xpath': vports[port.name]['xpath'] + '/capture',
                'captureMode': 'captureTriggerMode',
                'hardwareEnabled': False,
                'softwareEnabled': False
            }
            pallette = {
                'xpath': capture['xpath'] + '/filterPallette'
            }
            filter = {
                'xpath': capture['xpath'] + '/filter'
            }
            trigger = {
                'xpath': capture['xpath'] + '/trigger'
            }
            if port.capture is not None and port.capture.basic is not None:
                capture['hardwareEnabled'] = True
                filter['captureFilterEnable'] = True
                trigger['captureTriggerEnable'] = True
                filter['captureFilterEnable'] = True
                for basic in port.capture.basic:
                    if basic.choice == 'mac_address' and basic.mac_address.mac == 'source':
                        pallette['SA1'] = basic.mac_address.filter
                        pallette['SAMask1'] = basic.mac_address.mask
                        filter['captureFilterSA'] = 'notAddr1' if basic.not_operator is True else 'addr1'
                        trigger['triggerFilterSA'] = filter['captureFilterSA']
                    elif basic.choice == 'mac_address' and basic.mac_address.mac == 'destination':
                        pallette['DA1'] = basic.mac_address.filter
                        pallette['DAMask1'] = basic.mac_address.mask
                        filter['captureFilterDA'] = 'notAddr1' if basic.not_operator is True else 'addr1'
                        trigger['triggerFilterDA'] = filter['captureFilterDA']
                    elif basic.choice == 'custom':
                        pallette['pattern1'] = basic.custom.filter
                        pallette['patternMask1'] = basic.custom.mask
                        pallette['patternOffset1'] = basic.custom.offset
                        filter['captureFilterPattern'] = 'notPattern1' if basic.not_operator is True else 'pattern1'
                        trigger['triggerFilterPattern'] = filter['captureFilterPattern']
            imports.append(capture)
            imports.append(pallette)
            imports.append(filter)
            imports.append(trigger)
        self._import(imports)

    def _set_location(self):
        vports = self._api.select_vports()
        imports = []
        for port in self._api.snappi_config.ports:
            self._api.ixn_objects[port.name] = vports[port.name]['href']
            vport = {
                'xpath': vports[port.name]['xpath'],
                'location': getattr(port, 'location', None),
            }
            imports.append(vport)
        self._import(imports)

    def _set_layer1(self):
        """Set the /vport/l1Config/... properties
        """
        if hasattr(self._api.snappi_config, 'layer1') is False:
            return
        if self._api.snappi_config.layer1 is None:
            return
        vports = self._api.select_vports()
        imports = []
        reset_auto_negotiation = dict()
        for layer1 in self._api.snappi_config.layer1:
            for port_name in layer1.port_names:
                vport = vports[port_name]
                if vport['connectionState'] in ['connectedLinkUp', 'connectedLinkDown']:
                    if layer1.choice == 'ethernet':
                        self._configure_ethernet(vport, layer1, imports)
                    elif layer1.choice == 'one_hundred_gbe':
                        reset_auto_negotiation[port_name] = layer1.one_hundred_gbe.auto_negotiate is not None
                        self._configure_100gbe(vport, layer1, imports)
        self._import(imports)
        
        # Due to dependency attribute (ieeeL1Defaults) resetting enableAutoNegotiation
        imports = []
        for layer1 in self._api.snappi_config.layer1:
            for port_name in layer1.port_names:
                vport = vports[port_name]
                if port_name in reset_auto_negotiation and reset_auto_negotiation[port_name]:
                    self._reset_auto_negotiation(vport, layer1, imports)
        self._import(imports)

    def _configure_layer1_type(self, interface, vport, imports):
        """Set the /vport -type
        
        If flow_control is not None then the -type attribute should 
        be switched to a type with the Fcoe extension if it is allowed.

        If flow_control is None then the -type attribute should 
        be switched to a type without the Fcoe extension.
        """
        fcoe = False
        if hasattr(interface, 'flow_control') and interface.flow_control is not None:
            fcoe = True
        vport_type = vport['type']
        elegible_fcoe_vport_types = [
            'ethernet', 'tenGigLan', 'fortyGigLan', 'tenGigWan', 'hundredGigLan',
            'tenFortyHundredGigLan', 'novusHundredGigLan', 'novusTenGigLan',
            'krakenFourHundredGigLan', 'aresOneHundredGigLan'
        ]
        if fcoe is True and vport_type in elegible_fcoe_vport_types:
            vport_type = vport_type + 'Fcoe'
        if fcoe is False and vport_type.endswith('Fcoe'):
            vport_type = vport_type.replace('Fcoe', '')
        if vport_type != vport['type']:
            imports.append(
                {
                    'xpath': vport['xpath'],
                    'type': vport_type
                }
            )
        if fcoe is True and vport_type.endswith('Fcoe'):
            self._configure_fcoe(vport, interface.flow_control, imports)
        return vport_type

    def _configure_ethernet(self, vport, layer1, imports):
        if hasattr(layer1, 'ethernet') is True and layer1.ethernet is not None:
            self._configure_layer1_type(layer1.ethernet, vport, imports)
            ethernet = layer1.ethernet
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
            imports.append(
                {
                    'xpath': vport['xpath'] + '/l1Config/' + vport['type'].replace('Fcoe', ''),
                    'speed': Vport._SPEED_MAP[ethernet.speed],
                    'media': ethernet.media,
                    'autoNegotiate': ethernet.auto_negotiate,
                    'speedAuto': advertise
                }
            )

    def _configure_100gbe(self, vport, layer1, imports):
        if hasattr(layer1, 'one_hundred_gbe') is True and layer1.one_hundred_gbe is not None:
            self._configure_layer1_type(layer1.one_hundred_gbe, vport, imports)
            one_hundred_gbe = layer1.one_hundred_gbe
            imports.append(
                {
                    'xpath': vport['xpath'] + '/l1Config/' + vport['type'].replace('Fcoe', ''),
                    'ieeeL1Defaults': one_hundred_gbe.ieee_media_defaults,
                    'speed': Vport._SPEED_MAP[one_hundred_gbe.speed],
                    'enableAutoNegotiation': one_hundred_gbe.auto_negotiate,
                    'enableRsFec': one_hundred_gbe.rs_fec,
                    'linkTraining': one_hundred_gbe.link_training,
                }
            )
    
    def _reset_auto_negotiation(self, vport, layer1, imports):
        if hasattr(layer1, 'one_hundred_gbe') is True and layer1.one_hundred_gbe is not None:
            one_hundred_gbe = layer1.one_hundred_gbe
            imports.append(
                {
                    'xpath': vport['xpath'] + '/l1Config/' + vport['type'].replace('Fcoe', ''),
                    'enableAutoNegotiation': one_hundred_gbe.auto_negotiate,
                }
            )

    def _configure_fcoe(self, vport, flow_control, imports):
        if flow_control is not None and flow_control.choice == 'ieee_802_1qbb':
            pfc = flow_control.ieee_802_1qbb
            fcoe = {
                'xpath': vport['xpath'] + '/l1Config/' + vport['type'] + '/fcoe',
                'enablePFCPauseDelay': True,
                'flowControlType': Vport._FLOW_CONTROL_MAP[flow_control.choice],
                'pfcPauseDelay': pfc.pfc_delay,
                'pfcPriorityGroups': [
                    -1 if pfc.pfc_class_0 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_1 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_2 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_3 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_4 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_5 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_6 is None else pfc.pfc_class_0,
                    -1 if pfc.pfc_class_7 is None else pfc.pfc_class_0,
                ],
                'priorityGroupSize': 'priorityGroupSize-8',
                'supportDataCenterMode': True
            }
            imports.append(fcoe)

    def _connect(self):
        self._ixn_vport.find(ConnectionState='^((?!connectedLink).)*$')
        try:
            force_ownership = self._api.snappi_config.options.port_options.location_preemption
        except:
            force_ownership = False
        try:
            self._ixn_vport.ConnectPorts(force_ownership)
        except Exception as e:
            self._api.add_error(e)

    def _set_result_value(self, row, column_name, column_value, column_type = str):
        if len(self._column_names) > 0 and column_name not in self._column_names:
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
            self._set_result_value(port_row, 'link', 'up' if vport['connectionState'] == 'connectedLinkUp' else 'down')
            self._set_result_value(port_row, 'capture', 'stopped')
            port_rows[vport['name']] = port_row
        try:
            table = self._api.assistant.StatViewAssistant('Port Statistics')
            for row in table.Rows:
                port_row = port_rows[row['Port Name']]
                self._set_result_value(port_row, 'frames_tx', row['Frames Tx.'], int)
                self._set_result_value(port_row, 'frames_rx', row['Valid Frames Rx.'], int)
                self._set_result_value(port_row, 'frames_tx_rate', row['Frames Tx. Rate'], float)
                self._set_result_value(port_row, 'frames_rx_rate', row['Valid Frames Rx. Rate'], float)
                self._set_result_value(port_row, 'bytes_tx', row['Bytes Tx.'], int)
                self._set_result_value(port_row, 'bytes_rx', row['Bytes Rx.'], int)
                self._set_result_value(port_row, 'bytes_tx_rate', row['Bytes Tx. Rate'], float)
                self._set_result_value(port_row, 'bytes_rx_rate', row['Bytes Rx. Rate'], float)
                self._set_result_value(port_row, 'pfc_class_0_frames_rx', row['Rx Pause Priority Group 0 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_1_frames_rx', row['Rx Pause Priority Group 1 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_2_frames_rx', row['Rx Pause Priority Group 2 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_3_frames_rx', row['Rx Pause Priority Group 3 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_4_frames_rx', row['Rx Pause Priority Group 4 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_5_frames_rx', row['Rx Pause Priority Group 5 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_6_frames_rx', row['Rx Pause Priority Group 6 Frames'], int)
                self._set_result_value(port_row, 'pfc_class_7_frames_rx', row['Rx Pause Priority Group 7 Frames'], int)
        except:
            pass
        return port_rows.values()
