import time
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.customfield import CustomField


class TrafficItem(CustomField):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (Api): instance of the ixnetworkapi class

    Note: Sometime IxNetwork field type not matches with model packet field type
    Please use '@' to specify model packet field type. Ex
        'ether_type': 'pfcPause.header.header.ethertype@int'
    """

    _RESULT_COLUMNS = [
        ("frames_tx", "Tx Frames", int),
        ("frames_rx", "Rx Frames", int),
        ("frames_tx_rate", "Tx Frame Rate", float),
        ("frames_rx_rate", "Rx Frame Rate", float),
        ("bytes_tx", "Tx Bytes", int),
        ("bytes_rx", "Rx Bytes", int),
        ("loss", "Loss %", float),
        # ('bytes_tx_rate', 'Tx Rate (Bps)', float),
        # ('bytes_rx_rate', 'Rx Rate (Bps)', float),
    ]

    _RESULT_LATENCY_STORE_FORWARD = [
        ("minimum_ns", "Store-Forward Min Latency (ns)", int),
        ("maximum_ns", "Store-Forward Max Latency (ns)", int),
        ("average_ns", "Store-Forward Avg Latency (ns)", int),
    ]

    _RESULT_LATENCY_CUT_THROUGH = [
        ("minimum_ns", "Cut-Through Min Latency (ns)", int),
        ("maximum_ns", "Cut-Through Max Latency (ns)", int),
        ("average_ns", "Cut-Through Avg Latency (ns)", int),
    ]

    _RESULT_TIMESTAMP = [
        ("first_timestamp_ns", "First TimeStamp", int),
        ("last_timestamp_ns", "Last TimeStamp", int),
    ]

    _STACK_IGNORE = ["ethernet.fcs", "pfcPause.fcs"]

    _TYPE_TO_HEADER = {
        "ethernet": "ethernet",
        "pfcPause": "pfcpause",
        "vlan": "vlan",
        "ipv4": "ipv4",
        "ipv6": "ipv6",
        "tcp": "tcp",
        "udp": "udp",
        "gtpu": "gtpv1",
        "gTPuOptionalFields": "gtpv1option",
        "custom": "custom",
    }

    _HEADER_TO_TYPE = {
        "ethernet": "ethernet",
        "pfcpause": "pfcPause",
        "vlan": "vlan",
        "ipv4": "ipv4",
        "ipv6": "ipv6",
        "tcp": "tcp",
        "udp": "udp",
        "gtpv1": "gtpu",
        "gtpv1option": "gTPuOptionalFields",
        "custom": "custom",
    }

    _BIT_RATE_UNITS_TYPE = {
        "bps": "bitsPerSec",
        "kbps": "kbitsPerSec",
        "mbps": "mbitsPerSec",
        "gbps": "mbytesPerSec",
    }

    _LATENCY = {"cut_through": "cutThrough", "store_forward": "storeForward"}

    _PFCPAUSE = {
        "dst": "pfcPause.header.header.dstAddress",
        "src": "pfcPause.header.header.srcAddress",
        "ether_type": "pfcPause.header.header.ethertype@int",
        "control_op_code": "pfcPause.header.macControl.controlOpcode@int",
        "class_enable_vector": "pfcPause.header.macControl.priorityEnableVector@int",
        "pause_class_0": "pfcPause.header.macControl.pauseQuanta.pfcQueue0@int",
        "pause_class_1": "pfcPause.header.macControl.pauseQuanta.pfcQueue1@int",
        "pause_class_2": "pfcPause.header.macControl.pauseQuanta.pfcQueue2@int",
        "pause_class_3": "pfcPause.header.macControl.pauseQuanta.pfcQueue3@int",
        "pause_class_4": "pfcPause.header.macControl.pauseQuanta.pfcQueue4@int",
        "pause_class_5": "pfcPause.header.macControl.pauseQuanta.pfcQueue5@int",
        "pause_class_6": "pfcPause.header.macControl.pauseQuanta.pfcQueue6@int",
        "pause_class_7": "pfcPause.header.macControl.pauseQuanta.pfcQueue7@int",
    }

    _ETHERNET = {
        "dst": "ethernet.header.destinationAddress",
        "src": "ethernet.header.sourceAddress",
        "ether_type": "ethernet.header.etherType@int",
        "pfc_queue": "ethernet.header.pfcQueue",
    }

    _VLAN = {
        "id": "vlan.header.vlanTag.vlanID",
        "cfi": "vlan.header.vlanTag.cfi",
        "priority": "vlan.header.vlanTag.vlanUserPriority",
        "protocol": "vlan.header.protocolID",
    }

    _IPV4 = {
        "version": "ipv4.header.version",
        "header_length": "ipv4.header.headerLength",
        "priority": "_ipv4_priority",
        "total_length": "ipv4.header.totalLength",
        "identification": "ipv4.header.identification",
        "reserved": "ipv4.header.flags.reserved",
        "dont_fragment": "ipv4.header.flags.fragment",
        "more_fragments": "ipv4.header.flags.lastFragment",
        "fragment_offset": "ipv4.header.fragmentOffset",
        "time_to_live": "ipv4.header.ttl",
        "protocol": "ipv4.header.protocol",
        "header_checksum": "ipv4.header.checksum",
        "src": "ipv4.header.srcIp",
        "dst": "ipv4.header.dstIp",
    }

    _IPV6 = {
        "version": "ipv6.header.versionTrafficClassFlowLabel.version",
        "traffic_class": "ipv6.header.versionTrafficClassFlowLabel.trafficClass",
        "flow_label": "ipv6.header.versionTrafficClassFlowLabel.flowLabel",
        "payload_length": "ipv6.header.payloadLength",
        "next_header": "ipv6.header.nextHeader",
        "hop_limit": "ipv6.header.hopLimit",
        "src": "ipv6.header.srcIP",
        "dst": "ipv6.header.dstIP",
    }

    _TOS = {
        "precedence": "ipv4.header.priority.tos.precedence",
        "delay": "ipv4.header.priority.tos.delay",
        "throughput": "ipv4.header.priority.tos.throughput",
        "reliability": "ipv4.header.priority.tos.reliability",
        "monetary": "ipv4.header.priority.tos.monetary",
        "unused": "ipv4.header.priority.tos.unused",
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
        "version": "gtpu.header.version",
        "protocol_type": "gtpu.header.pt",
        "reserved": "gtpu.header.reserved",
        "e_flag": "gtpu.header.e",
        "s_flag": "gtpu.header.s",
        "pn_flag": "gtpu.header.n",
        "message_type": "tpu.header.type",
        "message_length": "gtpu.header.totalLength",
        "teid": "gtpu.header.teid",
    }

    _GTPV1OPTION = {
        "squence_number": "gTPuOptionalFields.header.sequenceNumber",
        "n_pdu_number": "gTPuOptionalFields.header.npduNumber",
        "next_extension_header_type": "gTPuOptionalFields.header.nextExtHdrField",
    }

    _CUSTOM = "_custom_headers"

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self.has_latency = False
        self._flow_timeout = 10

    def config(self):
        """Configure config.flows onto Ixnetwork.Traffic.TrafficItem

        CRUD
        ----
        - DELETE any TrafficItem.Name that does not exist in config.flows
        - CREATE TrafficItem for any config.flows[*].name that does not exist
        - UPDATE TrafficItem for any config.flows[*].name that exists
        """
        ixn_traffic_item = self._api._traffic_item
        self.flows_has_latency = []
        self.flows_has_timestamp = []
        self.flows_has_loss = []
        self.latency_mode = None
        self._api._remove(ixn_traffic_item, self._api.snappi_config.flows)
        if len(self._api.snappi_config.flows) > 0:
            for flow in self._api.snappi_config.flows:
                self._endpoint_validation(flow)
                args = {
                    "Name": flow.name,
                    "TrafficItemType": "l2L3",
                    "TrafficType": self._get_traffic_type(flow),
                    "SrcDestMesh": self._get_mesh_type(flow),
                }
                ixn_traffic_item.find(
                    Name="^%s$" % self._api.special_char(flow.name)
                )
                if len(ixn_traffic_item) == 0:
                    ixn_traffic_item.add(**args)
                else:
                    self._update(ixn_traffic_item, **args)
                self._configure_endpoint(
                    ixn_traffic_item.EndpointSet, flow.tx_rx
                )
                metrics = flow.get("metrics")
                if metrics is not None and metrics.enable is True:
                    self._configure_tracking(flow, ixn_traffic_item.Tracking)
                    latency = metrics.get("latency")
                    if latency is not None and latency.enable is True:
                        self.flows_has_latency.append(flow.name)
                        self._process_latency(latency)
                    timestamps = metrics.get("timestamps")
                    if timestamps is True:
                        self.flows_has_timestamp.append(flow.name)
                    loss = metrics.get("loss")
                    if loss is True:
                        self.flows_has_loss.append(flow.name)
                ixn_ce = ixn_traffic_item.ConfigElement.find()
                hl_stream_count = len(ixn_traffic_item.HighLevelStream.find())
                self._configure_stack(
                    ixn_ce, flow.get("packet", with_default=True)
                )
                self._configure_size(
                    ixn_ce, flow.get("size", with_default=True)
                )
                self._configure_rate(
                    ixn_ce, flow.get("rate", with_default=True)
                )
                self._configure_tx_control(
                    ixn_ce, hl_stream_count, flow.duration
                )
            self._configure_options()
            self._configure_latency()

    def _process_latency(self, latency):
        if self.latency_mode is None:
            if latency.mode is not None:
                self.latency_mode = latency.mode
            else:
                self.latency_mode = "store_forward"
        else:
            if latency.mode is not None and self.latency_mode != latency.mode:
                raise Exception("Latency mode needs to be same for all flows")

    def _configure_latency(self):
        ixn_latency = self._api._traffic.Statistics.Latency
        if self.latency_mode is not None:
            self.has_latency = True
            ixn_CpdpConvergence = self._api._traffic.Statistics.CpdpConvergence
            ixn_CpdpConvergence.Enabled = False
            ixn_latency.Enabled = True
            ixn_latency.Mode = TrafficItem._LATENCY[self.latency_mode]
        else:
            self.has_latency = False
            ixn_latency.Enabled = False

    def _configure_tracking(self, flow, ixn_tracking):
        """Set tracking options"""
        ixn_tracking.find()
        tracking_options = ["trackingenabled0"]
        if flow.tx_rx.choice == "device":
            tracking_options.append("sourceDestPortPair0")
        if set(tracking_options) != set(ixn_tracking.TrackBy):
            ixn_tracking.update(TrackBy=tracking_options)

    def _configure_options(self):
        enable_min_frame_size = False
        for flow in self._api.snappi_config.flows:
            if (
                len(flow.packet) == 1
                and flow.packet[0].parent.choice == "pfcpause"
            ):
                enable_min_frame_size = True
                break
        if self._api._traffic.EnableMinFrameSize != enable_min_frame_size:
            self._api._traffic.EnableMinFrameSize = enable_min_frame_size

    def _endpoint_validation(self, flow):
        if flow.tx_rx.choice is None:
            raise ValueError(
                "%s Flow.tx_rx property cannot be None" % flow.name
            )
        if flow.tx_rx.choice == "device":
            device = flow.tx_rx.device
            if not isinstance(device.tx_names, list) or not isinstance(
                device.rx_names, list
            ):
                raise ValueError(
                    "device tx_names and rx_names must be a list "
                    "in flow %s" % flow.name
                )
            if len(device.tx_names) != len(set(device.tx_names)):
                raise ValueError(
                    "All names in device tx_names "
                    "must be unique for flow %s" % flow.name
                )
            if len(device.rx_names) != len(set(device.rx_names)):
                raise ValueError(
                    "All names in device rx_names "
                    "must be unique for flow %s" % flow.name
                )

    def _get_mesh_type(self, flow):
        if flow.tx_rx.choice == "port":
            mesh_type = "oneToOne"
        else:
            device = flow.tx_rx.device
            if device.mode == "mesh" or device.mode is None:
                mesh_type = "manyToMany"
            else:
                mesh_type = "oneToOne"
                if len(device.tx_names) != len(device.rx_names):
                    raise ValueError(
                        "Length of device tx_names and rx_names "
                        "must be same for device mode ONE_TO_ONE in flow %s"
                        % flow.name
                    )
        return mesh_type

    def _get_traffic_type(self, flow):
        if flow.tx_rx.choice == "port":
            encap = "raw"
        else:
            encap_list = []
            device = flow.tx_rx.device
            if device.tx_names is not None:
                for tx_name in device.tx_names:
                    encap_list.append(self._api.get_device_encap(tx_name))
            if device.rx_names is not None:
                for rx_name in device.rx_names:
                    encap_list.append(self._api.get_device_encap(rx_name))
            if len(set(encap_list)) == 1:
                encap = encap_list[0]
            else:
                raise Exception(
                    "All devices identified in tx_names and rx_names "
                    "must be of same type in flow %s" % flow.name
                )
        return encap

    def _configure_endpoint(self, ixn_endpoint_set, endpoint):
        """Transform flow.tx_rx to /trafficItem/endpointSet
        The model allows for only one endpointSet per traffic item
        """
        args = {"Sources": [], "Destinations": []}
        if endpoint.choice == "port":
            args["Sources"].append(
                self._api.get_ixn_object(endpoint.port.tx_name)
                .Protocols.find()
                .href
            )
            if endpoint.port.rx_name != None:
                args["Destinations"].append(
                    self._api.get_ixn_object(endpoint.port.rx_name)
                    .Protocols.find()
                    .href
                )
        else:
            for device_name in endpoint.device.tx_names:
                args["Sources"].append(self._api.get_ixn_href(device_name))
            for device_name in endpoint.device.rx_names:
                args["Destinations"].append(
                    self._api.get_ixn_href(device_name)
                )
        ixn_endpoint_set.find()
        if len(ixn_endpoint_set) > 1:
            ixn_endpoint_set.remove()
        if len(ixn_endpoint_set) == 0:
            ixn_endpoint_set.add(**args)
        elif (
            ixn_endpoint_set.Sources != args["Sources"]
            or ixn_endpoint_set.Destinations != args["Destinations"]
            or len(ixn_endpoint_set.parent.ConfigElement.find()) == 0
        ):
            self._update(ixn_endpoint_set, **args)

    def _update(self, ixn_object, **kwargs):
        from ixnetwork_restpy.base import Base

        update = False
        for name, value in kwargs.items():
            if (
                isinstance(value, list)
                and len(value) > 0
                and isinstance(value[0], Base)
            ):
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
                elif (
                    TrafficItem._TYPE_TO_HEADER[stack_type_id] != header.choice
                ):
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
            if (
                TrafficItem._TYPE_TO_HEADER[stack_type_id]
                != headers[header_index].choice
            ):
                stacks_to_remove.append(ixn_stack[i])
            else:
                header_index += 1
        for stack in stacks_to_remove[::-1]:
            stack.Remove()

    def _add_stack(self, ixn_stream, ixn_stack, header):
        type_id = "^%s$" % TrafficItem._HEADER_TO_TYPE[header.choice]
        template = self._api._traffic.ProtocolTemplate.find(
            StackTypeId=type_id
        )
        stack_href = ixn_stack.AppendProtocol(template)
        return ixn_stream.Stack.read(stack_href)

    def _configure_field(self, ixn_field, header, field_choice=False):
        """Transform flow.packets[0..n].header.choice to /traffic/trafficItem/configElement/stack/field"""
        field_map = getattr(self, "_%s" % header.choice.upper())
        packet = getattr(header, header.choice)
        if isinstance(field_map, dict) is False:
            method = getattr(self, field_map)
            method(ixn_field, packet)
            return

        for packet_field_name in dir(packet):
            if packet_field_name in field_map:
                pattern = packet.get(packet_field_name, with_default=True)
                if pattern is not None:
                    field_type_id = field_map[packet_field_name]
                    self._configure_pattern(
                        ixn_field, field_type_id, pattern, field_choice
                    )

    def _configure_pattern(
        self, ixn_field, field_type_id, pattern, field_choice=False
    ):
        def get_value(field_value):
            if field_type is None:
                return field_value
            ixn_type = ixn_field.ValueFormat
            if field_type == "int" and ixn_type == "hex":
                field_value = str(hex(int(field_value)))[2:]
            return field_value

        custom_field = getattr(self, field_type_id, None)
        if custom_field is not None:
            if pattern.choice is not None:
                custom_field(ixn_field, pattern)
            return
        id_type = field_type_id.split("@")
        field_type_id, field_type = (
            id_type if len(id_type) > 1 else [id_type[0], None]
        )
        ixn_field = ixn_field.find(FieldTypeId=field_type_id)
        if pattern.choice is None:
            self._set_default(ixn_field, field_choice)
            return

        if pattern.choice == "value":
            ixn_field.update(
                Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType="singleValue",
                SingleValue=get_value(pattern.value),
            )
        elif pattern.choice == "values":
            ixn_field.update(
                Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType="valueList",
                ValueList=[get_value(v) for v in pattern.values],
            )
        elif pattern.choice == "increment":
            ixn_field.update(
                Auto=False,
                ValueType="increment",
                ActiveFieldChoice=field_choice,
                StartValue=get_value(pattern.increment.start),
                StepValue=pattern.increment.step,
                CountValue=pattern.increment.count,
            )
        elif pattern.choice == "decrement":
            ixn_field.update(
                Auto=False,
                ValueType="decrement",
                ActiveFieldChoice=field_choice,
                StartValue=get_value(pattern.decrement.start),
                StepValue=pattern.decrement.step,
                CountValue=pattern.decrement.count,
            )
        elif pattern.choice == "random":
            ixn_field.update(
                Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType="repeatableRandomRange",
                MinValue=pattern.random.min,
                MaxValue=pattern.random.max,
                StepValue=pattern.random.step,
                Seed=pattern.random.seed,
                CountValue=pattern.random.count,
            )
        else:
            # TBD: add to set_config errors - invalid pattern specified
            pass

        if pattern.get("metric_group") is not None:
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
            ixn_field.update(
                Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType="singleValue",
                SingleValue=ixn_field.DefaultValue,
            )

    def _configure_size(self, ixn_stream, size):
        """Transform frameSize flows.size to /traffic/trafficItem[*]/configElement[*]/frameSize"""
        if size.choice is None:
            return
        ixn_frame_size = ixn_stream.FrameSize
        args = {}
        if size.choice == "fixed":
            args["Type"] = "fixed"
            args["FixedSize"] = size.fixed
        elif size.choice == "increment":
            args["Type"] = "increment"
            args["IncrementFrom"] = size.increment.start
            args["IncrementTo"] = size.increment.end
            args["IncrementStep"] = size.increment.step
        elif size.choice == "random":
            args["Type"] = "random"
            args["RandomMin"] = size.random.min
            args["RandomMax"] = size.random.max
        else:
            print(
                "Warning - We need to implement this %s choice" % size.choice
            )
        self._update(ixn_frame_size, **args)

    def _configure_rate(self, ixn_stream, rate):
        """Transform frameRate flows.rate to /traffic/trafficItem[*]/configElement[*]/frameRate"""
        if rate.choice is None:
            return
        ixn_frame_rate = ixn_stream.FrameRate
        args = {}
        value = None
        if rate.choice == "percentage":
            args["Type"] = "percentLineRate"
            value = rate.percentage
        elif rate.choice == "pps":
            args["Type"] = "framesPerSecond"
            value = rate.pps
        else:
            args["Type"] = "bitsPerSecond"
            args["BitRateUnitsType"] = TrafficItem._BIT_RATE_UNITS_TYPE[
                rate.choice
            ]
            value = getattr(rate, rate.choice)
        args["Rate"] = value
        self._update(ixn_frame_rate, **args)

    def _configure_delay(self, parent, args):
        delay = parent.get("delay", with_default=True)
        if delay.choice is not None:
            value = getattr(delay, delay.choice, None)
            if value is None:
                raise Exception("Delay must be of type <int>")
            if isinstance(value, float) and not float.is_integer(value):
                self._api.warning(
                    "Cast Delay to <int> due to software limitation"
                )
            if delay.choice == "microseconds":
                args["StartDelayUnits"] = "nanoseconds"
                args["StartDelay"] = value * 1000
            else:
                args["StartDelayUnits"] = delay.choice
                args["StartDelay"] = value

    def _configure_tx_control(self, ixn_stream, hl_stream_count, duration):
        """Transform duration flows.duration to /traffic/trafficItem[*]/configElement[*]/TransmissionControl"""
        if duration.choice is None:
            return
        ixn_tx_control = ixn_stream.TransmissionControl
        args = {}
        if duration.choice == "continuous":
            args["Type"] = "continuous"
            args["MinGapBytes"] = duration.continuous.gap
            self._configure_delay(duration.continuous, args)
        elif duration.choice == "fixed_packets":
            args["Type"] = "fixedFrameCount"
            args["FrameCount"] = (
                duration.fixed_packets.packets / hl_stream_count
            )
            args["MinGapBytes"] = duration.fixed_packets.gap
            self._configure_delay(duration.fixed_packets, args)
        elif duration.choice == "fixed_seconds":
            args["Type"] = "fixedDuration"
            args["Duration"] = duration.fixed_seconds.seconds
            args["MinGapBytes"] = duration.fixed_seconds.gap
            self._configure_delay(duration.fixed_seconds, args)
        elif duration.choice == "burst":
            if (
                duration.burst.bursts is not None
                and int(duration.burst.bursts) > 0
            ):
                args["Type"] = "burstFixedDuration"
                args["RepeatBurst"] = duration.burst.bursts
            else:
                args["Type"] = "custom"
            args["BurstPacketCount"] = duration.burst.packets
            args["MinGapBytes"] = duration.burst.gap
            args["EnableInterBurstGap"] = True
            inter_burst_gap = duration.burst.get(
                "inter_burst_gap", with_default=True
            )
            if inter_burst_gap.choice is not None:
                value = getattr(inter_burst_gap, inter_burst_gap.choice, None)
                if value is None:
                    raise Exception(
                        "Inter packet gap mush be of type some <int> value"
                    )
                if inter_burst_gap.choice == "microseconds":
                    args["InterBurstGap"] = value * 1000
                    args["InterBurstGapUnits"] = "nanoseconds"
                else:
                    args["InterBurstGap"] = value
                    args["InterBurstGapUnits"] = inter_burst_gap.choice
        self._update(ixn_tx_control, **args)

    def transmit(self, request):
        """Set flow transmit
        1) If start then start any device protocols that are traffic dependent
        2) If start then generate and apply traffic
        3) Execute requested transmit action (start|stop|pause|resume)
        """
        regex = ""
        flow_names = [flow.name for flow in self._api._config.flows]
        if request and request.flow_names:
            flow_names = request.flow_names
        if len(flow_names) == 1:
            regex = "^%s$" % self._api.special_char(flow_names)[0]
        elif len(flow_names) > 1:
            regex = "^(%s)$" % "|".join(self._api.special_char(flow_names))

        if request.state == "start":
            if len(self._api._topology.find()) > 0:
                with Timer(self._api, "Devices start"):
                    self._api._ixnetwork.StartAllProtocols("sync")
                    self._api.check_protocol_statistics()
            if len(self._api._traffic_item.find()) == 0:
                return
            self._api._traffic_item.find(State="^unapplied$")
            if len(self._api._traffic_item) > 0:
                with Timer(self._api, "Flows generate/apply"):
                    self._api._traffic_item.Generate()
                    self._api._traffic.Apply()
            self._api._traffic_item.find(State="^started$")
            if len(self._api._traffic_item) == 0:
                with Timer(self._api, "Flows clear statistics"):
                    self._api._ixnetwork.ClearStats(
                        [
                            "waitForPortStatsRefresh",
                            "waitForTrafficStatsRefresh",
                        ]
                    )
            self._api.capture._start_capture()
        self._api._traffic_item.find(Name=regex)
        if len(self._api._traffic_item) > 0:
            if request.state == "start":
                self._api._traffic_item.find(
                    Name=regex, Suspend=True, State="^started$"
                )
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, "Flows resume"):
                        self._api._traffic_item.PauseStatelessTraffic(False)
                self._api._traffic_item.find(Name=regex, State="^stopped$")
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, "Flows start"):
                        self._api._traffic_item.StartStatelessTrafficBlocking()
            elif request.state == "stop":
                self._api._traffic_item.find(Name=regex, State="^started$")
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, "Flows stop"):
                        self._api._traffic_item.StopStatelessTrafficBlocking()
            elif request.state == "pause":
                self._api._traffic_item.find(Name=regex, State="^started$")
                if len(self._api._traffic_item) > 0:
                    with Timer(self._api, "Flows pause"):
                        self._api._traffic_item.PauseStatelessTraffic(True)
        if request.state == "stop":
            if len(self._api._topology.find()) > 0:
                with Timer(self._api, "Devices stop"):
                    self._api._ixnetwork.StopAllProtocols("sync")

    def _set_result_value(
        self, row, column_name, column_value, column_type=str
    ):
        if (
            len(self._column_names) > 0
            and column_name not in self._column_names
        ):
            return
        try:
            row[column_name] = column_type(column_value)
        except:
            if column_type.__name__ in ["float", "int"]:
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
            "txStopWatchExpected",
            "locked",
            "started",
            "startedWaitingForStats",
            "startedWaitingForStreams",
            "stoppedWaitingForStats",
        ]
        if state in started_states:
            return "started"
        else:
            return "stopped"

    def results(self, request):
        """Return flow results"""
        # setup parameters
        self._column_names = request.get("metric_names")
        if self._column_names is None:
            self._column_names = []
        elif not isinstance(self._column_names, list):
            msg = "Invalid format of column_names passed {},\
                    expected list".format(
                self._column_names
            )
            raise Exception(msg)

        flow_names = request.get("flow_names")
        has_request_flow = True
        if flow_names is None or len(flow_names) == 0:
            has_request_flow = False
            flow_names = [flow.name for flow in self._api._config.flows]
        elif not isinstance(flow_names, list):
            msg = "Invalid format of flow_names passed {},\
                    expected list".format(
                flow_names
            )
            raise Exception(msg)
        final_flow_names = []
        for flow in self._api._config.flows:
            metrics = flow.get("metrics")
            if metrics is None:
                continue
            if metrics.enable is True and flow.name in flow_names:
                final_flow_names.append(flow.name)
        if len(final_flow_names) == 0:
            msg = """
            To fetch flow metrics at least one flow shall have metric enabled
            """
            raise Exception(msg.strip())
        diff = set(flow_names).difference(final_flow_names)
        if len(diff) > 0 and has_request_flow is True:
            raise Exception(
                "Flow metrics is not enabled on flows {}".format(
                    "".join(list(diff))
                )
            )
        flow_names = final_flow_names
        regfilter = {"property": "name", "regex": ".*"}
        regfilter["regex"] = "^(%s)$" % "|".join(
            self._api.special_char(flow_names)
        )

        flow_count = len(flow_names)
        ixn_page = self._api._ixnetwork.Statistics.View.find(
            Caption="Flow Statistics"
        ).Page
        if ixn_page.PageSize < flow_count:
            ixn_page.PageSize = flow_count

        # initialize result values
        flow_rows = {}
        for traffic_item in self._api.select_traffic_items(
            traffic_item_filters=[regfilter]
        ).values():
            for stream in traffic_item["highLevelStream"]:
                for rx_port_name in stream["rxPortNames"]:
                    flow_row = {}
                    self._set_result_value(
                        flow_row, "name", traffic_item["name"]
                    )
                    self._set_result_value(
                        flow_row,
                        "transmit",
                        self._get_state(traffic_item["state"]),
                    )
                    self._set_result_value(
                        flow_row, "port_tx", stream["txPortName"]
                    )
                    self._set_result_value(flow_row, "port_rx", rx_port_name)
                    # init all columns with corresponding zero-values so that
                    # the underlying dictionary contains all requested columns
                    # in an event of unwanted exceptions
                    for (
                        external_name,
                        _,
                        external_type,
                    ) in self._RESULT_COLUMNS:
                        self._set_result_value(
                            flow_row, external_name, 0, external_type
                        )
                    flow_rows[
                        traffic_item["name"]
                        + stream["txPortName"]
                        + rx_port_name
                    ] = flow_row

        flow_stat = self._api.assistant.StatViewAssistant("Flow Statistics")
        for row in flow_stat.Rows:
            name = row["Traffic Item"]
            if len(flow_names) > 0 and name not in flow_names:
                continue
            tx_port = row["Tx Port"]
            rx_port = row["Rx Port"]
            if name + tx_port + rx_port in flow_rows:
                flow_row = flow_rows[name + tx_port + rx_port]
                if (
                    float(row["Tx Frame Rate"]) > 0
                    or int(row["Tx Frames"]) == 0
                ):
                    flow_row["transmit"] = "started"
                else:
                    flow_row["transmit"] = "stopped"
                for (
                    external_name,
                    internal_name,
                    external_type,
                ) in self._RESULT_COLUMNS:
                    # keep plugging values for next columns even if the
                    # current one raises exception
                    try:
                        self._set_result_value(
                            flow_row,
                            external_name,
                            row[internal_name],
                            external_type,
                        )
                    except Exception:
                        # TODO print a warning maybe ?
                        pass
                if name in self.flows_has_latency:
                    self._construct_latency(flow_row, row)
                if name in self.flows_has_timestamp:
                    self._construct_timestamp(flow_row, row)
                if name not in self.flows_has_loss:
                    flow_row.pop("loss")
        return list(flow_rows.values())

    def _construct_latency(self, flow_row, row):
        if self.latency_mode == "store_forward":
            latency_map = TrafficItem._RESULT_LATENCY_STORE_FORWARD
        else:
            latency_map = TrafficItem._RESULT_LATENCY_CUT_THROUGH
        latency_result = {}
        for external_name, internal_name, external_type in latency_map:
            if internal_name not in row.Columns:
                raise Exception(
                    "Could not fetch column %s in latency metrics"
                    % internal_name
                )
            try:
                self._set_result_value(
                    latency_result,
                    external_name,
                    row[internal_name],
                    external_type,
                )
            except Exception as exception_err:
                self._api.warning(
                    "Could not fetch latency metrics: %s" % exception_err
                )
                pass
        if len(latency_result) > 0:
            flow_row["latency"] = latency_result

    def _construct_timestamp(self, flow_row, row):
        timestamp_result = {}
        for (
            external_name,
            internal_name,
            external_type,
        ) in TrafficItem._RESULT_TIMESTAMP:
            if internal_name not in row.Columns:
                raise Exception(
                    "Could not fetch column %s in timestamp metrics"
                    % internal_name
                )

            try:
                val = row[internal_name].split(":")
                mul = [3600, 60, 1]
                sv = sum(
                    [
                        int(float(v) * 10 ** 9 + 0.1) * mul[i]
                        for i, v in enumerate(val)
                    ]
                )
                self._set_result_value(
                    timestamp_result, external_name, sv, external_type
                )
            except Exception as exception_err:
                self._api.warning(
                    "Could not fetch timestamp metrics: %s" % exception_err
                )
                pass
        if len(timestamp_result) > 0:
            flow_row["timestamps"] = timestamp_result
