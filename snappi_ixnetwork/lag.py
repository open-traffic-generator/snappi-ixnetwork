import json
from snappi_ixnetwork.timer import Timer


class Lag(object):
    """Transforms OpenAPI objects into IxNetwork objects
    - Lag to /lag
    Args
    ----
    - ixnetworkapi (Api): instance of the Api class
    """

    _ETHERNET = {
        "mac": {"ixn_attr": "mac", "default": "_default_mac"},
        "mtu": {"ixn_attr": "mtu", "default": "1500"},
    }

    _VLAN_TPID = {
        "x8100": "ethertype8100",
        "x88a8": "ethertype88a8",
        "x9100": "ethertype9100",
        "x9200": "ethertype9200",
        "x9300": "ethertype9300",
    }

    _VLAN = {
        # 'tpid' : {
        #     'ixn_attr' : 'tpid',
        #     'default' : 'ethertype8100',
        #     'enum_map' : _VLAN_TPID
        # },
        "priority": {"ixn_attr": "priority", "default": "0"},
        "vlanId": {"ixn_attr": "vlanId", "default": "1"},
    }

    _LACP = {
        "actor_key": {"ixn_attr": "actorKey", "default": "1"},
        "actor_port_number": {"ixn_attr": "actorPortNumber", "default": "1"},
        "actor_port_priority": {
            "ixn_attr": "actorPortPriority",
            "default": "1",
        },
        "actor_system_id": {
            "ixn_attr": "actorSystemId",
            "default": "_default_system_id",
        },
        "actor_system_priority": {
            "ixn_attr": "actorSystemPriority",
            "default": "1",
        },
        "lacpdu_periodic_time_interval": {
            "ixn_attr": "lacpduPeriodicTimeInterval",
            "default": "0",
        },
        "lacpdu_timeout": {"ixn_attr": "lacpduTimeout", "default": "0"},
        "actor_activity": {"ixn_attr": "lacpActivity", "default": "active"},
    }

    _STATIC = {"lag_id": {"ixn_attr": "lagId", "default": "1"}}

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._lag_ports = {}

    def config(self):
        """Transform config.ports into Ixnetwork.Vport
        1) delete any vport that is not part of the config
        2) create a vport for every config.ports[] that is not present in IxNetwork
        3) set config.ports[].location to /vport -location using resourcemanager
        4) set /vport/l1Config/... properties using the corrected /vport -type
        5) connectPorts to use new l1Config settings and clearownership
        """
        self._resource_manager = self._api._ixnetwork.ResourceManager
        self._ixn_lag = self._api._lag
        self._lag_ports = {}
        self._lags_config = self._api.snappi_config.lags
        with Timer(self._api, "Lag Configuration"):
            self._delete_lags()
            if len(self._lags_config) == 0:
                return
            self._create_lags()
        with Timer(self._api, "Lag Ethernet Configuration"):
            self._ethernet_config()
        with Timer(self._api, "Lag Protocol Configuration"):
            self._protocol_config()

    def _import(self, imports):
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False
            )
            for item in errata:
                self._api.warning(item)
            return len(errata) == 0
        return True

    def _delete_lags(self):
        """Delete any Lags from the api server that do not exist in the new config"""
        self._api._remove(self._ixn_lag, self._lags_config)

    def _select_lags(self):
        payload = {
            "selects": [
                {
                    "from": "/",
                    "properties": [],
                    "children": [
                        {"child": "lag", "properties": ["name"], "filters": []}
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        lags = {}
        if "lag" in results[0]:
            for lag in results[0]["lag"]:
                lags[lag["name"]] = lag
        return lags

    def _select_vports(self):
        """Select all vports.
        Return them in a dict keyed by vport name.
        """
        payload = {
            "selects": [
                {
                    "from": "/",
                    "properties": [],
                    "children": [
                        {
                            "child": "vport",
                            "properties": [
                                "name",
                            ],
                            "filters": [],
                        }
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        vports = {}
        if "vport" in results[0]:
            for vport in results[0]["vport"]:
                vports[vport["name"]] = vport
        return vports

    def _get_vports(self, ixn_vports, ports):
        vports = []
        for port in ports:
            if port.port_name not in ixn_vports:
                raise Exception("Port {0} is not available".format(port.name))
            vports.append(ixn_vports[port.port_name]["xpath"])
        return vports

    def _create_lags(self):
        """Add any Lags to the api server that do not already exist"""
        self._ixn_lag.find()
        existing_lags = [ixn_lag.Name for ixn_lag in self._ixn_lag]
        for lag in self._lags_config:
            self._lag_ports[lag.name] = lag.ports
            if lag.name not in existing_lags:
                self._ixn_lag.add(Name=lag.name)
        imports = []
        ixn_vports = self._select_vports()
        ixn_lags = self._select_lags()
        for name, ixn_lag in ixn_lags.items():
            self._api.ixn_objects[name] = ixn_lag["href"]
            lag_import = {
                "xpath": ixn_lag["xpath"],
                "vports": self._get_vports(ixn_vports, self._lag_ports[name]),
            }
            imports.append(lag_import)
        self._import(imports)

    def _set_multivalue(self, source, attribute, value):
        xpath = "/multivalue[@source = '{0} {1}']".format(source, attribute)
        if isinstance(value, list):
            return {"xpath": "{0}/valueList".format(xpath), "values": value}
        else:
            return {"xpath": "{0}/singleValue".format(xpath), "value": value}

    def _ethernet_config(self):
        imports = []
        ixn_lags = self._select_lags()
        for name, ports in self._lag_ports.items():
            ether_xpath = "{0}/protocolStack/ethernet[1]".format(
                ixn_lags[name]["xpath"]
            )
            ixn_lag = self._ixn_lag.find(
                Name="^%s$" % self._api.special_char(name)
            )
            ixn_proto_stack = ixn_lag.ProtocolStack.find()
            if len(ixn_proto_stack) == 0:
                ixn_proto_stack = ixn_lag.ProtocolStack.add()[0]
            ixn_proto_stack.Multiplier = 1
            for eth_attr in Lag._ETHERNET:
                attr_values = self._configure_attribute(
                    eth_attr, Lag._ETHERNET, ports, "ethernet"
                )
                imports.append(
                    self._set_multivalue(
                        ether_xpath,
                        attr_values.ixn_attribute,
                        attr_values.config_value,
                    )
                )
            vlans = self._process_vlans(ports)
            if len(vlans) > 0:
                if len(vlans) > 0:
                    imports.append(
                        self._set_multivalue(ether_xpath, "enableVlans", True)
                    )
                    imports.append(
                        {"xpath": ether_xpath, "vlanCount": len(vlans)}
                    )

                for idx, vlan in enumerate(vlans):
                    for vlan_attr in Lag._VLAN:
                        attr_values = self._configure_attribute(
                            vlan_attr, Lag._VLAN, vlan
                        )
                        vlan_xpath = "{0}/vlan[{1}]".format(
                            ether_xpath, idx + 1
                        )
                        imports.append(
                            self._set_multivalue(
                                vlan_xpath,
                                attr_values.ixn_attribute,
                                attr_values.config_value,
                            )
                        )
        self._import(imports)

    def _protocol_config(self):
        imports = []
        ixn_lags = self._select_lags()
        for name, ports in self._lag_ports.items():
            ixn_lag = self._ixn_lag.find(
                Name="^%s$" % self._api.special_char(name)
            )
            ixn_eth = ixn_lag.ProtocolStack.find().Ethernet.find()
            ixn_lacp = ixn_eth.Lagportlacp.find()
            ixn_static = ixn_eth.Lagportstaticlag.find()
            choice = None
            protocols = []
            for port in ports:
                protocol = port.protocol
                if choice is None:
                    choice = protocol.choice
                elif choice != protocol.choice:
                    raise Exception(
                        "Please configure same protocol "
                        "[static, lacp] within same Lag ports"
                    )
                if choice == "lacp":
                    protocol.lacp.actor_system_id = (
                        protocol.lacp.actor_system_id.replace(":", " ")
                    )
                protocols.append(protocol)
            if choice is None:
                if len(ixn_static) > 0:
                    ixn_static.Active.Single(False)
                if len(ixn_lacp) > 0:
                    ixn_lacp.Active.Single(False)
                return
            if choice == "lacp":
                if len(ixn_static) > 0:
                    ixn_static.remove()
                lacp_xpath = (
                    "{0}/protocolStack/ethernet[1]/lagportlacp[1]".format(
                        ixn_lags[name]["xpath"]
                    )
                )
                imports.append(
                    self._set_multivalue(lacp_xpath, "active", True)
                )
                for lacp_attr in Lag._LACP:
                    attr_values = self._configure_attribute(
                        lacp_attr, Lag._LACP, protocols, choice
                    )
                    imports.append(
                        self._set_multivalue(
                            lacp_xpath,
                            attr_values.ixn_attribute,
                            attr_values.config_value,
                        )
                    )
            else:
                if len(ixn_lacp) > 0:
                    ixn_lacp.remove()
                static_xpath = (
                    "{0}/protocolStack/ethernet[1]/lagportstaticlag[1]".format(
                        ixn_lags[name]["xpath"]
                    )
                )
                imports.append(
                    self._set_multivalue(static_xpath, "active", True)
                )
                for static_attr in Lag._STATIC:
                    attr_values = self._configure_attribute(
                        static_attr, Lag._STATIC, protocols, choice
                    )
                    imports.append(
                        self._set_multivalue(
                            static_xpath,
                            attr_values.ixn_attribute,
                            attr_values.config_value,
                        )
                    )

        self._import(imports)

    def _process_vlans(self, ports):
        vlan_count = -1
        vlan_list = []
        for port in ports:
            vlans = port.ethernet.vlans
            if vlan_count == -1:
                vlan_count = len(vlans)
                for i in range(len(vlans)):
                    vlan_list.append([vlans[i]])
            elif vlan_count == len(vlans):
                for i in range(len(vlans)):
                    vlan_list[i].append(vlans[i])
            else:
                raise Exception("Please configure equal numbers of VLANs")
        return vlan_list

    def _configure_attribute(self, attr, mapper, parent_list, obj_name=None):
        attr_values = ProtocolAttributes()
        attr_mapper = mapper[attr]
        ixn_attr = attr_mapper["ixn_attr"]
        default_value = attr_mapper["default"]
        enum_map = attr_mapper.get("enum_map")
        default_obj = getattr(self, default_value, None)
        attr_values.ixn_attribute = ixn_attr
        for parent in parent_list:
            if obj_name is not None:
                parent = getattr(parent, obj_name, None)
            config_value = getattr(parent, attr, None)
            if config_value is not None:
                if enum_map is None:
                    attr_values.config_value = str(config_value)
                else:
                    attr_values.config_value = enum_map[str(config_value)]
            elif default_obj is None:
                attr_values.config_value = default_value
            else:
                attr_values.config_value = default_obj()
        return attr_values

    def _select_protcols(self, lag_href):
        payload = {
            "selects": [
                {
                    "from": lag_href,
                    "properties": [],
                    "children": [
                        {
                            "child": "protocolStack",
                            "properties": ["*"],
                            "filters": [],
                        },
                        {
                            "child": "lagMode",
                            "properties": ["*"],
                            "filters": [],
                        },
                    ],
                    "inlines": [],
                }
            ]
        }
        url = "%s/operations/select?xpath=true" % self._api._ixnetwork.href
        results = self._api._ixnetwork._connection._execute(url, payload)
        lags = {}
        if "lag" in results[0]:
            for lag in results[0]["lag"]:
                lags[lag["name"]] = lag
        return lags

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

    def results(self, request):
        """Return port results"""
        if request.column_names is None:
            self._column_names = []
        else:
            self._column_names = request.column_names
        port_rows = {}
        for vport in self._api.select_vports().values():
            port_row = {}
            self._set_result_value(port_row, "name", vport["name"])
            location = vport["location"]
            if vport["connectionState"].startswith("connectedLink") is True:
                location += ";connected"
            elif len(location) > 0:
                location += ";" + vport["connectionState"]
            else:
                location = vport["connectionState"]
            self._set_result_value(port_row, "location", location)
            self._set_result_value(
                port_row,
                "link",
                "up"
                if vport["connectionState"] == "connectedLinkUp"
                else "down",
            )
            self._set_result_value(port_row, "capture", "stopped")
            port_rows[vport["name"]] = port_row
        try:
            table = self._api.assistant.StatViewAssistant("Port Statistics")
            for row in table.Rows:
                port_row = port_rows[row["Port Name"]]
                self._set_result_value(
                    port_row, "frames_tx", row["Frames Tx."], int
                )
                self._set_result_value(
                    port_row, "frames_rx", row["Valid Frames Rx."], int
                )
                self._set_result_value(
                    port_row, "frames_tx_rate", row["Frames Tx. Rate"], float
                )
                self._set_result_value(
                    port_row,
                    "frames_rx_rate",
                    row["Valid Frames Rx. Rate"],
                    float,
                )
                self._set_result_value(
                    port_row, "bytes_tx", row["Bytes Tx."], int
                )
                self._set_result_value(
                    port_row, "bytes_rx", row["Bytes Rx."], int
                )
                self._set_result_value(
                    port_row, "bytes_tx_rate", row["Bytes Tx. Rate"], float
                )
                self._set_result_value(
                    port_row, "bytes_rx_rate", row["Bytes Rx. Rate"], float
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_0_frames_rx",
                    row["Rx Pause Priority Group 0 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_1_frames_rx",
                    row["Rx Pause Priority Group 1 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_2_frames_rx",
                    row["Rx Pause Priority Group 2 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_3_frames_rx",
                    row["Rx Pause Priority Group 3 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_4_frames_rx",
                    row["Rx Pause Priority Group 4 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_5_frames_rx",
                    row["Rx Pause Priority Group 5 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_6_frames_rx",
                    row["Rx Pause Priority Group 6 Frames"],
                    int,
                )
                self._set_result_value(
                    port_row,
                    "pfc_class_7_frames_rx",
                    row["Rx Pause Priority Group 7 Frames"],
                    int,
                )
        except:
            pass
        return port_rows.values()


class ProtocolAttributes(object):
    def __init__(self):
        self._ixn_attr = None
        self._config_value = []

    @property
    def ixn_attribute(self):
        return self._ixn_attr

    @ixn_attribute.setter
    def ixn_attribute(self, value):
        self._ixn_attr = value

    @property
    def config_value(self):
        return self._config_value

    @config_value.setter
    def config_value(self, value):
        self._config_value.append(value)
