from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class RoCEv2(Base):
    _RoCEv2 = {"ib_mtu": "ibMTU"}

    _MANDATE_CONFIG = {
        "initial_psn": "initialPSN",
        "virtual_address": "remoteVA",
        "remote_key": "remoteKey",
    }

    _VERB = {
        "choice": {
            "ixn_attr": "executeCommands",
            "enum_map": {
                "none": "none",
                "write": "rdmawrite",
                "write_with_immediate": "rdmawritewithimmdt",
                "send": "send",
                "send_with_immediate": "sendwithimmdt",
            },
        }
    }

    _ECN = {
        "ecn": {
            "ixn_attr": "ecnVal",
            "enum_map": {"non_ect": 0, "ect_1": 1, "ect_0": 2, "ce": 3},
        }
    }

    _IMMD_DATA = {"immediate_data": "immidtData"}

    _MESSAGE_SIZE = {
        "message_size": "messageSize",
        "message_size_unit": {
            "ixn_attr": "messageSizeUnit",
            "enum_map": {"bytes": "byte", "kb": "kb", "mb": "mb", "gb": "gb"},
        },
    }

    ecn_mapping = {"non_ect": 0, "ect_1": 1, "ect_0": 2, "ce": 3}

    def __init__(self, ngpf):
        super(RoCEv2, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)

    def config(self, device):
        self.logger.debug("Configuring RoCEv2")
        rocev2 = device.get("rocev2")
        if rocev2 is None:
            return
        stateful_flow = None
        options = None
        if hasattr(self._ngpf.api.snappi_config, "stateful_flows"):
            stateful_flow = self._ngpf.api.snappi_config.stateful_flows
        if hasattr(self._ngpf.api.snappi_config, "options"):
            options = self._ngpf.api.snappi_config.options
        self._config_ipv4_interfaces(rocev2, stateful_flow, options)
        self._config_ipv6_interfaces(rocev2, stateful_flow, options)

    def _get_interface_info(self):
        ip_types = ["ipv4", "ipv6"]
        same_dg_ips = []
        invalid_ips = []
        ethernets = self._ngpf.working_dg.get("ethernet")
        if ethernets is None:
            return same_dg_ips, invalid_ips
        for ethernet in ethernets:
            for ip_type in ip_types:
                ips = ethernet.get(ip_type)
                if ips is not None:
                    ip_names = [ip.get("name").value for ip in ips]
                    same_dg_ips.extend(ip_names)
                    if len(ips) > 1:
                        invalid_ips.extend(ip_names)
        return same_dg_ips, invalid_ips

    def _is_valid(self, ip_name):
        is_invalid = True
        same_dg_ips, invalid_ips = self._get_interface_info()
        self.logger.debug(
            "Validating %s against interface same_dg_ips : %s invalid_ips %s"
            % (ip_name, same_dg_ips, invalid_ips)
        )
        if ip_name in invalid_ips:
            self._ngpf.api.add_error(
                "Multiple IP {name} on top of name Ethernet".format(
                    name=ip_name
                )
            )
            is_invalid = False
        if len(same_dg_ips) > 0 and ip_name not in same_dg_ips:
            self._ngpf.api.add_error(
                "RoCEv2 should not configured on top of different device"
            )
            is_invalid = False
        return is_invalid

    def _config_ipv4_interfaces(
        self, rocev2, stateful_flow=None, options=None
    ):
        self.logger.debug("Configuring RoCEv2 IPv4 interfaces")
        ipv4_interfaces = rocev2.get("ipv4_interfaces")
        if ipv4_interfaces is None:
            return
        for ipv4_interface in ipv4_interfaces:
            ipv4_name = ipv4_interface.get("ipv4_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ipv4_name
            )
            if not self._is_valid(ipv4_name):
                continue
            ixn_ipv4 = self._ngpf.api.ixn_objects.get_object(ipv4_name)
            self._config_rocev2v4(
                ipv4_interface,
                ipv4_interface.get("peers"),
                ixn_ipv4,
                stateful_flow,
                options,
            )

    def _config_rocev2v4(
        self, ipv4_interface, rocev2_peers, ixn_ipv4, stateful_flow, options
    ):
        if rocev2_peers is None:
            return
        self.logger.debug("Configuring RoCEv2 Peer")
        for rocev2_peer in rocev2_peers:
            ixn_rocev2v4 = self.create_node_elemet(
                ixn_ipv4, "rocev2", rocev2_peer.get("name")
            )
            self._ngpf.set_device_info(rocev2_peer, ixn_rocev2v4)
            self.configure_multivalues(
                ipv4_interface, ixn_rocev2v4, RoCEv2._RoCEv2
            )

            # Assign Dp QP Count as number of QPs added in a peer
            ixn_rocev2v4["qpCount"] = len(rocev2_peer.qps)

            # Populate Destination IP Address
            peerIPlist = rocev2_peer.get("destination_ip_address")
            cleaned_list = [x for x in peerIPlist.split(",") if x]
            ixn_rocev2v4["peerIPList"] = cleaned_list
            self._configureFlowSettings(
                rocev2_peer, ixn_rocev2v4, stateful_flow, options
            )

    def _config_ipv6_interfaces(self, rocev2, stateful_flow, options):
        self.logger.debug("Configuring RoCEv2 IPv6 interfaces")
        ipv6_interfaces = rocev2.get("ipv6_interfaces")
        if ipv6_interfaces is None:
            return
        for ipv6_interface in ipv6_interfaces:
            ipv6_name = ipv6_interface.get("ipv6_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ipv6_name
            )
            if not self._is_valid(ipv6_name):
                continue
            ixn_ipv6 = self._ngpf.api.ixn_objects.get_object(ipv6_name)
            self._config_rocev2v6(ipv6_interface.get("peers"), ixn_ipv6)

    def _config_rocev2v6(
        self, ipv6_interface, rocev2_peers, ixn_ipv6, stateful_flow, options
    ):
        if rocev2_peers is None:
            return
        self.logger.debug("Configuring RoCEv2 Peer")
        for rocev2_peer in rocev2_peers:
            ixn_rocev2v6 = self.create_node_elemet(
                ixn_ipv6, "roce6v2", rocev2_peer.get("name")
            )
            self._ngpf.set_device_info(rocev2_peer, ixn_rocev2v6)
            self.configure_multivalues(
                rocev2_peer, ixn_rocev2v6, RoCEv2._RoCEv2
            )
            ixn_rocev2v6["qpCount"] = len(rocev2_peer.qps)
            self._configureFlowSettings(rocev2_peer, ixn_rocev2v6)

            peerIPlist = rocev2_peer.get("destination_ip_address")
            cleaned_list = [x for x in peerIPlist.split(",") if x]
            ixn_rocev2v6["peerIPList"] = cleaned_list
            self._configureFlowSettings(
                rocev2_peer, ixn_rocev2v6, stateful_flow, options
            )

    def _configureFlowSettings(
        self, rocev2_peer, ixn_rocev2, stateful_flow, options
    ):
        qp_name = ""
        ixn_flow_settings = self.create_node_elemet(ixn_rocev2, "flows")
        qps = rocev2_peer.qps
        qp_name = []
        if qps:
            # convert value to list
            source_qp_number = []
            dscp = []
            udp_source_port = []
            ecn_values = []
            for qp in qps:
                qp_name.append(qp.qp_name)
                source_qp_number.append(
                    qp.connection_type.reliable_connection.get(
                        "source_qp_number"
                    )
                )
                dscp.append(qp.connection_type.reliable_connection.get("dscp"))
                udp_source_port.append(
                    qp.connection_type.reliable_connection.get(
                        "udp_source_port"
                    )
                )
                ecn_values.append(
                    qp.connection_type.reliable_connection.get("ecn")
                )
                self.configure_multivalues(
                    qp.connection_type.reliable_connection,
                    ixn_flow_settings,
                    RoCEv2._ECN,
                )
            if (len(source_qp_number) == 1 and 2 in source_qp_number) or len(
                set(source_qp_number)
            ):
                # only 1 qp is added and default value of 2 is there then the user has not configured qp number or all the values in the list are default i.e. 2, then disable Custom QP
                ixn_flow_settings["customizeQP"] = False
            else:
                ixn_flow_settings["customizeQP"] = True
            ecn_numeric_value = [
                RoCEv2._ECN["ecn"]["enum_map"][ecn] for ecn in ecn_values
            ]
            ixn_flow_settings["customQP"] = self.multivalue(source_qp_number)
            ixn_flow_settings["dscp"] = self.multivalue(dscp)
            ixn_flow_settings["udpSourcePort"] = self.multivalue(
                udp_source_port
            )
            ixn_flow_settings["ecnVal"] = self.multivalue(ecn_numeric_value)

        rocev2s = []
        counter = 0
        found = False
        message_size = []
        message_size_unit = []
        immediate_data = []
        rocev2_verb = []
        if (
            stateful_flow is not None
            and stateful_flow.get("rocev2") is not None
        ):
            rocev2s = stateful_flow.get("rocev2")

        for rocev2 in rocev2s:
            for tx_port in rocev2.tx_ports:
                flows = tx_port.transmit_type.target_line_rate.flows
                for flow in flows:
                    if len(qp_name):
                        if flow.name in qp_name:
                            counter = counter + 1
                            # add values to list, creating a list of values to puit as Valuelist in multivalue, in order to support different values for each row
                            message_size.append(flow.get("message_size"))
                            message_size_unit.append(
                                flow.get("message_size_unit")
                            )
                            rocev2_verb.append(flow.rocev2_verb.get("choice"))
                            if (
                                flow.rocev2_verb.choice
                                == "write_with_immediate"
                            ):
                                immediate_data.append(
                                    flow.rocev2_verb.write_with_immediate.get(
                                        "immediate_data"
                                    )
                                )
                            elif (
                                flow.rocev2_verb.choice
                                == "send_with_immediate"
                            ):
                                immediate_data.append(
                                    flow.rocev2_verb.send_with_immediate.get(
                                        "immediate_data"
                                    )
                                )

                            if counter == len(qp_name):
                                # assign value to ixn node
                                ixn_flow_settings["messageSize"] = (
                                    self.multivalue(message_size)
                                )
                                mapped_units = [
                                    RoCEv2._MESSAGE_SIZE["message_size_unit"][
                                        "enum_map"
                                    ][unit]
                                    for unit in message_size_unit
                                ]
                                ixn_flow_settings["messageSizeUnit"] = (
                                    self.multivalue(mapped_units)
                                )
                                mapped_verbs = [
                                    RoCEv2._VERB["choice"]["enum_map"][verb]
                                    for verb in rocev2_verb
                                ]
                                ixn_flow_settings["executeCommands"] = (
                                    self.multivalue(mapped_verbs)
                                )
                                ixn_flow_settings["immidtData"] = (
                                    self.multivalue(immediate_data)
                                )

                                # now populate global port settings
                                if options is not None:
                                    self._populateGLobalPortSettings(options)
                                return

    def _populateGLobalPortSettings(self, options):
        perportoptions = []
        protocols = []
        ixnRocev2GlobalPortSettings = (
            self._ngpf.api._ixnetwork.Globals.Topology.find().Rocev2.find()
        )
        if options is not None and options.get("per_port_options") is not None:
            perportoptions = options.get("per_port_options")
        for perportoption in perportoptions:
            protocols = perportoption.get("protocols")
            for protocol in protocols:
                if protocol.cnp:  # meaning rocev2
                    # CNP
                    if protocol.cnp.get("choice") == "ip_dscp":
                        ixnRocev2GlobalPortSettings.CnpPriorityType.Single(
                            "handshakeprioritytypeipdscp"
                        )
                    ixnRocev2GlobalPortSettings.CnpPriorityValue.Single(
                        protocol.cnp.ip_dscp.get("value")
                    )
                    ecn_key = protocol.cnp.get("ecn_value")
                    ecn_numeric = self.ecn_mapping.get(ecn_key, None)
                    if ecn_numeric is not None:
                        ixnRocev2GlobalPortSettings.CnpEcnVal.Single(
                            ecn_numeric
                        )
                    ixnRocev2GlobalPortSettings.CnpDelayTimer.Single(
                        protocol.cnp.get("cnp_delay_timer")
                    )
                    # ACK
                    if protocol.connection_type.reliable_connection.ack:
                        if (
                            protocol.connection_type.reliable_connection.ack.get(
                                "choice"
                            )
                            == "ip_dscp"
                        ):
                            ixnRocev2GlobalPortSettings.AckPriorityType.Single(
                                "handshakeprioritytypeipdscp"
                            )
                        ixnRocev2GlobalPortSettings.AckPriorityValue.Single(
                            protocol.connection_type.reliable_connection.ack.ip_dscp.get(
                                "value"
                            )
                        )
                        ecn_key = protocol.connection_type.reliable_connection.ack.get(
                            "ecn_value"
                        )
                        ecn_numeric = self.ecn_mapping.get(ecn_key, None)
                        if ecn_numeric is not None:
                            ixnRocev2GlobalPortSettings.AckEcnVal.Single(
                                ecn_numeric
                            )
                    # NAK
                    if protocol.connection_type.reliable_connection.nak:
                        if (
                            protocol.connection_type.reliable_connection.nak.get(
                                "choice"
                            )
                            == "ip_dscp"
                        ):
                            ixnRocev2GlobalPortSettings.NakPriorityType.Single(
                                "handshakeprioritytypeipdscp"
                            )
                        ixnRocev2GlobalPortSettings.NakPriorityValue.Single(
                            protocol.connection_type.reliable_connection.nak.ip_dscp.get(
                                "value"
                            )
                        )
                        ecn_key = protocol.connection_type.reliable_connection.nak.get(
                            "ecn_value"
                        )
                        ecn_numeric = self.ecn_mapping.get(ecn_key, None)
                        if ecn_numeric is not None:
                            ixnRocev2GlobalPortSettings.NakEcnVal.Single(
                                ecn_numeric
                            )
                    # Retransmission
                    # ixnRocev2GlobalPortSettings.EnableACKTimeout.Single(protocol.connection_type.reliable_connection.get("enable_retransmission_timeout"))
                    # ixnRocev2GlobalPortSettings.AckTimeout.Single(protocol.connection_type.reliable_connection.get("retransmission_timeout_value"))
                    # ixnRocev2GlobalPortSettings.RetransRetryCount.Single(protocol.connection_type.reliable_connection.get("retransmission_retry_count"))

    def _configureTrafficParameters(
        self, rocev2_traffic, stateful_flow=None, options=None
    ):
        trafficPortConfigs = rocev2_traffic.RoceV2PortConfig.find()
        trafficflows = rocev2_traffic.RoceV2Stream.find()
        rocev2s = []
        if stateful_flow is not None:
            rocev2s = stateful_flow.get("rocev2")
        for trafficportconfig in trafficPortConfigs:
            for rocev2 in rocev2s:
                for tx_port in rocev2.tx_ports:
                    if trafficportconfig.TxPort == tx_port.port_name:
                        trafficportconfig.TargetLineRateInPercent = (
                            tx_port.transmit_type.target_line_rate.value
                        )
        if options is not None:
            for trafficportconfig in trafficPortConfigs:
                dcqcn_params = trafficportconfig.RoceV2DcqcnParams
                for dcqcn_param in dcqcn_params:
                    perportoptions = options.get("per_port_options")
                    for perportoption in perportoptions:
                        if perportoption.port_name == trafficportconfig.TxPort:
                            protocols = perportoption.get("protocols")
                            for protocol in protocols:
                                if (
                                    protocol.cnp
                                ):  # meaning rocev2 port configuration is present in script
                                    self._populateDcqcnSettings(
                                        dcqcn_param, protocol
                                    )

    def _populateDcqcnSettings(self, dcqcn_param, protocol):
        dcqcn_param.Enabled = protocol.dcqcn_settings.get("enable_dcqcn")
        dcqcn_param.AlphaG = protocol.dcqcn_settings.get("alpha_g")
        dcqcn_param.InitAlpha = protocol.dcqcn_settings.get("initial_alpha")
        dcqcn_param.AlphaUpdatePeriod = protocol.dcqcn_settings.get(
            "alpha_update_period"
        )
        dcqcn_param.RateReduceMonitorPeriod = protocol.dcqcn_settings.get(
            "rate_reduction_time_period"
        )
        dcqcn_param.InitRateOnFirstCnpReceived = protocol.dcqcn_settings.get(
            "initial_rate_after_first_cnp"
        )
        dcqcn_param.MinRateLimit = protocol.dcqcn_settings.get(
            "minimum_rate_limmit"
        )
        dcqcn_param.MaxFlowRateDecrPerStep = protocol.dcqcn_settings.get(
            "maximum_rate_decrement_at_time"
        )
        dcqcn_param.TargetRateClamp = protocol.dcqcn_settings.get(
            "clamp_target_rate"
        )
        dcqcn_param.RateIncrTimerResetPeriod = protocol.dcqcn_settings.get(
            "rate_increment_time"
        )
        dcqcn_param.ByteResetCount = protocol.dcqcn_settings.get(
            "rate_increment_byte_counter"
        )
        dcqcn_param.StageThreshold = protocol.dcqcn_settings.get(
            "rate_increment_threshold"
        )
        dcqcn_param.AdditiveIncrRate = protocol.dcqcn_settings.get(
            "additive_increment_rate"
        )
        dcqcn_param.HyperIncrRate = protocol.dcqcn_settings.get(
            "hyper_increment_rate"
        )
