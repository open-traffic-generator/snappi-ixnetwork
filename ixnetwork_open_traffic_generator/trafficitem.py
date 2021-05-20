from time import time
from ixnetwork_open_traffic_generator.timer import Timer
from ixnetwork_open_traffic_generator.customfield import CustomField


class TrafficItem(CustomField):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    
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
    }

    _VLAN = {
        'id': 'vlan.header.vlanTag.vlanID',
        'cfi': 'vlan.header.vlanTag.cfi',
        'priority': 'vlan.header.vlanTag.vlanUserPriority',
        'protocol': 'vlan.header.protocolID'
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
    }

    _IPV6 = {
        'version' : 'ipv6.header.versionTrafficClassFlowLabel.version',
        'traffic_class' : 'ipv6.header.versionTrafficClassFlowLabel.trafficClass',
        'flow_label' : 'ipv6.header.versionTrafficClassFlowLabel.flowLabel',
        'payload_length' : 'ipv6.header.payloadLength',
        'next_header' : 'ipv6.header.nextHeader',
        'hop_limit' : 'ipv6.header.hopLimit',
        'src' : 'ipv6.header.srcIP',
        'dst' : 'ipv6.header.dstIP'
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
    }

    _UDP = {
        "src_port": "udp.header.srcPort",
        "dst_port": "udp.header.dstPort",
        "length": "udp.header.length",
        "checksum": "udp.header.checksum",
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

    def config(self):
        """Configure config.flows onto Ixnetwork.Traffic.TrafficItem
        
        CRUD
        ----
        - DELETE any TrafficItem.Name that does not exist in config.flows
        - CREATE TrafficItem for any config.flows[*].name that does not exist
        - UPDATE TrafficItem for any config.flows[*].name that exists
        """
        ixn_traffic_item = self._api._traffic_item
        self._api._remove(ixn_traffic_item, self._api.config.flows)
        if self._api.config.flows is not None:
            for flow in self._api.config.flows:
                args = {
                    'Name': flow.name,
                    'TrafficItemType': 'l2L3',
                    'TrafficType': self._get_traffic_type(flow),
                    'SrcDestMesh': 'oneToOne' if flow.tx_rx.choice == 'port' else 'manyToMany'
                }
                ixn_traffic_item.find(Name='^%s$' % flow.name,
                                      TrafficType=args['TrafficType'])
                if len(ixn_traffic_item) == 0:
                    ixn_traffic_item.add(**args)
                else:
                    self._update(ixn_traffic_item, **args)
                self._configure_endpoint(ixn_traffic_item.EndpointSet,
                                         flow.tx_rx)
                self._configure_tracking(flow, ixn_traffic_item.Tracking)
                ixn_ce = ixn_traffic_item.ConfigElement.find()
                hl_stream_count = len(ixn_traffic_item.HighLevelStream.find())
                self._configure_stack(ixn_ce, flow.packet)
                self._configure_size(ixn_ce, flow.size)
                self._configure_rate(ixn_ce, flow.rate)
                self._configure_tx_control(ixn_ce, hl_stream_count, flow.duration)
            self._configure_options()

    def _configure_tracking(self, flow, ixn_tracking):
        """Set tracking options"""
        ixn_tracking.find()
        tracking_options = ['trackingenabled0']
        if flow.tx_rx.choice == 'device':
            tracking_options.append('sourceDestPortPair0')
        if set(tracking_options) != set(ixn_tracking.TrackBy):
            ixn_tracking.update(TrackBy=tracking_options)
        
    def _configure_options(self):
        enable_min_frame_size = False
        for flow in self._api.config.flows:
            if (len(flow.packet) == 1 and flow.packet[
                    0].choice == 'pfcpause'):
                enable_min_frame_size = True
                break
        if self._api._traffic.EnableMinFrameSize != enable_min_frame_size:
            self._api._traffic.EnableMinFrameSize = enable_min_frame_size

    def _get_traffic_type(self, flow):
        if flow.tx_rx is None:
            raise ValueError('%s Flow.tx_rx property cannot be None' %
                             flow.name)
        elif flow.tx_rx.choice == 'port':
            encap = 'raw'
        else:
            encap = None
            for name in flow.tx_rx.device.tx_device_names:
                device = self._api.get_config_object(name)
                if device.choice == 'ethernet':
                    encap = 'ethernetVlan'
                elif device.choice == 'bgpv4':
                    encap = 'ipv4'
                else:
                    encap = device.choice
        return encap

    def _configure_endpoint(self, ixn_endpoint_set, endpoint):
        """Transform flow.tx_rx to /trafficItem/endpointSet
        The model allows for only one endpointSet per traffic item
        """
        args = {'Sources': [], 'Destinations': []}
        if (endpoint.choice == "port"):
            args['Sources'].append(
                self._api.get_ixn_object(
                    endpoint.port.tx_port_name).Protocols.find().href)
            if endpoint.port.rx_port_name != None:
                args['Destinations'].append(
                    self._api.get_ixn_object(
                        endpoint.port.rx_port_name).Protocols.find().href)
        else:
            for port_name in endpoint.device.tx_device_names:
                args['Sources'].append(self._api.get_ixn_href(port_name))
            for port_name in endpoint.device.rx_device_names:
                args['Destinations'].append(self._api.get_ixn_href(port_name))
        ixn_endpoint_set.find()
        if len(ixn_endpoint_set) > 1:
            ixn_endpoint_set.remove()
        if len(ixn_endpoint_set) == 0:
            ixn_endpoint_set.add(**args)
        elif ixn_endpoint_set.Sources != args[
                'Sources'] or ixn_endpoint_set.Destinations != args[
                    'Destinations'] or len(ixn_endpoint_set.parent.ConfigElement.find()) == 0:
            self._update(ixn_endpoint_set, **args)

    def _update(self, ixn_object, **kwargs):
        from ixnetwork_restpy.base import Base
        update = False
        for name, value in kwargs.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(
                    value[0], Base):
                value = [item.href for item in value]
            elif isinstance(value, Base):
                value = value.href
            if getattr(ixn_object, name) != value:
                update = True
        if update is True:
            ixn_object.update(**kwargs)

    def _configure_stack(self, ixn_stream, headers):
        """Transform flow.packets[0..n] to /traffic/trafficItem/configElement/stack
        The len of the headers list is the definitive list which means add/remove
        any stack items so that the stack list matches the headers list.
        If the headers list is empty then use the traffic generator default stack.
        """
        headers = self.adjust_header(headers)
        ixn_stack = ixn_stream.Stack.find()
        for i in range(0, len(headers)):
            header = headers[i]
            if len(ixn_stack) <= i:
                stack = self._add_stack(ixn_stream, stack, header)
            else:
                stack_type_id = ixn_stack[i].StackTypeId
                if stack_type_id in self._STACK_IGNORE:
                    stack = self._add_stack(ixn_stream, stack, header)
                elif stack_type_id not in TrafficItem._TYPE_TO_HEADER:
                    stack = self._add_stack(ixn_stream, ixn_stack[i], header)
                elif TrafficItem._TYPE_TO_HEADER[
                        stack_type_id] != header.choice:
                    stack = self._add_stack(ixn_stream, ixn_stack[i], header)
                else:
                    stack = ixn_stack[i]
            self._configure_field(stack.Field, header)

        # scan and compare new stack to overcome IxNetwork stack serialization
        # then remove additional stack
        if len(headers) == 0:
            return
        stacks_to_remove = []
        ixn_stack = ixn_stream.Stack.find()
        header_index = 0
        for i in range(0, len(ixn_stack)):
            stack_type_id = ixn_stack[i].StackTypeId
            if stack_type_id in self._STACK_IGNORE:
                continue
            if len(headers) <= header_index:
                stacks_to_remove.append(ixn_stack[i])
                continue
            if TrafficItem._TYPE_TO_HEADER[
                    stack_type_id] != headers[header_index].choice:
                stacks_to_remove.append(ixn_stack[i])
            else:
                header_index += 1
        for stack in stacks_to_remove[::-1]:
            stack.Remove()

    def _add_stack(self, ixn_stream, ixn_stack, header):
        type_id = '^%s$' % TrafficItem._HEADER_TO_TYPE[header.choice]
        template = self._api._traffic.ProtocolTemplate.find(
            StackTypeId=type_id)
        stack_href = ixn_stack.AppendProtocol(template)
        return ixn_stream.Stack.read(stack_href)

    def _configure_field(self, ixn_field, header, field_choice=False):
        """Transform flow.packets[0..n].header.choice to /traffic/trafficItem/configElement/stack/field
        """
        field_map = getattr(self, '_%s' % header.choice.upper())
        packet = getattr(header, header.choice)
        if isinstance(field_map, dict) is False:
            method = getattr(self, field_map)
            method(ixn_field, packet)
            return

        for packet_field_name in dir(packet):
            if packet_field_name in field_map:
                pattern = getattr(packet, packet_field_name)
                field_type_id = field_map[packet_field_name]
                self._configure_pattern(ixn_field, field_type_id, pattern,
                                        field_choice)

    def _configure_pattern(self,
                           ixn_field,
                           field_type_id,
                           pattern,
                           field_choice=False):
        
        custom_field = getattr(self, field_type_id, None)
        if custom_field is not None:
            if pattern is not None:
                custom_field(ixn_field, pattern)
            return

        ixn_field = ixn_field.find(FieldTypeId=field_type_id)
        self._set_default(ixn_field, field_choice)
        
        if pattern is None:
            return
        
        if pattern.choice == 'fixed':
            ixn_field.update(Auto=False,
                             ActiveFieldChoice=field_choice,
                             ValueType='singleValue',
                             SingleValue=pattern.fixed)
        elif pattern.choice == 'list':
            ixn_field.update(Auto=False,
                             ActiveFieldChoice=field_choice,
                             ValueType='valueList',
                             ValueList=pattern.list)
        elif pattern.choice == 'counter':
            value_type = 'increment' if pattern.counter.up is True else 'decrement'
            try:
                ixn_field.update(Auto=False,
                                ValueType=value_type,
                                ActiveFieldChoice=field_choice,
                                StartValue=pattern.counter.start,
                                StepValue=pattern.counter.step,
                                CountValue=pattern.counter.count)
            except Exception as e:
                print(e)
        elif pattern.choice == 'random':
            ixn_field.update(Auto=False,
                             ActiveFieldChoice=field_choice,
                             ValueType='repeatableRandomRange',
                             MinValue=pattern.random.min,
                             MaxValue=pattern.random.max,
                             StepValue=pattern.random.step,
                             Seed=pattern.random.seed,
                             CountValue=pattern.random.count)
        else:
            # TBD: add to set_config errors - invalid pattern specified
            pass

        if pattern.ingress_result_name is not None:
            ixn_field.TrackingEnabled = True
            self._api.ixn_objects[pattern.ingress_result_name] = ixn_field.href

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

    def _configure_size(self, ixn_stream, size):
        """ Transform frameSize flows.size to /traffic/trafficItem[*]/configElement[*]/frameSize
        """
        if size is None:
            return
        ixn_frame_size = ixn_stream.FrameSize
        args = {}
        if size.choice == 'fixed':
            args['Type'] = "fixed"
            args['FixedSize'] = size.fixed
        elif size.choice == 'increment':
            args['Type'] = "incrment"
            args['IncrementFrom'] = size.increment.start
            args['IncrementTo'] = size.increment.end
            args['IncrementStep'] = size.increment.step
        elif size.choice == 'random':
            args['Type'] = "random"
            args['RandomMin'] = size.random.min
            args['RandomMax'] = size.random.max
        else:
            print('Warning - We need to implement this %s choice' %
                  size.choice)
        self._update(ixn_frame_size, **args)

    def _configure_rate(self, ixn_stream, rate):
        """ Transform frameRate flows.rate to /traffic/trafficItem[*]/configElement[*]/frameRate
        """
        if rate is None:
            return
        ixn_frame_rate = ixn_stream.FrameRate
        args = {}
        if rate.unit == 'line':
            args['Type'] = 'percentLineRate'
        elif rate.unit == 'pps':
            args['Type'] = 'framesPerSecond'
        else:
            args['Type'] = 'bitsPerSecond'
            args['BitRateUnitsType'] = TrafficItem._BIT_RATE_UNITS_TYPE[
                rate.unit]
        args['Rate'] = rate.value
        self._update(ixn_frame_rate, **args)

    def _configure_tx_control(self, ixn_stream, hl_stream_count, duration):
        """Transform duration flows.duration to /traffic/trafficItem[*]/configElement[*]/TransmissionControl
        """
        if duration is None:
            return
        ixn_tx_control = ixn_stream.TransmissionControl
        args = {}
        if duration.choice == 'continuous':
            args['Type'] = 'continuous'
            args['MinGapBytes'] = duration.continuous.gap
            args['StartDelay'] = duration.continuous.delay
            args['StartDelayUnits'] = duration.continuous.delay_unit
        elif duration.choice == 'packets':
            args['Type'] = 'fixedFrameCount'
            args['FrameCount'] = duration.packets.packets / hl_stream_count
            args['MinGapBytes'] = duration.packets.gap
            args['StartDelay'] = duration.packets.delay
            args['StartDelayUnits'] = duration.packets.delay_unit
        elif duration.choice == 'seconds':
            args['Type'] = 'fixedDuration'
            args['Duration'] = duration.seconds.seconds
            args['MinGapBytes'] = duration.seconds.gap
            args['StartDelay'] = duration.seconds.delay
            args['StartDelayUnits'] = duration.seconds.delay_unit
        elif duration.choice == 'burst':
            if duration.burst.bursts is not None \
                    and int(duration.burst.bursts) > 0:
                args['Type'] = 'burstFixedDuration'
                args['RepeatBurst'] = duration.burst.bursts
            else:
                args['Type'] = 'custom'
            args['BurstPacketCount'] = duration.burst.packets
            args['MinGapBytes'] = duration.burst.gap
            args['EnableInterBurstGap'] = True
            args['InterBurstGap'] = duration.burst.inter_burst_gap
            args['InterBurstGapUnits'] = duration.burst.inter_burst_gap_unit
        self._update(ixn_tx_control, **args)

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
            if len(self._api.config.lags) > 0:
                self._api._ixnetwork.Lag.find().Start()
            if len(self._api._topology.find()) > 0:
                with Timer(self._api, 'Devices start'):
                    self._api._ixnetwork.StartAllProtocols('sync')
                    self._api.check_protocol_statistics()
            if len(self._api._traffic_item.find()) == 0:
                return
            self._api._traffic_item.find(State='^unapplied$')
            if len(self._api._traffic_item) > 0:
                with Timer(self._api, 'Flows generate/apply'):
                    self._generate_flows_and_apply()
            self._api._traffic_item.find(State='^started$')
            if len(self._api._traffic_item) == 0:
                with Timer(self._api, 'Flows clear statistics'):
                    self._api._ixnetwork.ClearStats(
                        ['waitForPortStatsRefresh', 'waitForTrafficStatsRefresh'])
            self._api._start_capture()
        self._api._traffic_item.find(Name=regex)
        if len(self._api._traffic_item) > 0:
            if request.state == 'start':
                self._api._traffic_item.find(Name=regex, Suspend=True,
                                             State='^started$')
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

    def _generate_flows_and_apply(self):
        url = '%s/traffic/trafficItem' % self._api._ixnetwork.href
        res = self._api._request('GET', url)
        hrefs = [
            j['links'][-1]['href']
            for j in res if j.get('links') is not None and len(j['links']) > 0
        ]
        url = '{}/traffic/trafficItem/operations/generate'.format(
            self._api._ixnetwork.href
        )
        payload = {
            'arg1': hrefs
        }
        self._api._request('POST', url=url, payload=payload)
        self._api._traffic.Apply()
        return

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
        if request.column_names is None:
            self._column_names = []
        else:
            self._column_names = request.column_names
        filter = {'property': 'name', 'regex': '.*'}
        flow_names = [flow.name for flow in self._api._config.flows]
        if request is not None and request.flow_names is not None and len(
                request.flow_names) > 0:
            flow_names = request.flow_names
        if len(flow_names) == 1:
            filter['regex'] = '^%s$' % \
                self._convert_string_to_regex(flow_names)[0]
        elif len(flow_names) > 1:
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
