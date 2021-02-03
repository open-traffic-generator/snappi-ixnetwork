from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.customfield import CustomField
import snappi


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
        self._api._remove(ixn_traffic_item, self._api.snappi_config.flows)
        if len(self._api.snappi_config.flows) > 0:
            for flow in self._api.snappi_config.flows:
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
        for flow in self._api.snappi_config.flows:
            if (len(flow.packet) == 1 and flow.packet[
                    0].parent.choice == 'pfcpause'):
                enable_min_frame_size = True
                break
        if self._api._traffic.EnableMinFrameSize != enable_min_frame_size:
            self._api._traffic.EnableMinFrameSize = enable_min_frame_size

    def _get_traffic_type(self, flow):
        if flow.tx_rx.choice is None:
            raise ValueError('%s Flow.tx_rx property cannot be None' %
                             flow.name)
        elif flow.tx_rx.choice == 'port':
            encap = 'raw'
        else:
            encap = None
            for name in flow.tx_rx.device.tx_names:
                device = self._api.get_config_object(name)
                if device.__class__ \
                        is snappi.DeviceBgpv4RouteRange:
                    encap = 'ipv4'
                else:
                    encap = self._api.get_device_encap(name)
        return encap

    def _configure_endpoint(self, ixn_endpoint_set, endpoint):
        """Transform flow.tx_rx to /trafficItem/endpointSet
        The model allows for only one endpointSet per traffic item
        """
        args = {'Sources': [], 'Destinations': []}
        if (endpoint.choice == "port"):
            args['Sources'].append(
                self._api.get_ixn_object(
                    endpoint.port.tx_name).Protocols.find().href)
            if endpoint.port.rx_name != None:
                args['Destinations'].append(
                    self._api.get_ixn_object(
                        endpoint.port.rx_name).Protocols.find().href)
        else:
            for device_name in endpoint.device.tx_names:
                args['Sources'].append(self._api.get_ixn_href(device_name))
            for device_name in endpoint.device.rx_names:
                args['Destinations'].append(self._api.get_ixn_href(device_name))
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
            if pattern.choice is not None:
                custom_field(ixn_field, pattern)
            return
    
        ixn_field = ixn_field.find(FieldTypeId=field_type_id)
        self._set_default(ixn_field, field_choice)
    
        if pattern.choice is None:
            return
    
        if pattern.choice == 'value':
            ixn_field.update(Auto=False,
                             ActiveFieldChoice=field_choice,
                             ValueType='singleValue',
                             SingleValue=pattern.value)
        elif pattern.choice == 'values':
            ixn_field.update(Auto=False,
                             ActiveFieldChoice=field_choice,
                             ValueType='valueList',
                             ValueList=pattern.values)
        elif pattern.choice == 'increment':
            try:
                ixn_field.update(Auto=False,
                                 ValueType='increment',
                                 ActiveFieldChoice=field_choice,
                                 StartValue=pattern.increment.start,
                                 StepValue=pattern.increment.step,
                                 CountValue=pattern.increment.count)
            except Exception as e:
                print(e)
        elif pattern.choice == 'decrement':
            try:
                ixn_field.update(Auto=False,
                                 ValueType='decrement',
                                 ActiveFieldChoice=field_choice,
                                 StartValue=pattern.decrement.start,
                                 StepValue=pattern.decrement.step,
                                 CountValue=pattern.decrement.count)
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
    
        if pattern.metric_group is not None:
            ixn_field.TrackingEnabled = True
            self._api.ixn_objects[pattern.metric_group] = ixn_field.href

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
        if size.choice is None:
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
        if rate.choice is None:
            return
        ixn_frame_rate = ixn_stream.FrameRate
        args = {}
        value = None
        if rate.choice == 'percentage':
            args['Type'] = 'percentLineRate'
            value = rate.percentage
        elif rate.choice == 'pps':
            args['Type'] = 'framesPerSecond'
            value = rate.pps
        else:
            # TODO: fix for other units
            args['Type'] = 'bitsPerSecond'
            args['BitRateUnitsType'] = TrafficItem._BIT_RATE_UNITS_TYPE[
                rate.unit]
            value = rate.bps
        args['Rate'] = value
        self._update(ixn_frame_rate, **args)

    def _configure_tx_control(self, ixn_stream, hl_stream_count, duration):
        """Transform duration flows.duration to /traffic/trafficItem[*]/configElement[*]/TransmissionControl
        """
        if duration.choice is None:
            return
        ixn_tx_control = ixn_stream.TransmissionControl
        args = {}
        if duration.choice == 'continuous':
            args['Type'] = 'continuous'
            args['MinGapBytes'] = duration.continuous.gap
            args['StartDelay'] = duration.continuous.delay
            args['StartDelayUnits'] = duration.continuous.delay_unit
        elif duration.choice == 'fixed_packets':
            args['Type'] = 'fixedFrameCount'
            args['FrameCount'] = duration.fixed_packets.packets / hl_stream_count
            args['MinGapBytes'] = duration.fixed_packets.gap
            args['StartDelay'] = duration.fixed_packets.delay
            args['StartDelayUnits'] = duration.fixed_packets.delay_unit
        elif duration.choice == 'fixed_seconds':
            args['Type'] = 'fixedDuration'
            args['Duration'] = duration.fixed_seconds.seconds
            args['MinGapBytes'] = duration.fixed_seconds.gap
            args['StartDelay'] = duration.fixed_seconds.delay
            args['StartDelayUnits'] = duration.fixed_seconds.delay_unit
        elif duration.choice == 'burst':
            args['Type'] = 'custom'
            args['BurstPacketCount'] = duration.burst.packets
            args['MinGapBytes'] = duration.burst.gap
            args[
                'EnableInterBurstGap'] = True if duration.burst.gap > 0 else False
            args['InterBurstGap'] = duration.burst.inter_burst_gap
            args['InterBurstGapUnits'] = duration.burst.inter_burst_gap_unit
        self._update(ixn_tx_control, **args)

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
            regex = '^%s$' % flow_names[0]
        elif len(flow_names) > 1:
            regex = '^(%s)$' % '|'.join(flow_names)

        if request.state == 'start':
            all_flow_names = ' '.join(
                [flow.name for flow in self._api.snappi_config.flows])
            self._api._traffic_item.find(State='^unapplied$')
            if len(self._api._topology.find()) > 0:
                with Timer(self._api, 'Devices start'):
                    self._api._ixnetwork.StartAllProtocols('sync')
                    self._api.check_protocol_statistics()
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
                self._api._traffic_item.find(Name=regex, State='^stopped$')
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, 'Flows start'):
                        self._api._traffic_item.StartStatelessTrafficBlocking()
                self._api._traffic_item.find(Name=regex, State='^started$')
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, 'Flows resume'):
                        self._api._traffic_item.PauseStatelessTraffic(False)
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
        self._column_names =  request._properties.get('column_names')
        if self._column_names is None:
            self._column_names = []
        elif not isinstance(self._column_names, list):
            msg = "Invalid format of column_names passed {},\
                    expected list".format(self._column_names)
            raise Exception(msg)

        flow_names = request._properties.get('flow_names')
        if flow_names is None:
            flow_names = [flow.name for flow in self._api._config.flows]
        elif not isinstance(flow_names, list):
            msg = "Invalid format of flow_names passed {},\
                    expected list".format(flow_names)
            raise Exception(msg)

        filter = {'property': 'name', 'regex': '.*'}
        filter['regex'] = '^(%s)$' % '|'.join(flow_names)

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
