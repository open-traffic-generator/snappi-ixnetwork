import json

from pkg_resources import fixup_namespace_packages
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.customfield import CustomField


class TrafficItem(CustomField):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (Api): instance of the ixnetworkapi class
    
    """
    _RESULT_COLUMNS = [
        ('frames_tx', 'Tx Frames', int),
        ('frames_rx', 'Rx Frames', int),
        ('frames_tx_rate', 'Tx Frame Rate', float),
        ('frames_rx_rate', 'Rx Frame Rate', float),
        ('bytes_tx', 'Tx Bytes', int),
        ('bytes_rx', 'Rx Bytes', int),
        ('loss', 'Loss %', float),
        # TODO: these are not defined in API spec
        ('bytes_tx_rate', 'Tx Rate (Bps)', float),
        ('bytes_rx_rate', 'Rx Rate (Bps)', float),
    ]

    _STACK_IGNORE = ['ethernet.fcs', 'pfcPause.fcs']

    _TYPE_TO_HEADER = {
        'ethernet': 'ethernet',
        'pfcPause': 'pfcpause',
        'vlan': 'vlan',
        'ipv4': 'ipv4',
        'ipv6': 'ipv6',
        'tcp': 'tcp',
        'udp': 'udp',
        'gtpu': 'gtpv1',
        'gTPuOptionalFields': 'gtpv1option',
        'custom': 'custom'
    }

    _HEADER_TO_TYPE = {
        'ethernet': 'ethernet',
        'pfcpause': 'pfcPause',
        'vlan': 'vlan',
        'ipv4': 'ipv4',
        'ipv6': 'ipv6',
        'tcp': 'tcp',
        'udp': 'udp',
        'gtpv1': 'gtpu',
        'gtpv1option': 'gTPuOptionalFields',
        'custom': 'custom'
    }

    _BIT_RATE_UNITS_TYPE = {
        'bps': 'bitsPerSec',
        'kbps': 'kbitsPerSec',
        'mbps': 'mbitsPerSec',
        'gbps': 'mbytesPerSec'
    }

    _PFCPAUSE = {
        'dst': 'pfcPause.header.header.dstAddress',
        'src': 'pfcPause.header.header.srcAddress',
        'ether_type': 'pfcPause.header.header.ethertype',
        'control_op_code': 'pfcPause.header.macControl.controlOpcode',
        'class_enable_vector':
        'pfcPause.header.macControl.priorityEnableVector',
        'pause_class_0': 'pfcPause.header.macControl.pauseQuanta.pfcQueue0',
        'pause_class_1': 'pfcPause.header.macControl.pauseQuanta.pfcQueue1',
        'pause_class_2': 'pfcPause.header.macControl.pauseQuanta.pfcQueue2',
        'pause_class_3': 'pfcPause.header.macControl.pauseQuanta.pfcQueue3',
        'pause_class_4': 'pfcPause.header.macControl.pauseQuanta.pfcQueue4',
        'pause_class_5': 'pfcPause.header.macControl.pauseQuanta.pfcQueue5',
        'pause_class_6': 'pfcPause.header.macControl.pauseQuanta.pfcQueue6',
        'pause_class_7': 'pfcPause.header.macControl.pauseQuanta.pfcQueue7',
    }

    _ETHERNET = {
        'dst': 'ethernet.header.destinationAddress',
        'src': 'ethernet.header.sourceAddress',
        'ether_type': 'ethernet.header.etherType',
        'pfc_queue': 'ethernet.header.pfcQueue',
        'order': ['dst', 'src', 'ether_type', 'pfc_queue']
    }

    _VLAN = {
        'id': 'vlan.header.vlanTag.vlanID',
        'cfi': 'vlan.header.vlanTag.cfi',
        'priority': 'vlan.header.vlanTag.vlanUserPriority',
        'protocol': 'vlan.header.protocolID',
        'order': ['id', 'cfi', 'priority', 'protocol']
    }

    _IPV4 = {
        'version': 'ipv4.header.version',
        'header_length': 'ipv4.header.headerLength',
        'priority': '_ipv4_priority',
        'total_length': 'ipv4.header.totalLength',
        'identification': 'ipv4.header.identification',
        'reserved': 'ipv4.header.flags.reserved',
        'dont_fragment': 'ipv4.header.flags.fragment',
        'more_fragments': 'ipv4.header.flags.lastFragment',
        'fragment_offset': 'ipv4.header.fragmentOffset',
        'time_to_live': 'ipv4.header.ttl',
        'protocol': 'ipv4.header.protocol',
        'header_checksum': 'ipv4.header.checksum',
        'src': 'ipv4.header.srcIp',
        'dst': 'ipv4.header.dstIp',
        'order': ['version', 'header_length']
    }

    _IPV6 = {
        'version' : 'ipv6.header.versionTrafficClassFlowLabel.version',
        'traffic_class' : 'ipv6.header.versionTrafficClassFlowLabel.trafficClass',
        'flow_label' : 'ipv6.header.versionTrafficClassFlowLabel.flowLabel',
        'payload_length' : 'ipv6.header.payloadLength',
        'next_header' : 'ipv6.header.nextHeader',
        'hop_limit' : 'ipv6.header.hopLimit',
        'src' : 'ipv6.header.srcIP',
        'dst' : 'ipv6.header.dstIP',
        'order': ['version', 'traffic_class', 'flow_label', 'payload_length']
    }
    
    _TOS = {
        "precedence": "ipv4.header.priority.tos.precedence",
        "delay": "ipv4.header.priority.tos.delay",
        "throughput": "ipv4.header.priority.tos.throughput",
        "reliability": "ipv4.header.priority.tos.reliability",
        "monetary": "ipv4.header.priority.tos.monetary",
        "unused": "ipv4.header.priority.tos.unused"
    }

    _TCP = {
        "src_port": "tcp.header.srcPort",
        "dst_port": "tcp.header.dstPort",
        "ecn_ns": "tcp.header.ecn.nsBit",
        "ecn_cwr": "tcp.header.ecn.cwrBit",
        "ecn_echo": "tcp.header.ecn.ecnEchoBit",
        "ctl_urg": "tcp.header.controlBits.urgBit",
        "ctl_ack": "tcp.header.controlBits.ackBit",
        "ctl_psh": "tcp.header.controlBits.pshBit",
        "ctl_rst": "tcp.header.controlBits.rstBit",
        "ctl_syn": "tcp.header.controlBits.synBit",
        "ctl_fin": "tcp.header.controlBits.finBit",
        "order": ["src_port", "dst_port"]
    }

    _UDP = {
        "src_port": "udp.header.srcPort",
        "dst_port": "udp.header.dstPort",
        "length": "udp.header.length",
        "checksum": "udp.header.checksum",
        "order": ["src_port", "dst_port"]
    }
    
    _GTPV1 = {
        "version" : "gtpu.header.version",
        "protocol_type" : "gtpu.header.pt",
        "reserved" : "gtpu.header.reserved",
        "e_flag" : "gtpu.header.e",
        "s_flag" : "gtpu.header.s",
        "pn_flag" : "gtpu.header.n",
        "message_type" : "tpu.header.type",
        "message_length" : "gtpu.header.totalLength",
        "teid" : "gtpu.header.teid"
    }

    _GTPV1OPTION = {
        "squence_number" : "gTPuOptionalFields.header.sequenceNumber",
        "n_pdu_number" : "gTPuOptionalFields.header.npduNumber",
        "next_extension_header_type" : "gTPuOptionalFields.header.nextExtHdrField"
    }
    
    _CUSTOM = '_custom_headers'

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi

    def _export_config(self):
        href = '%sresourceManager' % self._api._ixnetwork.href
        url = '%s/operations/exportconfig' % href
        payload = {
            'arg1': href,
            'arg2': [
                "/traffic/trafficItem/descendant-or-self::*"
            ],
            'arg3': True,
            'arg4': 'json'
        }
        res = self._api._request('POST', url=url, payload=payload)
        return json.loads(res['result'])

    def _importconfig(self, imports):
        imports['xpath'] = '/'
        href = '%sresourceManager' % self._api._ixnetwork.href
        url = '%s/operations/importconfig' % href
        import json
        payload = {
            'arg1': href,
            'arg2': json.dumps(imports),
            'arg3': False
        }
        res = self._api._request('POST', url=url, payload=payload)
        return res

    def config(self):
        """Configure config.flows onto Ixnetwork.Traffic.TrafficItem

        CRUD
        ----
        - DELETE any TrafficItem.Name that does not exist in config.flows
        - CREATE TrafficItem for any config.flows[*].name that does not exist
        - UPDATE TrafficItem for any config.flows[*].name that exists
        """
        with Timer(self._api, "traffic config export"):
            ixn_traffic_item = self._export_config()
        if ixn_traffic_item.get('traffic') is None:
            return
        ixn_traffic_item = ixn_traffic_item['traffic'].get('trafficItem')
        if ixn_traffic_item is None:
            return
        tr_json = {
            'traffic': {
                'xpath': '/traffic',
                'trafficItem': []
            }
        }

        for i, flow in enumerate(self._api.stateful_config.flows):
            with Timer(self._api, "json processing for traffic"):
                tr_item = {'xpath': ixn_traffic_item[i]['xpath']}
                tr_item.update(
                    self._configure_tracking(ixn_traffic_item[i])
                )
                ce_xpaths = [
                    {'xpath': ce['xpath']}
                    for ce in ixn_traffic_item[i]['configElement']
                ]
                tr_item['configElement'] = ce_xpaths
                self._configure_size(tr_item['configElement'], flow.size)
                self._configure_rate(tr_item['configElement'], flow.rate)
                hl_stream_count = len(ixn_traffic_item[i]['highLevelStream'])
                self._configure_tx_control(
                    tr_item['configElement'], hl_stream_count, flow.duration
                )
                tr_type = ixn_traffic_item[i]['trafficType']
                for i, ce in enumerate(ixn_traffic_item[i]['configElement']):
                    stack = self._configure_packet(
                        tr_type, ce['stack'], flow.packet
                    )
                    tr_item['configElement'][i]['stack'] = stack

                tr_json['traffic']['trafficItem'].append(tr_item)
        with Timer(self._api, "Apply traffic json"):
            self._importconfig(tr_json)

        self._configure_options()

    def _configure_tracking(self, tr_item_json):
        """Set tracking options"""
        xpath = tr_item_json['xpath']
        if tr_item_json.get('trafficType') == 'raw':
            trackBy = ["trackingenabled0"]
        else:
            trackBy = ["trackingenabled0", "sourceDestPortPair0"]
        tracking = [{
            'xpath': '%s/tracking' % xpath,
            'trackBy': trackBy
        }]
        return {'tracking': tracking}

    def _configure_options(self):
        enable_min_frame_size = False
        for flow in self._api.snappi_config.flows:
            if (len(flow.packet) == 1 and flow.packet[
                    0].parent.choice == 'pfcpause'):
                enable_min_frame_size = True
                break
        if self._api._traffic.EnableMinFrameSize != enable_min_frame_size:
            self._api._traffic.EnableMinFrameSize = enable_min_frame_size

    def _configure_packet(self, tr_type, ixn_stack, snappi_packet):
        if len(snappi_packet) == 0:
            return
        stacks = [{'xpath': s['xpath']} for s in ixn_stack]
        stack_names = [
            s['xpath'].split(' = ')[-1].strip("']").split("-")[0]
            for s in ixn_stack
        ]
        tr_types_block = ['ethernetVlan', 'ipv4', 'ipv6', 'raw']
        if tr_type in tr_types_block:
            for i, header in enumerate(snappi_packet):
                if header._choice not in stack_names:
                    ce_path = stacks[0]['xpath'].split(' = ')[0]
                    index =\
                        stacks[-1]['xpath'].split(' = ')[
                            -1].strip("']").split("-")[-1]
                    index = '%s-%s' % (header._choice, index)
                    xpath = '%s = \'%s\']' % (ce_path, index)
                    self._append_header(header, xpath, stacks)
                    continue
                ind = stack_names.index(header._choice)
                ixn_fields = ixn_stack[ind]['field']
                fields = self._configure_stack_fields(ixn_fields, header)
                stacks[ind]['field'] = fields
        return stacks

    def _append_header(self, snappi_header, xpath, stacks, add_trailer=True):
        field_map = getattr(self, '_%s' % snappi_header._choice.upper())
        stack_name = self._TYPE_TO_HEADER.get(snappi_header._choice)
        if stack_name is None:
            raise NotImplementedError(
                "%s stack is not implemented" % snappi_header._choice
            )
        header = {'xpath': xpath}
        if field_map.get('order') is not None:
            fields = self._generate_fields(field_map, xpath)
            header['field'] = self._configure_stack_fields(
                fields, snappi_header
            )
        index = len(stacks) if len(stacks) <= 1 else -2
        stacks.insert(index, header)
        if index == -2 and add_trailer:
            fcs = stacks[-1]['xpath']
            ce, n = fcs.split(' = ')
            n = n.split('-')[0]
            fcs = '%s = \'%s-%s\']' % (ce, n, len(stacks))
            stacks[-1]['xpath'] = fcs
        return header

    def _generate_fields(self, field_map, xpath):
        fields = []
        for i, f in enumerate(field_map['order']):
            fmap = '%s-%s' % (field_map[f], i + 1)
            fields.append({
                'xpath': '%s/field[@alias = \'%s\']' % (xpath, fmap)
            })
        return fields

    def _configure_stack_fields(self, ixn_fields, snappi_header):
        if len(snappi_header._properties) == 0:
            return
        fields = [{'xpath': f['xpath']} for f in ixn_fields]
        field_names = [
            f['xpath'].split(' = ')[-1].strip("']").split("-")[0]
            for f in ixn_fields
        ]
        field_map = getattr(self, '_%s' % snappi_header._choice.upper())
        for field in snappi_header._properties:
            try:
                ind = field_names.index(field_map[field])
            except Exception:
                continue
            field = getattr(snappi_header, field)
            self._config_field_pattern(field, fields[ind])
        return fields

    def _config_field_pattern(self, snappi_field, field_json):
        if snappi_field.choice is None:
            return
        ixn_patt = {
            'value': 'singleValue', 'values': 'valueList',
            'increment': 'increment', 'decrement': 'decrement',
            'random': 'repeatableRandomRange'
        }

        field_json['valueType'] = ixn_patt[snappi_field.choice]
        if snappi_field.choice in ['value', 'values']:
            field_json[ixn_patt[snappi_field.choice]] =\
                getattr(snappi_field, snappi_field.choice)
        if snappi_field.choice in ['increment', 'decrement']:
            obj = getattr(snappi_field, snappi_field.choice)
            field_json['startValue'] = obj.start
            field_json['stepValue'] = obj.step
            field_json['countValue'] = obj.count
        field_json['activeFieldChoice'] = False
        field_json['auto'] = False
        return

    def _set_default(self, ixn_field, field_choice):
        """We are setting all the field to default. Otherwise test is keeping the same value from previous run."""
        if ixn_field.ReadOnly:
            return
        
        if ixn_field.SupportsAuto:
            if ixn_field.Auto is not True:
                ixn_field.Auto = True
        else:
            ixn_field.update(Auto=False,
                             ActiveFieldChoice=field_choice,
                             ValueType='singleValue',
                             SingleValue=ixn_field.DefaultValue)

    def _configure_size(self, ce_dict, size):
        """ Transform frameSize flows.size to /traffic/trafficItem[*]/configElement[*]/frameSize
        """
        if size.choice is None:
            return
        for ce in ce_dict:
            ce['frameSize'] = {
                'xpath': '%s/frameSize' % ce['xpath']
            }
            # ixn_frame_size = ixn_stream.FrameSize
            # args = {}
            if size.choice == 'fixed':
                ce['frameSize']['type'] = "fixed"
                ce['frameSize']['fixedSize'] = size.fixed
            elif size.choice == 'increment':
                ce['frameSize']['type'] = "increment"
                ce['frameSize']['incrementFrom'] = size.increment.start
                ce['frameSize']['incrementTo'] = size.increment.end
                ce['frameSize']['incrementStep'] = size.increment.step
            elif size.choice == 'random':
                ce['frameSize']['type'] = "random"
                ce['frameSize']['randomMin'] = size.random.min
                ce['frameSize']['randomMax'] = size.random.max
            else:
                print('Warning - We need to implement this %s choice' %
                    size.choice)
        return

    def _configure_rate(self, ce_dict, rate):
        """ Transform frameRate flows.rate to /traffic/trafficItem[*]/configElement[*]/frameRate
        """
        if rate.choice is None:
            return
        # ixn_frame_rate = ixn_stream.FrameRate
        # args = {}
        for ce in ce_dict:
            ce['frameRate'] = {
                'xpath': '%s/frameRate' % ce['xpath']
            }
            value = None
            if rate.choice == 'percentage':
                ce['frameRate']['type'] = 'percentLineRate'
                value = rate.percentage
            elif rate.choice == 'pps':
                ce['frameRate']['type'] = 'framesPerSecond'
                value = rate.pps
            else:
                ce['frameRate']['type'] = 'bitsPerSecond'
                ce['frameRate']['bitRateUnitsType'] = TrafficItem._BIT_RATE_UNITS_TYPE[
                    rate.choice]
                value = getattr(rate, rate.choice)
            ce['frameRate']['Rate'] = value
        return

    def _configure_tx_control(self, ce_dict, hl_stream_count, duration):
        """Transform duration flows.duration to /traffic/trafficItem[*]/configElement[*]/TransmissionControl
        """
        if duration.choice is None:
            return
        # ixn_tx_control = ixn_stream.TransmissionControl
        # args = {}
        for ce in ce_dict:
            ce['transmissionControl'] = {
                'xpath': '%s/transmissionControl' % ce['xpath']
            }
            if duration.choice == 'continuous':
                ce['transmissionControl']['type'] = 'continuous'
                ce['transmissionControl']['minGapBytes'] =\
                    duration.continuous.gap
                ce['transmissionControl']['startDelay'] =\
                    duration.continuous.delay
                ce['transmissionControl']['startDelayUnits'] =\
                    duration.continuous.delay_unit
            elif duration.choice == 'fixed_packets':
                ce['transmissionControl']['type'] =\
                    'fixedFrameCount'
                ce['transmissionControl']['frameCount'] =\
                    duration.fixed_packets.packets / hl_stream_count
                ce['transmissionControl']['minGapBytes'] =\
                    duration.fixed_packets.gap
                ce['transmissionControl']['startDelay'] =\
                    duration.fixed_packets.delay
                ce['transmissionControl']['startDelayUnits'] =\
                    duration.fixed_packets.delay_unit
            elif duration.choice == 'fixed_seconds':
                ce['transmissionControl']['type'] = 'fixedDuration'
                ce['transmissionControl']['duration'] =\
                    duration.fixed_seconds.seconds
                ce['transmissionControl']['minGapBytes'] =\
                    duration.fixed_seconds.gap
                ce['transmissionControl']['startDelay'] =\
                    duration.fixed_seconds.delay
                ce['transmissionControl']['startDelayUnits'] =\
                    duration.fixed_seconds.delay_unit
            elif duration.choice == 'burst':
                ce['transmissionControl']['type'] = 'custom'
                ce['transmissionControl']['burstPacketCount'] =\
                    duration.burst.packets
                ce['transmissionControl']['minGapBytes'] =\
                    duration.burst.gap
                ce['transmissionControl']['enableInterBurstGap'] =\
                    True if duration.burst.gap > 0 else False
                ce['transmissionControl']['interBurstGap'] =\
                    duration.burst.inter_burst_gap
                ce['transmissionControl']['interBurstGapUnits'] =\
                    duration.burst.inter_burst_gap_unit
        return

    def _convert_string_to_regex(self, names):
        ret_list = []
        for n in names:
            ret_list.append(
                n.replace('(', '\\(').replace(')', '\\)')
                    .replace('[', '\\[').replace(']', '\\]')
                    .replace('.', '\\.').replace('*', '\\*')
                    .replace('+', '\\+').replace('?', '\\?')
                    .replace('{', '\\{').replace('}', '\\}')
            )
        return ret_list

    def transmit(self, request):
        """Set flow transmit
        1) If start then start any device protocols that are traffic dependent
        2) If start then generate and apply traffic
        3) Execute requested transmit action (start|stop|pause|resume)
        """
        regex = ''
        flow_names = [flow.name for flow in self._api._config.flows]
        if request and request.flow_names:
            flow_names = request.flow_names
        if len(flow_names) == 1:
            regex = '^%s$' % self._convert_string_to_regex(flow_names)[0]
        elif len(flow_names) > 1:
            regex = '^(%s)$' % '|'.join(
                self._convert_string_to_regex(flow_names)
            )

        if request.state == 'start':
            if len(self._api._topology.find()) > 0:
                with Timer(self._api, 'Devices start'):
                    self._api._ixnetwork.StartAllProtocols('sync')
                    self._api.check_protocol_statistics()
            if len(self._api._traffic_item.find()) == 0:
                return
            self._api._traffic_item.find(State='^unapplied$')
            if len(self._api._traffic_item) > 0:
                with Timer(self._api, 'Flows generate/apply'):
                    self._api._traffic_item.Generate()
                    self._api._traffic.Apply()
            self._api._traffic_item.find(State='^started$')
            if len(self._api._traffic_item) == 0:
                with Timer(self._api, 'Flows clear statistics'):
                    self._api._ixnetwork.ClearStats(
                        ['waitForPortStatsRefresh', 'waitForTrafficStatsRefresh'])
            self._api.capture._start_capture()
        self._api._traffic_item.find(Name=regex)
        if len(self._api._traffic_item) > 0:
            if request.state == 'start':
                self._api._traffic_item.find(Name=regex, State='^started$')
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, 'Flows resume'):
                        self._api._traffic_item.PauseStatelessTraffic(False)
                self._api._traffic_item.find(Name=regex, State='^stopped$')
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, 'Flows start'):
                        self._api._traffic_item.StartStatelessTrafficBlocking()
            elif request.state == 'stop':
                self._api._traffic_item.find(Name=regex, State='^started$')
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, 'Flows stop'):
                        self._api._traffic_item.StopStatelessTrafficBlocking()
            elif request.state == 'pause':
                self._api._traffic_item.find(Name=regex, State='^started$')
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, 'Flows pause'):
                        self._api._traffic_item.PauseStatelessTraffic(True)
        if request.state == 'stop':
            if len(self._api._topology.find()) > 0:
                with Timer(self._api, 'Devices stop'):
                    self._api._ixnetwork.StopAllProtocols('sync')

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

    def _get_state(self, state):
        """IxNetwork traffic item states
            error, locked, started, 
            startedWaitingForStats, startedWaitingForStreams, stopped, 
            stoppedWaitingForStats, txStopWatchExpected, unapplied
        """
        started_states = [
            'txStopWatchExpected', 'locked', 'started',
            'startedWaitingForStats', 'startedWaitingForStreams',
            'stoppedWaitingForStats'
        ]
        if state in started_states:
            return 'started'
        else:
            return 'stopped'

    def results(self, request):
        """Return flow results
        """
        # setup parameters
        self._column_names = request._properties.get('column_names')
        if self._column_names is None:
            self._column_names = []
        elif not isinstance(self._column_names, list):
            msg = "Invalid format of column_names passed {},\
                    expected list".format(self._column_names)
            raise Exception(msg)

        flow_names = request._properties.get('flow_names')
        if flow_names is None or len(flow_names) == 0:
            flow_names = [flow.name for flow in self._api._config.flows]
        elif not isinstance(flow_names, list):
            msg = "Invalid format of flow_names passed {},\
                    expected list".format(flow_names)
            raise Exception(msg)

        filter = {'property': 'name', 'regex': '.*'}
        filter['regex'] = '^(%s)$' % '|'.join(
            self._convert_string_to_regex(flow_names)
        )

        # initialize result values
        flow_rows = {}
        for traffic_item in self._api.select_traffic_items(
                traffic_item_filters=[filter]).values():
            for stream in traffic_item['highLevelStream']:
                for rx_port_name in stream['rxPortNames']:
                    flow_row = {}
                    self._set_result_value(flow_row, 'name', traffic_item['name'])
                    self._set_result_value(flow_row, 'transmit', self._get_state(traffic_item['state']))
                    self._set_result_value(flow_row, 'port_tx', stream['txPortName'])
                    self._set_result_value(flow_row, 'port_rx', rx_port_name)
                    # init all columns with corresponding zero-values so that
                    # the underlying dictionary contains all requested columns
                    # in an event of unwanted exceptions
                    for external_name, _, external_type in self._RESULT_COLUMNS:
                        self._set_result_value(
                            flow_row, external_name, 0, external_type
                        )
                    flow_rows[traffic_item['name'] + stream['txPortName'] + rx_port_name] = flow_row

        # resolve result values
        table = self._api.assistant.StatViewAssistant(
            'Flow Statistics')
        for row in table.Rows:
            if len(flow_names) > 0 and row['Traffic Item'] not in flow_names:
                continue
            if row['Traffic Item'] + row['Tx Port'] + row['Rx Port'] in flow_rows:
                flow_row = flow_rows[row['Traffic Item'] + row['Tx Port'] + row['Rx Port']]
                if float(row['Tx Frame Rate']) > 0 or int(row['Tx Frames']) == 0:
                    flow_row['transmit'] = 'started'
                else:
                    flow_row['transmit'] = 'stopped'
                for external_name, internal_name, external_type in self._RESULT_COLUMNS:
                    # keep plugging values for next columns even if the
                    # current one raises exception
                    try:
                        self._set_result_value(
                            flow_row, external_name, row[internal_name],
                            external_type
                        )
                    except Exception:
                        # TODO print a warning maybe ?
                        pass

        return list(flow_rows.values())
