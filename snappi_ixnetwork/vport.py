import json
import time
import re
from snappi_ixnetwork.timer import Timer


class Vport(object):
    """Transforms OpenAPI objects into IxNetwork objects

    Args
    ----
    - ixnetworkapi (Api): instance of the Api class

    Transformations
    ---------------
    - /components/schemas/Port to /vport
    - /components/schemas/Layer1 to /vport/l1Config/...

    Process
    -------
    - Remove any vports that are not in the config.ports
    - Add any vports that are in the config.ports
    - If the location of the config.ports.location is different than the
      the /vport -connectedTo property set it to None
    - If the config.ports.location is None don't connect the ports
      else connect the port, get the vport type, set the card mode based on the
      config.layer1.speed

    Notes
    -----
    - Uses resourcemanager to set the vport location and l1Config as it is the
      most efficient way. DO NOT use the AssignPorts API as it is too slow.
    - Only setup l1Config if location is connected.
    - Given a connected location and speed the vport -type, card resource mode
      and l1Config sub node are derived.

    """

    _SPEED_MAP = {
        "speed_400_gbps": "speed400g",
        "speed_200_gbps": "speed200g",
        "speed_100_gbps": "speed100g",
        "speed_50_gbps": "speed50g",
        "speed_40_gbps": "speed40g",
        "speed_25_gbps": "speed25g",
        "speed_10_gbps": "speed10g",
        "speed_1_gbps": "speed1000",
        "speed_100_fd_mbps": "speed100fd",
        "speed_100_hd_mbps": "speed100hd",
        "speed_10_fd_mbps": "speed10fd",
        "speed_10_hd_mbps": "speed10hd",
    }
    _VM_SPEED_MAP = {
        "speed_400_gbps": "speed400g",
        "speed_200_gbps": "speed200g",
        "speed_100_gbps": "speed100g",
        "speed_90_gbps": "speed90g",
        "speed_80_gbps": "speed80g",
        "speed_70_gbps": "speed70g",
        "speed_60_gbps": "speed60g",
        "speed_50_gbps": "speed50g",
        "speed_40_gbps": "speed40g",
        "speed_30_gbps": "speed30g",
        "speed_25_gbps": "speed25g",
        "speed_20_gbps": "speed20g",
        "speed_10_gbps": "speed10g",
        "speed_9_gbps": "speed9000",
        "speed_8_gbps": "speed8000",
        "speed_7_gbps": "speed7000",
        "speed_6_gbps": "speed6000",
        "speed_5_gbps": "speed5000",
        "speed_4_gbps": "speed4000",
        "speed_3_gbps": "speed3000",
        "speed_2_gbps": "speed2000",
        "speed_1_gbps": "speed1000",
        "speed_100_mbps": "speed100",
        "speed_100_fd_mbps": "speed100",
        "speed_100_hd_mbps": "speed100",
        "speed_10_fd_mbps": "speed100",
        "speed_10_hd_mbps": "speed100",
    }

    _SPEED_MODE_MAP = {
        "speed_1_gbps": "normal",
        "speed_10_gbps": "tengig",
        "speed_25_gbps": "twentyfivegig",
        "speed_40_gbps": "fortygig",
        "speed_50_gbps": "fiftygig",
        "speed_100_gbps": "^(?!.*(twohundredgig|fourhundredgig)).*hundredgig.*$",
        "speed_200_gbps": "twohundredgig",
        "speed_400_gbps": "fourhundredgig",
    }

    _ADVERTISE_MAP = {
        "advertise_one_thousand_mbps": "speed1000",
        "advertise_one_hundred_fd_mbps": "speed100fd",
        "advertise_one_hundred_hd_mbps": "speed100hd",
        "advertise_ten_fd_mbps": "speed10fd",
        "advertise_ten_hd_mbps": "speed10hd",
    }
    _FLOW_CONTROL_MAP = {
        "ieee_802_1qbb": "ieee802.1Qbb",
        "ieee_802_3x": "ieee802.3x",
    }

    _RESULT_COLUMNS = [
        ("frames_tx", "Frames Tx.", int),
        ("frames_rx", "Valid Frames Rx.", int),
        ("frames_tx_rate", "Frames Tx. Rate", float),
        ("frames_rx_rate", "Valid Frames Rx. Rate", float),
        ("bytes_tx", "Bytes Tx.", int),
        ("bytes_rx", "Bytes Rx.", int),
        ("bytes_tx_rate", "Bytes Tx. Rate", float),
        ("bytes_rx_rate", "Bytes Rx. Rate", float),
        # ('pfc_class_0_frames_rx', 'Rx Pause Priority Group 0 Frames', int),
        # ('pfc_class_1_frames_rx', 'Rx Pause Priority Group 1 Frames', int),
        # ('pfc_class_2_frames_rx', 'Rx Pause Priority Group 2 Frames', int),
        # ('pfc_class_3_frames_rx', 'Rx Pause Priority Group 3 Frames', int),
        # ('pfc_class_4_frames_rx', 'Rx Pause Priority Group 4 Frames', int),
        # ('pfc_class_5_frames_rx', 'Rx Pause Priority Group 5 Frames', int),
        # ('pfc_class_6_frames_rx', 'Rx Pause Priority Group 6 Frames', int),
        # ('pfc_class_7_frames_rx', 'Rx Pause Priority Group 7 Frames', int),
    ]

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._layer1_check = []

    def config(self):
        """Transform config.ports into Ixnetwork.Vport
        1) delete any vport that is not part of the config
        2) create a vport for every config.ports[] not present in IxNetwork
        3) set config.ports[].location to /vport -location or -connectedTo
        4) set /vport/l1Config/... properties using the corrected /vport -type
        5) connectPorts to use new l1Config settings and clearownership
        """
        self._resource_manager = self._api._ixnetwork.ResourceManager
        self._ixn_vport = self._api._vport
        self._layer1_check = []
        with Timer(self._api, "Ports configuration"):
            self._delete_vports()
            self._create_vports()
        with Timer(self._api, "Captures configuration"):
            self._api.capture.config()
        with Timer(self._api, "Location configuration"):
            self._set_location()
        with Timer(self._api, "Layer1 configuration"):
            self._set_layer1()

    def set_link_state(self, link_state):
        with Timer(self._api, "Link State operation"):
            payload = {
                "arg1": [],
                "arg2": link_state.state,
            }
            for port_name in link_state.port_names:
                payload["arg1"].append(self._api.get_ixn_href(port_name))
            url = "%s/vport/operations/linkupdn" % self._api._ixnetwork.href
            self._api._request("POST", url, payload)

    def _import(self, imports):
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False
            )
            for item in errata:
                self._api.warning(item)
            return len(errata) == 0
        return True

    def _delete_vports(self):
        """Delete any vports from the api server that do not exist in the new config"""
        self._api._remove(self._ixn_vport, self._api.snappi_config.ports)

    def _create_vports(self):
        """Add any vports to the api server that do not already exist"""
        vports = self._api.select_vports()
        imports = []
        for port in self._api.snappi_config.ports:
            if port.name not in vports.keys():
                index = len(vports) + len(imports) + 1
                vport_import = {
                    "xpath": "/vport[%i]" % index,
                    "name": port.name,
                    "rxMode": "captureAndMeasure",
                    "txMode": "interleaved",
                }
                location = port.get("location")
                if location is None:
                    vport_import["connectedTo"] = location
                    port.location = None
                imports.append(vport_import)
        self._import(imports)
        for name, vport in self._api.select_vports().items():
            self._api.ixn_objects[name] = vport["href"]

    def _add_hosts(self, HostReadyTimeout):
        chassis = self._api._ixnetwork.AvailableHardware.Chassis
        add_addresses = []
        check_addresses = []
        for port in self._api.snappi_config.ports:
            location = port.get("location")
            if location is not None:
                location_info = self._api.parse_location_info(location)
                chassis_address = location_info.chassis_info
                chassis.find(Hostname="^%s$" % chassis_address)
                if len(chassis) == 0:
                    add_addresses.append(chassis_address)
                check_addresses.append(chassis_address)
        add_addresses = set(add_addresses)
        check_addresses = set(check_addresses)
        if len(add_addresses) > 0:
            with Timer(
                self._api, "Add location hosts [%s]" % ", ".join(add_addresses)
            ):
                for add_address in add_addresses:
                    chassis.add(Hostname=add_address)
        if len(check_addresses) > 0:
            with Timer(
                self._api,
                "Location hosts ready [%s]" % ", ".join(check_addresses),
            ):
                start_time = time.time()
                while True:
                    chassis.find(
                        Hostname="^(%s)$" % "|".join(check_addresses),
                        State="^ready$",
                    )
                    if len(chassis) == len(check_addresses):
                        break
                    if time.time() - start_time > HostReadyTimeout:
                        raise RuntimeError(
                            "After %s seconds, not all location hosts [%s] are reachable"
                            % (HostReadyTimeout, ", ".join(check_addresses))
                        )
                    time.sleep(2)

    def _set_location(self):
        location_supported = True
        try:
            self._api._ixnetwork._connection._options(
                self._api._ixnetwork.href + "/locations"
            )
        except Exception:
            location_supported = False

        self._add_hosts(60)
        with Timer(self._api, "Aggregation mode speed change"):
            layer1_check = self._api.resource_group.set_group()
            self._layer1_check.extend(layer1_check)
        vports = self._api.select_vports()
        locations = []
        imports = []
        clear_locations = []
        for port in self._api.snappi_config.ports:
            vport = vports[port.name]
            location = port.get("location")

            if location_supported is True:
                if vport["location"] == location and vport[
                    "connectionState"
                ].startswith("connectedLink"):
                    continue
            else:
                if len(vport["connectedTo"]) > 0 and vport[
                    "connectionState"
                ].startswith("connectedLink"):
                    continue

            self._api.ixn_objects[port.name] = vport["href"]
            vport = {"xpath": vports[port.name]["xpath"]}
            if location_supported is True:
                vport["location"] = location
            else:
                if location is not None:
                    xpath = self._api.select_chassis_card_port(location)
                    vport["connectedTo"] = xpath
                else:
                    vport["connectedTo"] = ""
            imports.append(vport)
            if location is not None and len(location) > 0:
                clear_locations.append(location)
                locations.append(port.name)
        if len(locations) == 0:
            return
        self._clear_ownership(clear_locations)
        with Timer(self._api, "Location connect [%s]" % ", ".join(locations)):
            self._import(imports)
        with Timer(
            self._api, "Location state check [%s]" % ", ".join(locations)
        ):
            self._api._vport.find(ConnectionState="^(?!connectedLink).*$")
            if len(self._api._vport) > 0:
                self._api._vport.ConnectPorts()
            start = time.time()
            timeout = 10
            while True:
                self._api._vport.find(
                    Name="^(%s)$"
                    % "|".join(self._api.special_char(locations)),
                    ConnectionState="^connectedLink",
                )
                if len(self._api._vport) == len(locations):
                    break
                if time.time() - start > timeout:
                    unreachable = []
                    self._api._vport.find(
                        ConnectionState="^(?!connectedLink).*$"
                    )
                    for vport in self._api._vport:
                        unreachable.append(
                            "%s [%s: %s]"
                            % (
                                vport.Name,
                                vport.ConnectionState,
                                vport.ConnectionStatus,
                            )
                        )
                    raise RuntimeError(
                        "After %s seconds, %s are unreachable"
                        % (timeout, ", ".join(unreachable))
                    )
                time.sleep(2)
            for vport in self._api._vport.find(
                ConnectionState="^(?!connectedLinkUp).*$"
            ):
                self._api.warning(
                    "%s %s" % (vport.Name, vport.ConnectionState)
                )

    def _set_layer1(self):
        """Set the /vport/l1Config/... properties
        This should only happen if the vport connectionState is connectedLink...
        as it determines the ./l1Config child node.
        """
        layer1_config = self._api.snappi_config.get("layer1")
        if layer1_config is None:
            return
        if len(layer1_config) == 0:
            return
        reset_auto_negotiation = dict()
        # set and commit the card resource mode
        vports = self._api.select_vports()
        imports = []
        for layer1 in layer1_config:
            for port_name in layer1.port_names:
                self._set_card_resource_mode(
                    vports[port_name], layer1, imports
                )
        if self._import(imports) is False:
            # WARNING: this retry is because no reasonable answer as to why
            # changing card mode periodically fails with this opaque message
            # 'Releasing ownership on ports failed.'
            self._api.info("Retrying card resource mode change")
            self._import(imports)
        # set the vport type
        imports = []
        for layer1 in layer1_config:
            for port_name in layer1.port_names:
                self._set_vport_type(vports[port_name], layer1, imports)
        self._import(imports)
        vports = self._api.select_vports()
        # set the remainder of l1config properties
        imports = []
        for layer1 in layer1_config:
            for port_name in layer1.port_names:
                self._set_l1config_properties(
                    vports[port_name], layer1, imports
                )
        self._import(imports)
        # Due to dependency attribute (ieeeL1Defaults)
        # reset enableAutoNegotiation
        imports = []
        for layer1 in layer1_config:
            for port_name in layer1.port_names:
                vport = vports[port_name]
                if (
                    port_name in reset_auto_negotiation
                    and reset_auto_negotiation[port_name]
                ):
                    self._reset_auto_negotiation(vport, layer1, imports)
        self._import(imports)

    def _set_l1config_properties(self, vport, layer1, imports):
        """Set vport l1config properties"""
        if vport["connectionState"] not in [
            "connectedLinkUp",
            "connectedLinkDown",
        ]:
            return
        self._set_fcoe(vport, layer1, imports)
        self._import(imports)

        self._set_auto_negotiation(vport, layer1, imports)

    def _set_card_resource_mode(self, vport, layer1, imports):
        """If the card has an aggregation mode set it according to the speed"""
        if (
            vport["connectionState"]
            not in ["connectedLinkUp", "connectedLinkDown"]
            or layer1.name in self._layer1_check
        ):
            return

        aggregation_mode = None
        if layer1.speed in Vport._SPEED_MODE_MAP:
            card = self._api.select_chassis_card(vport)
            mode = Vport._SPEED_MODE_MAP[layer1.speed]
            for available_mode in card["availableModes"]:
                if re.search(mode, available_mode.lower()) is not None:
                    aggregation_mode = available_mode
                    break
        if (
            aggregation_mode is not None
            and aggregation_mode != card["aggregationMode"]
        ):
            self._api.info(
                "Setting %s to resource mode %s"
                % (card["description"], aggregation_mode)
            )
            imports.append(
                {"xpath": card["xpath"], "aggregationMode": aggregation_mode}
            )

    def _set_auto_negotiation(self, vport, layer1, imports):
        if layer1.speed.endswith("_mbps") or layer1.speed == "speed_1_gbps":
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
        flow_control = layer1.get("flow_control")
        if flow_control is not None:
            fcoe = True
        vport_type = vport["type"]
        elegible_fcoe_vport_types = [
            "ethernet",
            "tenGigLan",
            "fortyGigLan",
            "tenGigWan",
            "hundredGigLan",
            "tenFortyHundredGigLan",
            "novusHundredGigLan",
            "novusTenGigLan",
            "krakenFourHundredGigLan",
            "aresOneFourHundredGigLan",
            "starFourHundredGigLan",
        ]
        if fcoe is True and vport_type in elegible_fcoe_vport_types:
            vport_type = vport_type + "Fcoe"
        if fcoe is False and vport_type.endswith("Fcoe"):
            vport_type = vport_type.replace("Fcoe", "")
        if vport_type != vport["type"]:
            imports.append(
                {
                    "xpath": vport["xpath"] + "/l1Config",
                    "currentType": vport_type,
                }
            )
        return vport_type

    def _set_ethernet_auto_negotiation(self, vport, layer1, imports):
        advertise = []
        if layer1.speed == "speed_1_gbps":
            advertise.append(
                Vport._ADVERTISE_MAP["advertise_one_thousand_mbps"]
            )
        if layer1.speed == "speed_100_fd_mbps":
            advertise.append(
                Vport._ADVERTISE_MAP["advertise_one_hundred_fd_mbps"]
            )
        if layer1.speed == "speed_100_hd_mbps":
            advertise.append(
                Vport._ADVERTISE_MAP["advertise_one_hundred_hd_mbps"]
            )
        if layer1.speed == "speed_10_fd_mbps":
            advertise.append(Vport._ADVERTISE_MAP["advertise_ten_fd_mbps"])
        if layer1.speed == "speed_10_hd_mbps":
            advertise.append(Vport._ADVERTISE_MAP["advertise_ten_hd_mbps"])
        proposed_import = {
            "xpath": vport["xpath"]
            + "/l1Config/"
            + vport["type"].replace("Fcoe", ""),
            "speed": self._get_speed(vport, layer1),
            "media": layer1.get("media", with_default=True),
            "autoNegotiate": layer1.get("auto_negotiate", with_default=True),
            "speedAuto": advertise,
        }
        self._add_l1config_import(vport, proposed_import, imports)

    def _add_l1config_import(self, vport, proposed_import, imports):
        type = vport["type"].replace("Fcoe", "")
        l1config = vport["l1Config"][type]
        key_to_remove = []
        for key in proposed_import:
            if key == "xpath":
                continue
            if key not in l1config or l1config[key] == proposed_import[key]:
                key_to_remove.append(key)
        # add this constrain due to handle some specific use case (1G to 10G)
        if "speed" in key_to_remove and "speedAuto" not in key_to_remove:
            key_to_remove.remove("speed")
        for key in key_to_remove:
            proposed_import.pop(key)
        if len(proposed_import) > 0:
            imports.append(proposed_import)

    def _set_gigabit_auto_negotiation(self, vport, layer1, imports):
        advertise = []
        advertise.append(
            Vport._SPEED_MAP[layer1.get("speed", with_default=True)]
        )
        auto_field_name = "enableAutoNegotiation"
        if re.search("novustengiglan", vport["type"].lower()) is not None:
            auto_field_name = "autoNegotiate"
        # Due to ieeeL1Defaults dependency
        ieee_media_defaults = {
            "xpath": vport["xpath"]
            + "/l1Config/"
            + vport["type"].replace("Fcoe", ""),
            "ieeeL1Defaults": layer1.get(
                "ieee_media_defaults", with_default=True
            ),
        }
        self._add_l1config_import(vport, ieee_media_defaults, imports)
        auto_negotiation = layer1.get("auto_negotiation", with_default=True)
        rs_fec = auto_negotiation.get("rs_fec", with_default=True)
        link_training = auto_negotiation.get(
            "link_training", with_default=True
        )
        auto_negotiate = layer1.get("auto_negotiate", with_default=True)
        proposed_import = {
            "xpath": vport["xpath"]
            + "/l1Config/"
            + vport["type"].replace("Fcoe", ""),
            "speed": Vport._SPEED_MAP[layer1.speed],
            "{0}".format(auto_field_name): False
            if auto_negotiate is None
            else auto_negotiate,
            "enableRsFec": False if rs_fec is None else rs_fec,
            "linkTraining": False if link_training is None else link_training,
            "speedAuto": advertise,
        }
        proposed_import["media"] = layer1.get("media", with_default=True)
        self._add_l1config_import(vport, proposed_import, imports)

    def _get_speed(self, vport, layer1):
        if vport["type"] == "ethernetvm":
            return Vport._VM_SPEED_MAP[layer1.speed]
        else:
            return Vport._SPEED_MAP[layer1.speed]

    def _reset_auto_negotiation(self, vport, layer1, imports):
        if (
            layer1.speed.endswith("_mbps") is False
            and layer1.speed != "speed_1_gbps"
        ):
            imports.append(
                {
                    "xpath": vport["xpath"]
                    + "/l1Config/"
                    + vport["type"].replace("Fcoe", ""),
                    "enableAutoNegotiation": layer1.get(
                        "auto_negotiate", with_default=True
                    ),
                }
            )

    def _set_fcoe(self, vport, layer1, imports):
        flow_control = layer1.get("flow_control")
        if flow_control is None:
            return
        directed_address = flow_control.get(
            "directed_address", with_default=True
        )
        directed_address = "".join(directed_address.split(":"))
        l1_xpath = "%s/l1Config/%s" % (
            vport["xpath"],
            vport["type"].replace("Fcoe", ""),
        )
        imports.append(
            {"xpath": l1_xpath, "flowControlDirectedAddress": directed_address}
        )
        xpath = "%s/l1Config/%s/fcoe" % (
            vport["xpath"],
            vport["type"].replace("Fcoe", ""),
        )
        fcoe = {
            "xpath": xpath,
            "flowControlType": Vport._FLOW_CONTROL_MAP[flow_control.choice],
        }
        if flow_control.choice == "ieee_802_1qbb":
            pfc = flow_control.get("ieee_802_1qbb", with_default=True)
            pfc_delay = pfc.get("pfc_delay", with_default=True)
            fcoe["enablePFCPauseDelay"] = False if pfc_delay == 0 else True
            fcoe["pfcPauseDelay"] = pfc_delay
            fcoe["pfcPriorityGroups"] = [
                -1 if pfc.pfc_class_0 is None else pfc.pfc_class_0,
                -1 if pfc.pfc_class_1 is None else pfc.pfc_class_1,
                -1 if pfc.pfc_class_2 is None else pfc.pfc_class_2,
                -1 if pfc.pfc_class_3 is None else pfc.pfc_class_3,
                -1 if pfc.pfc_class_4 is None else pfc.pfc_class_4,
                -1 if pfc.pfc_class_5 is None else pfc.pfc_class_5,
                -1 if pfc.pfc_class_6 is None else pfc.pfc_class_6,
                -1 if pfc.pfc_class_7 is None else pfc.pfc_class_7,
            ]
            fcoe["priorityGroupSize"] = "priorityGroupSize-8"
            fcoe["supportDataCenterMode"] = True
        imports.append(fcoe)

    def _clear_ownership(self, locations):
        try:
            force_ownership = (
                self._api.snappi_config.options.port_options.location_preemption
            )
        except Exception:
            force_ownership = False
        if force_ownership is True:
            available_hardware_hrefs = {}
            location_hrefs = {}
            for location in locations:
                if ";" in location:
                    clp = location.split(";")
                    chassis = (
                        self._api._ixnetwork.AvailableHardware.Chassis.find(
                            Hostname=clp[0]
                        )
                    )
                    if len(chassis) > 0:
                        available_hardware_hrefs[
                            location
                        ] = "%s/card/%s/port/%s" % (
                            chassis.href,
                            abs(int(clp[1])),
                            abs(int(clp[2])),
                        )
                elif "/" in location:
                    appliance = location.split("/")[0]
                    locations = self._api._ixnetwork.Locations
                    locations.find(Hostname=appliance)
                    if len(locations) == 0:
                        locations.add(Hostname=appliance)
                    ports = locations.Ports.find(Location="^%s$" % location)
                    if len(ports) > 0:
                        location_hrefs[location] = ports.href
            self._api.clear_ownership(available_hardware_hrefs, location_hrefs)

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

    def results(self, request):
        """Return port results"""

        self._column_names = request.get("column_names")
        if self._column_names is None:
            self._column_names = []
        elif not isinstance(self._column_names, list):
            msg = "Invalid format of port_names passed {},\
                    expected list".format(
                self._column_names
            )
            raise Exception(msg)

        port_names = request.get("port_names")
        if port_names is None or len(port_names) == 0:
            port_names = [port.name for port in self._api._config.ports]
        elif not isinstance(port_names, list):
            msg = "Invalid format of port_names passed {},\
                    expected list".format(
                port_names
            )
            raise Exception(msg)

        port_filter = {"property": "name", "regex": ".*"}
        port_filter["regex"] = "^(%s)$" % "|".join(
            self._api.special_char(port_names)
        )

        port_rows = dict()
        vports = self._api.select_vports(port_name_filters=[port_filter])
        for vport in vports.values():
            port_row = dict()
            self._set_result_value(port_row, "name", vport.get("name"))
            location = vport.get("location")
            if (
                vport.get("connectionState").startswith("connectedLink")
                is True
            ):
                location += ";connected"
            elif len(location) > 0:
                location += ";" + vport.get("connectionState")
            else:
                location = vport.get("connectionState")
            self._set_result_value(port_row, "location", location)
            self._set_result_value(
                port_row,
                "link",
                "up"
                if vport["connectionState"] == "connectedLinkUp"
                else "down",
            )
            self._set_result_value(port_row, "capture", "stopped")
            # init all columns with corresponding zero-values so that
            # the underlying dictionary contains all requested columns
            # in an event of unwanted exceptions
            for ext_name, _, typ in self._RESULT_COLUMNS:
                self._set_result_value(port_row, ext_name, 0, typ)

            port_rows[vport["name"]] = port_row

        try:
            table = self._api.assistant.StatViewAssistant("Port Statistics")
        except Exception:
            self._api.warning("Could not retrive the port statistics viewer")
            return list(port_rows.values())

        for row in table.Rows:
            vport_name = row["Port Name"]
            if vport_name is None:
                raise Exception("Could not retrive 'Port Name' from stats")
            port_row = port_rows.get(vport_name)
            if port_row is None:
                continue
            for ext_name, int_name, typ in self._RESULT_COLUMNS:
                try:
                    row_val = row[int_name]
                    self._set_result_value(port_row, ext_name, row_val, typ)
                except Exception:
                    # TODO print a warning maybe ?
                    pass
        return list(port_rows.values())
