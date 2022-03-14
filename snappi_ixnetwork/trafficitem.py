import json
import snappi
from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.customfield import CustomField


class TrafficItem(CustomField):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (Api): instance of the ixnetworkapi class
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
        "vxlan": "vxlan",
        "ethernetARP": "arp",
    }

    _HEADER_TO_TYPE = {
        "ethernet": "ethernet",
        "pfcpause": "pfcPause",
        "ethernetpause": "ethernet",
        "ethernetpauseUHD": "globalPause",
        "vlan": "vlan",
        "ipv4": "ipv4",
        "ipv6": "ipv6",
        "tcp": "tcp",
        "udp": "udp",
        "gtpv1": "gtpu",
        "gtpv1option": "gTPuOptionalFields",
        "custom": "custom",
        "vxlan": "vxlan",
        "arp": "ethernetARP",
    }

    _ETHERNETPAUSEUHD = {
        "dst": "globalPause.header.header.dstAddress",
        "src": "globalPause.header.header.srcAddress",
        "ether_type": "globalPause.header.header.ethertype",
        "control_op_code": "globalPause.header.macControl.controlOpcode",
        "time": "globalPause.header.macControl.pfcQueue0",
        "order": ["dst", "src", "ether_type", "control_op_code", "time"],
        "convert_int_to_hex": ["ether_type", "time"],
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
        "ether_type": "pfcPause.header.header.ethertype",
        "control_op_code": "pfcPause.header.macControl.controlOpcode",
        "class_enable_vector": "pfcPause.header.macControl.priorityEnableVector",
        "pause_class_0": "pfcPause.header.macControl.pauseQuanta.pfcQueue0",
        "pause_class_1": "pfcPause.header.macControl.pauseQuanta.pfcQueue1",
        "pause_class_2": "pfcPause.header.macControl.pauseQuanta.pfcQueue2",
        "pause_class_3": "pfcPause.header.macControl.pauseQuanta.pfcQueue3",
        "pause_class_4": "pfcPause.header.macControl.pauseQuanta.pfcQueue4",
        "pause_class_5": "pfcPause.header.macControl.pauseQuanta.pfcQueue5",
        "pause_class_6": "pfcPause.header.macControl.pauseQuanta.pfcQueue6",
        "pause_class_7": "pfcPause.header.macControl.pauseQuanta.pfcQueue7",
        "order": [
            "dst",
            "src",
            "ether_type",
            "control_op_code",
            "class_enable_vector",
            "pause_class_0",
            "pause_class_1",
            "pause_class_2",
            "pause_class_3",
            "pause_class_4",
            "pause_class_5",
            "pause_class_6",
            "pause_class_7",
        ],
        "convert_int_to_hex": [
            "ether_type",
            "control_op_code",
            "class_enable_vector",
            "pause_class_0",
            "pause_class_1",
            "pause_class_2",
            "pause_class_3",
            "pause_class_4",
            "pause_class_5",
            "pause_class_6",
            "pause_class_7",
        ],
    }

    _ETHERNET = {
        "dst": "ethernet.header.destinationAddress",
        "src": "ethernet.header.sourceAddress",
        "ether_type": "ethernet.header.etherType",
        "pfc_queue": "ethernet.header.pfcQueue",
        "order": ["dst", "src", "ether_type", "pfc_queue"],
        "convert_int_to_hex": ["ether_type"],
        # sets to default only when traffic type is `Raw`
        "auto_to_default": ["src", "dst"],
    }

    _ETHERNETPAUSE = {
        "dst": "ethernet.header.destinationAddress",
        "src": "ethernet.header.sourceAddress",
        "ether_type": "ethernet.header.etherType",
        "control_op_code": CustomField._process_ethernet_pause,
        "order": ["dst", "src", "ether_type"],
        "convert_int_to_hex": ["ether_type"],
    }

    _ARP = {
        "hardware_type": "ethernetARP.header.hardwareType",
        "protocol_type": "ethernetARP.header.protocolType",
        "hardware_length": "ethernetARP.header.hardwareAddressLength",
        "protocol_length": "ethernetARP.header.protocolAddressLength",
        "operation": "ethernetARP.header.opCode",
        "sender_hardware_addr": "ethernetARP.header.srcHardwareAddress",
        "sender_protocol_addr": "ethernetARP.header.srcIP",
        "target_hardware_addr": "ethernetARP.header.dstHardwareAddress",
        "target_protocol_addr": "ethernetARP.header.dstIP",
        "order": [
            "hardware_type",
            "protocol_type",
            "hardware_length",
            "protocol_length",
            "operation",
            "sender_hardware_addr",
            "sender_protocol_addr",
            "target_hardware_addr",
            "target_protocol_addr",
        ],
        "convert_int_to_hex": [
            "hardware_type",
            "protocol_type",
            "hardware_length",
            "protocol_length",
        ],
    }

    _VLAN = {
        "id": "vlan.header.vlanTag.vlanID",
        "cfi": "vlan.header.vlanTag.cfi",
        "priority": "vlan.header.vlanTag.vlanUserPriority",
        "tpid": "vlan.header.protocolID",
        "order": ["priority", "cfi", "id", "tpid"],
        "convert_int_to_hex": ["tpid"],
    }

    _IPV4 = {
        "version": "ipv4.header.version",
        "header_length": "ipv4.header.headerLength",
        "priority": CustomField._process_ipv4_priority,
        "raw": "ipv4.header.priority.raw",
        "precedence": "ipv4.header.priority.tos.precedence",
        "delay": "ipv4.header.priority.tos.delay",
        "throughput": "ipv4.header.priority.tos.throughput",
        "reliability": "ipv4.header.priority.tos.reliability",
        "monetary": "ipv4.header.priority.tos.monetary",
        "unused": "ipv4.header.priority.tos.unused",
        "default": "ipv4.header.priority.ds.phb.defaultPHB.defaultPHB",
        "default-unused": "ipv4.header.priority.ds.phb.defaultPHB.unused",
        "phb": "ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB",
        "phb-unused": "ipv4.header.priority.ds.phb.classSelectorPHB.unused",
        "af": "ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB",
        "af-unused": "ipv4.header.priority.ds.phb.assuredForwardingPHB.unused",
        "ef": "ipv4.header.priority.ds.phb.expeditedForwardingPHB.expeditedForwardingPHB",
        "ef-unused": "ipv4.header.priority.ds.phb.expeditedForwardingPHB.unused",
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
        "order": [
            "version",
            "header_length",
            "raw",
            "precedence",
            "delay",
            "throughput",
            "reliability",
            "monetary",
            "unused",
            "default",
            "default-unused",
            "phb",
            "phb-unused",
            "af",
            "af-unused",
            "ef",
            "ef-unused",
            "total_length",
            "identification",
            "reserved",
            "dont_fragment",
            "more_fragments",
            "fragment_offset",
            "time_to_live",
            "protocol",
            "header_checksum",
            "src",
            "dst",
        ],
        "auto_to_default": ["src", "dst"],
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
        "order": [
            "version",
            "traffic_class",
            "flow_label",
            "payload_length",
            "next_header",
            "hop_limit",
            "src",
            "dst",
        ],
    }

    _TCP = {
        "src_port": "tcp.header.srcPort",
        "dst_port": "tcp.header.dstPort",
        "seq_num": "tcp.header.sequenceNumber",
        "ack_num": "tcp.header.acknowledgementNumber",
        "data_offset": "tcp.header.dataOffset",
        "reserved": "tcp.header.reserved",
        "ecn_ns": "tcp.header.ecn.nsBit",
        "ecn_cwr": "tcp.header.ecn.cwrBit",
        "ecn_echo": "tcp.header.ecn.ecnEchoBit",
        "ctl_urg": "tcp.header.controlBits.urgBit",
        "ctl_ack": "tcp.header.controlBits.ackBit",
        "ctl_psh": "tcp.header.controlBits.pshBit",
        "ctl_rst": "tcp.header.controlBits.rstBit",
        "ctl_syn": "tcp.header.controlBits.synBit",
        "ctl_fin": "tcp.header.controlBits.finBit",
        "window": "tcp.header.window",
        "order": [
            "src_port",
            "dst_port",
            "seq_num",
            "ack_num",
            "data_offset",
            "reserved",
            "ecn_ns",
            "ecn_cwr",
            "ecn_echo",
            "ctl_urg",
            "ctl_ack",
            "ctl_psh",
            "ctl_rst",
            "ctl_syn",
            "ctl_fin",
            "window",
        ],
    }

    _UDP = {
        "src_port": "udp.header.srcPort",
        "dst_port": "udp.header.dstPort",
        "length": "udp.header.length",
        "checksum": "udp.header.checksum",
        "order": ["src_port", "dst_port", "length", "checksum"],
    }

    _GTPV1 = {
        # GTP header needs to be added
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
        # GTP header needs to be added
        "squence_number": "gTPuOptionalFields.header.sequenceNumber",
        "n_pdu_number": "gTPuOptionalFields.header.npduNumber",
        "next_extension_header_type": "gTPuOptionalFields.header.nextExtHdrField",
    }

    _CUSTOM = {
        "length": "custom.header.length",
        "data": "custom.header.data",
        "bytes": CustomField._process_custom_header,
        "order": ["length", "data"],
    }

    _VXLAN = {
        "flags": "vxlan.header.flags",
        "reserved0": "vxlan.header.reserved",
        "vni": "vxlan.header.vni",
        "reserved1": "vxlan.header.reserved8",
        "order": ["flags", "reserved0", "vni", "reserved1"],
        "convert_int_to_hex": ["flags", "reserved0", "reserved1"],
    }

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self.ixn_config = None
        self.traffic_index = 1
        self.has_latency = False
        self._flow_timeout = 10
        self.flows_has_latency = []
        self.flows_has_timestamp = []
        self.flows_has_loss = []

    def _get_search_payload(self, parent, child, properties, filters):
        payload = {
            "selects": [
                {
                    "from": parent,
                    "properties": [],
                    "children": [
                        {
                            "child": child,
                            "properties": properties,
                            "filters": filters,
                        }
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "{}/operations/select?xpath=true".format(
            self._api.assistant._ixnetwork.href
        )
        return (url, payload)

    def _export_config(self):
        href = "%sresourceManager" % self._api._ixnetwork.href
        url = "%s/operations/exportconfig" % href
        payload = {
            "arg1": href,
            "arg2": ["/traffic/trafficItem/descendant-or-self::*"],
            "arg3": True,
            "arg4": "json",
        }
        res = self._api._request("POST", url=url, payload=payload)
        return json.loads(res["result"])

    def _importconfig(self, imports):
        imports["xpath"] = "/"
        href = "%sresourceManager" % self._api._ixnetwork.href
        url = "%s/operations/importconfig" % href

        payload = {
            "arg1": href,
            "arg2": json.dumps(imports),
            "arg3": False,
            "arg4": "suppressNothing",
            "arg5": True,
        }
        try:
            # TODO for larger config rest api is throwing error,
            # with no url found, when the first response is 202 (in-progress)
            # its keep checking the status of the url with 1 sec sleep, and
            # after a while error is thrown. but could see the configuration
            # applied at Ixnetwork. (Need to check with Eng team)
            response = self._api._request("POST", url=url, payload=payload)
        except Exception:
            return
        if (
            response["result"].get("errata") is not None
            and response["result"]["errata"] != []
        ):
            self._api.get_json_import_errors()
            raise SnappiIxnException(
                400, "{}".format(response["result"]["errata"])
            )

    def get_ports_encap(self, config):
        ixn = self._api.assistant._ixnetwork
        myfilter = [{"property": "name", "regex": ".*"}]
        url, payload = self._get_search_payload(
            "/",
            "(?i)^(vport)$",
            ["name"],
            myfilter,
        )
        result = ixn._connection._execute(url, payload)
        vports = {}
        for vp in result:
            if vp.get("vport") is None:
                continue
            for v in vp["vport"]:
                vports[v["name"]] = v["xpath"]
        return vports

    def get_device_info(self, config):
        if len(config.devices) == 0:
            return {}
        dev_names = []
        for f in config.flows:
            if f.tx_rx.choice == "port":
                continue
            dev_names.extend(f.tx_rx.device.tx_names)
            dev_names.extend(f.tx_rx.device.rx_names)
        dev_names = list(set(dev_names))
        if dev_names == []:
            return {}
        paths = {}
        for i, dev_name in enumerate(dev_names):
            paths[dev_name] = {"dev_info": self._api.ixn_objects.get(dev_name)}
            paths[dev_name]["type"] = self._api.get_device_encap(dev_name)
        return paths

    def get_ixn_config(self, config):
        ixn = self._api.assistant._ixnetwork
        myfilter = [{"property": "name", "regex": ".*"}]
        url, payload = self._get_search_payload(
            "/traffic",
            "(?i)^(trafficItem|configElement|frameRate"
            "|frameSize|transmissionControl|stack|field|highLevelStream"
            "|tracking|transmissionDistribution)$",
            [
                "name",
                "trafficType",
                "type",
                "rate",
                "duration",
                "displayName",
                "valueFormat",
            ],
            myfilter,
        )
        self.ixn_config = None
        tr = self.create_traffic(config)
        imports = {}
        imports["traffic"] = tr
        self._importconfig(imports)
        return ixn._connection._execute(url, payload)

    def remove_ixn_traffic(self):
        if len(self._api._ixnetwork.Traffic.TrafficItem.find()) > 0:
            # with Timer(self._api, "Remove Flows"):
            start_states = [
                "txStopWatchExpected",
                "locked",
                "started",
                "startedWaitingForStats",
                "startedWaitingForStreams",
                "stoppedWaitingForStats",
            ]
            state = self._api._ixnetwork.Traffic.State
            if state in start_states:
                self._api._ixnetwork.Traffic.StopStatelessTrafficBlocking()
            url = "%s/traffic/trafficItem" % self._api._ixnetwork.href
            self._api._request("DELETE", url)
            self._api._ixnetwork.Traffic.TrafficItem.find().refresh()
        self.traffic_index = 1

    def _gen_dev_endpoint(self, devices, names, endpoints, scalable_endpoints):
        while len(names) > 0:
            gen_name = None
            name = names[0]
            dev_info = devices[name]["dev_info"]
            xpath = dev_info.xpath
            cmp_names = set(dev_info.names)
            if len(cmp_names) > 0:
                inter_names = cmp_names.intersection(set(names))
                # todo: optimize within scalable
                if len(inter_names) == len(cmp_names):
                    endpoints.append(xpath)
                    gen_name = inter_names
                else:
                    gen_name = name
                    scalable_endpoints.append(
                        {
                            "arg1": xpath,
                            "arg2": 1,
                            "arg3": 1,
                            "arg4": dev_info.index + 1,
                            "arg5": dev_info.multiplier,
                        }
                    )
            else:
                gen_name = name
                endpoints.append(xpath)
            if not isinstance(gen_name, set):
                gen_name = {gen_name}
            names = list(set(names).difference(gen_name))

    def create_traffic(self, config):
        flows = config.flows
        tr = {"xpath": "/traffic", "trafficItem": []}
        ports = self.get_ports_encap(config)
        devices = self.get_device_info(config)
        for index, flow in enumerate(flows):
            if flow._properties.get("name") is None:
                raise Exception("name shall not be null for flows")
            if flow._properties.get("tx_rx") is None:
                msg = (
                    "Please configure the flow endpoint"
                    "for flow indexed at %s" % index
                )
                raise Exception(msg)
            self._endpoint_validation(flow)
            if flow.tx_rx.choice is None:
                msg = "Flow endpoint needs to be either port or device"
                raise Exception(msg)

            tr_xpath = "/traffic/trafficItem[%d]" % self.traffic_index
            tr["trafficItem"].append(
                {
                    "xpath": tr_xpath,
                    "name": "%s" % flow.name,
                    "srcDestMesh": self._get_mesh_type(flow),
                }
            )

            tr["trafficItem"][-1]["endpointSet"] = [
                {
                    "xpath": tr["trafficItem"][-1]["xpath"]
                    + "/endpointSet[1]",
                }
            ]
            if flow.tx_rx.choice == "port":
                tr_type = "raw"
                ep = getattr(flow.tx_rx, "port")
                tx_objs = ["%s/protocols" % ports.get(ep.tx_name)]
                rx_objs = ["%s/protocols" % ports.get(ep.rx_name)]
                tr["trafficItem"][-1]["endpointSet"][0]["sources"] = [
                    o for o in tx_objs
                ]
                tr["trafficItem"][-1]["endpointSet"][0]["destinations"] = [
                    o for o in rx_objs
                ]
            else:
                ep = getattr(flow.tx_rx, "device")
                tr_type = devices[ep.tx_names[0]]["type"]
                source = []
                destinations = []
                scalable_sources = []
                scalable_destinations = []
                self._gen_dev_endpoint(
                    devices, ep.tx_names, source, scalable_sources
                )
                self._gen_dev_endpoint(
                    devices, ep.rx_names, destinations, scalable_destinations
                )
                if len(source) > 0:
                    tr["trafficItem"][-1]["endpointSet"][0]["sources"] = source
                if len(destinations) > 0:
                    tr["trafficItem"][-1]["endpointSet"][0][
                        "destinations"
                    ] = destinations
                if len(scalable_sources) > 0:
                    tr["trafficItem"][-1]["endpointSet"][0][
                        "scalableSources"
                    ] = scalable_sources
                if len(scalable_destinations) > 0:
                    tr["trafficItem"][-1]["endpointSet"][0][
                        "scalableDestinations"
                    ] = scalable_destinations

            tr["trafficItem"][-1]["trafficType"] = tr_type
            if tr_type == "raw":
                tr["trafficItem"][-1]["configElement"] = self.config_raw_stack(
                    tr_xpath, self._flows_packet[index]
                )
            self.traffic_index += 1
        return tr

    def config_raw_stack(self, xpath, packet):
        ce_path = "%s/configElement[1]" % xpath
        config_elem = {"xpath": ce_path, "stack": []}
        for i, header in enumerate(packet):
            stack_name = self._HEADER_TO_TYPE.get(
                self._getUhdHeader(header.parent.choice)
            )
            header_xpath = "%s/stack[@alias = '%s-%d']" % (
                ce_path,
                stack_name,
                i + 1,
            )
            self._append_header(
                header, header_xpath, config_elem["stack"], is_raw_traffic=True
            )
        return [config_elem]

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

    def copy_flow_packet(self, config):
        self._flows_packet = []
        for flow in config.flows:
            flow_packet = []
            for pkt in flow.packet:
                parent = pkt.parent.__deepcopy__(None)
                head = parent.get(parent.choice)
                head._parent = parent
                flow_packet.append(head)
            self._flows_packet.append(flow_packet)
        return

    def config(self):
        """Configure config.flows onto Ixnetwork.Traffic.TrafficItem

        CRUD
        ----
        - DELETE any TrafficItem.Name that does not exist in config.flows
        - CREATE TrafficItem for any config.flows[*].name that does not exist
        - UPDATE TrafficItem for any config.flows[*].name that exists
        """
        with Timer(self._api, "Flows configuration"):
            self._config = self._api.snappi_config
            if len(self._config.flows) == 0:
                self.remove_ixn_traffic()
                return
            self.remove_ixn_traffic()
            self.copy_flow_packet(self._config)
            ixn_traffic_item = self.get_ixn_config(self._config)[0]
            self.flows_has_latency = []
            self.flows_has_timestamp = []
            self.flows_has_loss = []
            self.latency_mode = None
            if ixn_traffic_item.get("trafficItem") is None:
                # TODO raise Exception
                return
            ixn_traffic_item = ixn_traffic_item.get("trafficItem")
            tr_json = {"traffic": {"xpath": "/traffic", "trafficItem": []}}
            for i, flow in enumerate(self._config.flows):
                tr_item = {"xpath": ixn_traffic_item[i]["xpath"]}
                if ixn_traffic_item[i].get("configElement") is None:
                    raise Exception(
                        "Endpoints are not properly configured in IxNetwork"
                    )
                ce_xpaths = [
                    {"xpath": ce["xpath"]}
                    for ce in ixn_traffic_item[i]["configElement"]
                ]
                tr_item["configElement"] = ce_xpaths
                self._configure_size(
                    tr_item["configElement"], flow.get("size", True)
                )
                self._configure_rate(
                    tr_item["configElement"], flow.get("rate", True)
                )
                hl_stream_count = len(ixn_traffic_item[i]["highLevelStream"])
                self._configure_duration(
                    tr_item["configElement"],
                    hl_stream_count,
                    flow.get("duration", True),
                )
                # tr_type = ixn_traffic_item[i]["trafficType"]
                if flow.tx_rx.choice == "device":
                    for ind, ce in enumerate(
                        ixn_traffic_item[i]["configElement"]
                    ):
                        stack = self._configure_packet(
                            ce["stack"], self._flows_packet[i]
                        )
                        tr_item["configElement"][ind]["stack"] = stack

                metrics = flow.get("metrics")
                if metrics is not None and metrics.enable is True:
                    tr_item.update(
                        self._configure_tracking(ixn_traffic_item[i])
                    )
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
                tr_json["traffic"]["trafficItem"].append(tr_item)
            self._importconfig(tr_json)

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

    def _configure_tracking(self, tr_item_json):
        """Set tracking options"""
        xpath = tr_item_json["xpath"]
        if tr_item_json.get("trafficType") == "raw":
            trackBy = ["trackingenabled0"]
        else:
            trackBy = ["trackingenabled0", "sourceDestPortPair0"]
        tracking = [{"xpath": "%s/tracking" % xpath, "trackBy": trackBy}]
        return {"tracking": tracking}

    def _configure_options(self):
        if self.isUhd is True:
            return
        enable_min_frame_size = False
        for flow in self._config.flows:
            if (
                len(flow.packet) == 1
                and flow.packet[0].parent.choice == "pfcpause"
            ):
                enable_min_frame_size = True
                break
        if self._api._traffic.EnableMinFrameSize != enable_min_frame_size:
            self._api._traffic.EnableMinFrameSize = enable_min_frame_size

    def _configure_packet(self, ixn_stack, snappi_packet):
        if len(snappi_packet) == 0:
            return
        stacks = []
        ce_path = ixn_stack[0]["xpath"].split(" = ")[0]
        snappi_stack_names = [head.parent.choice for head in snappi_packet]
        stack_names = []
        for stack in ixn_stack:
            name = stack["xpath"].split(" = ")[-1].strip("']").split("-")[0]
            if name == "fcs":
                continue
            if self._TYPE_TO_HEADER.get(name) is None:
                msg = "%s snappi header is not mapped" % name
                raise SnappiIxnException("400", msg)
            stack_names.append(name)

        for index, header in enumerate(snappi_packet):
            choice = header.parent.choice
            if choice not in stack_names:
                if choice == "vlan":
                    stack_names.insert(index, choice)
                else:
                    stack_names.append(choice)
        for index, stack in enumerate(stack_names):
            ixn_header_name = self._HEADER_TO_TYPE.get(
                self._getUhdHeader(stack)
            )
            if ixn_header_name is None:
                msg = "%s ixia header is not mapped" % ixn_header_name
                raise SnappiIxnException("400", msg)
            index = "%s-%s" % (ixn_header_name, index + 1)
            xpath = "%s = '%s']" % (ce_path, index)
            if stack in snappi_stack_names:
                ind = snappi_stack_names.index(stack)
                snappi_packet[ind]
                self._append_header(snappi_packet[ind], xpath, stacks)
            else:
                header = getattr(snappi.FlowHeader(), stack)
                self._append_header(header, xpath, stacks)
        return stacks

    def _append_header(
        self,
        snappi_header,
        xpath,
        stacks,
        insert_header=False,
        header_index=None,
        is_raw_traffic=False,
    ):
        field_map = getattr(
            self,
            "_%s" % (self._getUhdHeader(snappi_header.parent.choice).upper()),
        )
        stack_name = self._HEADER_TO_TYPE.get(
            self._getUhdHeader(snappi_header.parent.choice)
        )
        if stack_name is None:
            raise NotImplementedError(
                "%s stack is not implemented" % snappi_header.parent.choice
            )
        header = {"xpath": xpath}
        if insert_header is True and header_index is not None:
            stacks.insert(header_index, header)
        else:
            stacks.append(header)
        if field_map.get("order") is not None:
            fields = self._generate_fields(field_map, xpath)
            header["field"] = self._configure_stack_fields(
                fields, snappi_header, stacks, is_raw_traffic
            )
            header["field"] = (
                [] if header["field"] is None else header["field"]
            )
        return header

    def _generate_fields(self, field_map, xpath):
        fields = []
        for i, f in enumerate(field_map["order"]):
            if not isinstance(field_map[f], str):
                continue
            fmap = "%s-%s" % (field_map[f], i + 1)
            fields.append({"xpath": "%s/field[@alias = '%s']" % (xpath, fmap)})
        return fields

    @property
    def isUhd(self):
        return "UHD" in self._api._ixnetwork.Globals.ProductVersion

    def _getUhdHeader(self, header=None):
        if self.isUhd is True and header == "ethernetpause":
            return header + "UHD"
        return header

    def _configure_stack_fields(
        self, ixn_fields, snappi_header, stacks, is_raw_traffic=False
    ):
        fields = [{"xpath": f["xpath"]} for f in ixn_fields]
        field_names = [
            f["xpath"].split(" = ")[-1].strip("']").split("-")[0]
            for f in ixn_fields
        ]
        field_map = getattr(
            self,
            "_%s" % (self._getUhdHeader(snappi_header.parent.choice).upper()),
        )
        for field in snappi_header._TYPES:
            format_type = None
            try:
                val = field_map[field]
                if not isinstance(val, str):
                    val(
                        self,
                        fields,
                        field_names,
                        snappi_header,
                        field,
                        stacks,
                    )
                    continue
                ind = field_names.index(val)
            except Exception:
                continue
            format_type = field_map.get("convert_int_to_hex", [])
            format_type = "hex" if field in format_type else None
            auto_to_def = field_map.get("auto_to_default", [])
            auto_to_def = (
                True
                if field in auto_to_def and is_raw_traffic is True
                else False
            )
            field = snappi_header.get(field, True)
            self._config_field_pattern(
                snappi_field=field,
                field_json=fields[ind],
                format_type=format_type,
                auto_to_default=auto_to_def,
            )
        return fields

    def _config_field_pattern(
        self,
        snappi_field,
        field_json,
        format_type=None,
        active_field=False,
        auto_to_default=False,
    ):
        if snappi_field is None:
            return
        ixn_pattern = {
            "value": "singleValue",
            "values": "valueList",
            "increment": "increment",
            "decrement": "decrement",
            "auto": "auto",
            "generated": "auto",
        }

        def get_value(field_value):
            # if choice == "auto" and auto_to_default is False:
            #     return "auto"
            if format_type is None:
                return field_value
            if snappi_type == int and format_type == "hex":
                if isinstance(field_value, list):
                    field_value = ["{:x}".format(v) for v in field_value]
                else:
                    field_value = "{:x}".format(field_value)
            return field_value

        choice = snappi_field.get("choice")
        if choice is None:
            return
        snappi_type = None
        if "_TYPES" in dir(snappi_field):
            snappi_type = snappi_field._TYPES.get("value", {}).get("type")
        field_json["valueType"] = ixn_pattern[choice]

        if choice in ["value", "values", "auto"]:
            value = get_value(snappi_field.get(choice))
            if auto_to_default is True and choice == "auto":
                choice = "value"
                field_json["valueType"] = ixn_pattern[choice]
            field_json[ixn_pattern[choice]] = value

        if choice in ["increment", "decrement"]:
            obj = snappi_field.get(choice)
            field_json["startValue"] = get_value(obj.start)
            field_json["stepValue"] = get_value(obj.step)
            field_json["countValue"] = obj.count
        if choice == "generated":
            value = snappi_field.get(choice)
            if value == "good":
                choice = "auto"
            else:
                # TODO currently added some dummy value for bad generated value
                # Need to add some logic to generate bad value
                field_json["value"] = "0001"
        field_json["activeFieldChoice"] = active_field
        field_json["auto"] = True if choice == "auto" else False
        return

    def _set_default(self, ixn_field, field_choice):
        """We are setting all the field to default. Otherwise test
        is keeping the same value from previous run."""
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

    def _configure_size(self, ce_dict, size):
        """Transform frameSize flows.size to
        /traffic/trafficItem[*]/configElement[*]/frameSize"""
        if size is None:
            return
        for ce in ce_dict:
            ce["frameSize"] = {"xpath": "%s/frameSize" % ce["xpath"]}
            # ixn_frame_size = ixn_stream.FrameSize
            # args = {}
            if size.choice == "fixed":
                ce["frameSize"]["type"] = "fixed"
                ce["frameSize"]["fixedSize"] = size.fixed
            elif size.choice == "increment":
                ce["frameSize"]["type"] = "increment"
                ce["frameSize"]["incrementFrom"] = size.increment.start
                ce["frameSize"]["incrementTo"] = size.increment.end
                ce["frameSize"]["incrementStep"] = size.increment.step
            else:
                print(
                    "Warning - We need to implement this %s choice"
                    % size.choice
                )
        return

    def _configure_rate(self, ce_dict, rate):
        """Transform frameRate flows.rate to
        /traffic/trafficItem[*]/configElement[*]/frameRate"""
        if rate is None:
            return
        # ixn_frame_rate = ixn_stream.FrameRate
        # args = {}
        for ce in ce_dict:
            ce["frameRate"] = {"xpath": "%s/frameRate" % ce["xpath"]}
            value = None
            if rate.choice == "percentage":
                ce["frameRate"]["type"] = "percentLineRate"
                value = rate.get("percentage", True)
            elif rate.choice == "pps":
                ce["frameRate"]["type"] = "framesPerSecond"
                value = rate.get("pps", True)
            else:
                ce["frameRate"]["type"] = "bitsPerSecond"
                ce["frameRate"][
                    "bitRateUnitsType"
                ] = TrafficItem._BIT_RATE_UNITS_TYPE[rate.choice]
                value = rate.get(rate.choice)
            ce["frameRate"]["rate"] = value
        return

    def _configure_duration(self, ce_dict, hl_stream_count, duration):
        """Transform duration flows.duration to
        /traffic/trafficItem[*]/configElement[*]/TransmissionControl"""
        if duration is None:
            return
        # ixn_tx_control = ixn_stream.TransmissionControl
        # args = {}
        for ce in ce_dict:
            ce["transmissionControl"] = {
                "xpath": "%s/transmissionControl" % ce["xpath"]
            }
            if duration.choice == "continuous":
                ce["transmissionControl"]["type"] = "continuous"
                ce["transmissionControl"][
                    "minGapBytes"
                ] = duration.continuous.get("gap", True)
                delay = duration.continuous.get("delay", True)
                value = delay.get(delay.choice, True)
                unit = delay.choice
                if delay.choice == "microseconds":
                    value = value * 1000
                    unit = "nanoseconds"
                ce["transmissionControl"]["startDelay"] = value
                ce["transmissionControl"]["startDelayUnits"] = unit
            elif duration.choice == "fixed_packets":
                ce["transmissionControl"]["type"] = "fixedFrameCount"
                ce["transmissionControl"]["frameCount"] = (
                    duration.fixed_packets.get("packets", True)
                    / hl_stream_count
                )
                ce["transmissionControl"][
                    "minGapBytes"
                ] = duration.fixed_packets.get("gap", True)
                delay = duration.fixed_packets.get("delay", True)
                value = delay.get(delay.choice, True)
                unit = delay.choice
                if delay.choice == "microseconds":
                    value = value * 1000
                    unit = "nanoseconds"
                ce["transmissionControl"]["startDelay"] = value
                ce["transmissionControl"]["startDelayUnits"] = unit
            elif duration.choice == "fixed_seconds":
                ce["transmissionControl"]["type"] = "fixedDuration"
                ce["transmissionControl"][
                    "duration"
                ] = duration.fixed_seconds.get("seconds", True)
                ce["transmissionControl"][
                    "minGapBytes"
                ] = duration.fixed_seconds.get("gap", True)
                delay = duration.fixed_seconds.get("delay", True)
                value = delay.get(delay.choice, True)
                unit = delay.choice
                if delay.choice == "microseconds":
                    value = value * 1000
                    unit = "nanoseconds"
                ce["transmissionControl"]["startDelay"] = value
                ce["transmissionControl"]["startDelayUnits"] = unit
            elif duration.choice == "burst":
                ce["transmissionControl"]["type"] = "custom"
                ce["transmissionControl"][
                    "burstPacketCount"
                ] = duration.burst.get("packets", True)
                gap = duration.burst.get("gap", True)
                ce["transmissionControl"]["minGapBytes"] = gap
                ce["transmissionControl"]["enableInterBurstGap"] = (
                    True if gap > 0 else False
                )
                inter_burst_gap = duration.burst.get("inter_burst_gap", True)
                value = inter_burst_gap.get(inter_burst_gap.choice, True)
                unit = inter_burst_gap.choice
                if inter_burst_gap.choice == "microseconds":
                    value = value * 1000
                    unit = "nanoseconds"
                ce["transmissionControl"]["interBurstGap"] = value
                ce["transmissionControl"]["interBurstGapUnits"] = unit
                if duration.burst.get("bursts") is not None:
                    ce["transmissionControl"]["type"] = "burstFixedDuration"
                    ce["transmissionControl"][
                        "repeatBurst"
                    ] = duration.burst.bursts
        return

    def transmit(self, request):
        """Set flow transmit
        1) check set_protocol_state for device protocols
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
                glob_topo = self._api._globals.Topology.refresh()
                if glob_topo.Status == "notStarted":
                    raise Exception(
                        "Please start protocols using set_protocol_state "
                        "before start traffic"
                    )
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
        except Exception:
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

        start_states = [
            "txStopWatchExpected",
            "locked",
            "started",
            "startedWaitingForStats",
            "startedWaitingForStreams",
            "stoppedWaitingForStats",
        ]
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

        has_request_flow = True
        req_flow_names = request.get("flow_names")
        if req_flow_names is None or len(req_flow_names) == 0:
            req_flow_names = []
            has_request_flow = False
        if not isinstance(req_flow_names, list):
            msg = "Invalid format of flow_names passed {},\
                    expected list".format(
                req_flow_names
            )
            raise Exception(msg)
        req_flow_names = self._api.special_char(req_flow_names)
        # initialize result values
        flow_names = []
        flow_rows = {}
        regfilter = {"property": "name", "regex": ".*"}
        if len(req_flow_names) > 0:
            regfilter["regex"] = "^(%s)$" % "|".join(req_flow_names)
        traffic_items = self._api.select_traffic_items(
            traffic_item_filters=[regfilter]
        )
        if len(traffic_items) == 0:
            raise Exception(
                "To fetch flow metrics at least Flow should configured"
            )
        for traffic_item in traffic_items.values():
            name = traffic_item["name"]
            track_by = traffic_item["tracking"][0]["trackBy"]
            # flow.
            if len(track_by) == 0 or "trackingenabled0" not in track_by:
                continue
            flow_names.append(name)
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
                    if self._api._flow_tracking:
                        flow_rows[
                            traffic_item["name"]
                            + stream["txPortName"]
                            + rx_port_name
                        ] = flow_row
                    else:
                        flow_rows[traffic_item["name"]] = flow_row

        if len(flow_names) == 0:
            msg = """
            To fetch flow metrics at least one flow shall have metric enabled
            """
            raise Exception(msg.strip())
        diff = set(req_flow_names).difference(flow_names)
        if len(diff) > 0 and has_request_flow is True:
            raise Exception(
                "Flow metrics is not enabled on flows {}".format(
                    "".join(list(diff))
                )
            )

        flow_count = len(flow_names)
        ixn_page = self._api._ixnetwork.Statistics.View.find(
            Caption="Flow Statistics"
        ).Page
        if ixn_page.PageSize < flow_count:
            ixn_page.PageSize = flow_count
        if self._api._flow_tracking:
            table = self._api.assistant.StatViewAssistant("Flow Statistics")
            for row in table.Rows:
                name = row["Traffic Item"]
                if (
                    len(flow_names) > 0
                    and row["Traffic Item"] not in flow_names
                ):
                    continue
                if (
                    row["Traffic Item"] + row["Tx Port"] + row["Rx Port"]
                    in flow_rows
                ):
                    flow_row = flow_rows[
                        row["Traffic Item"] + row["Tx Port"] + row["Rx Port"]
                    ]
                    if (
                        self._api._ixnetwork.Traffic.TrafficItem.find(
                            Name="^" + flow_row["name"] + "$"
                        ).State
                        in start_states
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
        else:
            flow_stat = self._api.assistant.StatViewAssistant(
                "Traffic Item Statistics"
            )
            for row in flow_stat.Rows:
                name = row["Traffic Item"]
                if len(flow_names) > 0 and name not in flow_names:
                    continue
                if name in flow_rows:
                    flow_row = flow_rows[name]
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
                    if (
                        name not in self.flows_has_loss
                        and len(self.flows_has_loss) > 0
                    ):
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
                        int(float(v) * 10**9 + 0.1) * mul[i]
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
        if len(timestamp_result) > 0:
            flow_row["timestamps"] = timestamp_result

    def update_flows(self, update_flows_config):
        """
        Update the flows with property size & rate
        """
        self._validate_update_flows_config(update_flows_config)
        for flow in update_flows_config.flows:
            hl = self._api._ixnetwork.Traffic.TrafficItem.find(
                Name=flow.name
            ).HighLevelStream.find()
            self._update_size(hl, flow.size)
            self._update_rate(hl, flow.rate)

    def _validate_update_flows_config(self, update_flows_config):
        errors = []
        for flow in update_flows_config.flows:
            if flow not in self._api._config.flows._items:
                errors.append(
                    "Adding a new flow {} is not allowed in update operation".format(
                        flow.name
                    )
                )
            else:
                for i_flow in self._api._initial_flows_config._items:
                    if i_flow.name == flow.name:
                        d1 = flow.serialize(flow.DICT)
                        d2 = i_flow.serialize(i_flow.DICT)
                        error = self._compare_property(d1, d2)
                        errors.extend(error)
        if errors:
            raise SnappiIxnException(400, "{}".format(("\n").join(errors)))

    def _compare_property(self, d1, d2):
        property_errors = []
        for key in d1.keys():
            if d1[key] != d2[key]:
                property_errors.append(key)
        property_errors = [
            property_err
            + " property update is not supported on flow {}".format(d1["name"])
            for property_err in property_errors
            if property_err not in ["rate", "size"]
        ]
        return property_errors

    def _update_size(self, ixn_hl_stream, size):
        if size.choice is not None:
            if size.choice != "fixed":
                raise SnappiIxnException(
                    400,
                    "Frame size update on a started flow is not supported for {} choice".format(
                        size.choice
                    ),
                )
            ixn_hl_stream.FrameSize.FixedSize = size.fixed

    def _update_rate(self, ixn_hl_stream, rate):
        if rate.choice is None:
            return
        ixn_frame_rate = ixn_hl_stream.FrameRate
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
