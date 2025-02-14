import json
import time
import io
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.logger import get_ixnet_logger


class CommonField:
    def __init__(self, field, offset):
        self.field = field
        self.offset = offset


class Capture(object):
    """Transforms OpenAPI objects into IxNetwork objects

    Args
    ----
    - ixnetworkapi (Api): instance of the Api class

    Transformations
    ---------------
    - /components/schemas/Capture to /vport/capture

    Process
    -------
    - Configure capture according to Filter

    Notes
    -----

    """

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._capture_request = None
        self.logger = get_ixnet_logger(__name__)

    def _import(self, imports):
        if len(imports) > 0:
            errata = self._resource_manager.ImportConfig(
                json.dumps(imports), False
            )
            for item in errata:
                self._api.warning(item)
            return len(errata) == 0
        return True

    def config(self):
        """Overwrite any capture settings"""
        self._resource_manager = self._api._ixnetwork.ResourceManager
        imports = []
        vports = self._api.select_vports()
        for vport in vports.values():
            if (
                vport["capture"]["hardwareEnabled"] is True
                or vport["capture"]["softwareEnabled"] is True
            ):
                capture = {
                    "xpath": vport["capture"]["xpath"],
                    "captureMode": "captureTriggerMode",
                    "hardwareEnabled": False,
                    "softwareEnabled": False,
                }
                imports.append(capture)
        for capture_item in self._api.snappi_config.captures:
            if capture_item.format == "pcap":
                self._api.warning(
                    "pcap format is not supported for IxNetwork, setting capture format to pcapng"
                )
                capture_item.format = "pcapng"
            if capture_item.port_names is None:
                continue
            for port_name in capture_item.port_names:
                capture_mode = "captureTriggerMode"
                if capture_item.get("overwrite"):
                    capture_mode = "captureContinuousMode"
                    reset = {
                        "xpath": vports[port_name]["xpath"]
                        + "/capture/trigger"
                    }
                    self._import(reset)
                capture = {
                    "xpath": vports[port_name]["xpath"] + "/capture",
                    "captureMode": capture_mode,
                    "hardwareEnabled": True,
                    "softwareEnabled": True,
                }
                pallette = {"xpath": capture["xpath"] + "/filterPallette"}
                filter = {"xpath": capture["xpath"] + "/filter"}
                trigger = {"xpath": capture["xpath"] + "/trigger"}
                if len(capture_item.filters) > 0:
                    filter["captureFilterEnable"] = True
                    trigger["captureTriggerEnable"] = True
                    filter["captureFilterFrameSizeEnable"] = False
                    trigger["captureTriggerFrameSizeEnable"] = False
                    filter["captureFilterFrameSizeTo"] = 9198
                    trigger["captureTriggerFrameSizeTo"] = 9198
                    filter["captureFilterFrameSizeFrom"] = 46
                    trigger["captureTriggerFrameSizeFrom"] = 46
                    generic_size = 0
                    expression_string = ""
                    for cap_filter in capture_item.filters:
                        if cap_filter.parent.choice == "ethernet":
                            expression_string = self._config_ethernet_pallette(
                                cap_filter,
                                pallette,
                                trigger,
                                filter,
                                generic_size,
                                expression_string,
                            )
                            generic_size += 14
                        elif cap_filter.parent.choice == "custom":
                            generic_size, expression_string = (
                                self._config_custom_pallete(
                                    cap_filter,
                                    pallette,
                                    trigger,
                                    filter,
                                    generic_size,
                                    expression_string,
                                )
                            )
                        elif cap_filter.parent.choice == "vlan":
                            expression_string = self._config_vlan_pallette(
                                cap_filter,
                                pallette,
                                trigger,
                                filter,
                                generic_size,
                                expression_string,
                            )
                            generic_size += 4
                        elif cap_filter.parent.choice == "ipv4":
                            expression_string = self._config_ipv4_pallete(
                                cap_filter,
                                pallette,
                                trigger,
                                filter,
                                generic_size,
                                expression_string,
                            )
                            generic_size += 20
                        elif cap_filter.parent.choice == "ipv6":
                            expression_string = self._config_ipv6_pallete(
                                cap_filter,
                                pallette,
                                trigger,
                                filter,
                                generic_size,
                                expression_string,
                            )
                            generic_size += 40
                        else:
                            expression_string = self._config_missing_pallete(
                                cap_filter,
                                pallette,
                                trigger,
                                filter,
                                generic_size,
                                expression_string,
                            )
                    filter["captureFilterExpressionString"] = expression_string
                    trigger["captureTriggerExpressionString"] = (
                        expression_string
                    )
                imports.append(capture)
                imports.append(pallette)
                imports.append(filter)
                imports.append(trigger)
        self._import(imports)

    def reset_capture_request(self):
        self._capture_request = None

    def _config_missing_pallete(
        self,
        cap_filter,
        pallette,
        trigger,
        filter,
        generic_size,
        expression_string,
    ):
        pallete_map = getattr(
            self, "_{0}_OFFSET_MAP".format(cap_filter.parent.choice.upper())
        )
        for field_name in dir(cap_filter):
            if field_name not in pallete_map:
                raise Exception(
                    "Api not implimented for {0}".format(field_name)
                )
            if field_name in pallete_map:
                cap_field = getattr(cap_filter, field_name)
                if cap_field.value is not None:
                    new_pattern = GetPattern(
                        filter.get("captureFilterPattern")
                    )
                    pallette[new_pattern.pattern] = cap_field.value
                    pallette[new_pattern.pattern_offset] = pallete_map[
                        field_name
                    ]
                    if cap_field.mask is not None:
                        pallette[new_pattern.pattern_mask] = cap_field.mask
                    negate = ""
                    if (
                        cap_field.negate is not None
                        and cap_field.negate is True
                    ):
                        filter["captureFilterPattern"] = "notPattern1"
                        negate = "!"
                    else:
                        filter["captureFilterPattern"] = (
                            new_pattern.filter_pattern
                        )
                    trigger["captureTriggerPattern"] = filter[
                        "captureFilterPattern"
                    ]
                    if len(expression_string) == 0:
                        expression_string = negate + "P1"
                    else:
                        expression_string = (
                            expression_string + " and " + negate + "P1"
                        )

        return expression_string

    def _config_custom_pallete(
        self,
        cap_filter,
        pallette,
        trigger,
        filter,
        generic_size,
        expression_string,
    ):
        if cap_filter.value is not None:
            pallette["pattern1"] = cap_filter.value
            if cap_filter.mask is not None:
                pallette["patternMask1"] = cap_filter.mask
            if cap_filter.offset is not None:
                pallette["patternOffset1"] = cap_filter.offset
                generic_size += cap_filter.offset
            negate = ""
            if cap_filter.negate is not None and cap_filter.negate is True:
                filter["captureFilterPattern"] = "notPattern1"
                negate = "!"
            else:
                filter["captureFilterPattern"] = "pattern1"
            trigger["captureTriggerPattern"] = filter["captureFilterPattern"]
            if len(expression_string) == 0:
                expression_string = negate + "P1"
            else:
                expression_string = expression_string + " and " + negate + "P1"

        return generic_size, expression_string

    def _config_ethernet_pallette(
        self,
        cap_filter,
        pallette,
        trigger,
        filter,
        generic_size,
        expression_string,
    ):
        if cap_filter.src.value is not None:
            expression_string = self._config_source_address(
                cap_filter.src, pallette, trigger, filter, expression_string
            )
        if cap_filter.dst.value is not None:
            expression_string = self._config_destination_address(
                cap_filter.dst, pallette, trigger, filter, expression_string
            )

        ethernet_fields = [
            CommonField(cap_filter.ether_type, 12),
            CommonField(cap_filter.pfc_queue, 0),
        ]

        for ethernet_field in ethernet_fields:
            if ethernet_field.field.value != "00":
                expression_string = self._config_common_filter_pallete(
                    ethernet_field.field,
                    pallette,
                    trigger,
                    filter,
                    generic_size + ethernet_field.offset,
                    expression_string,
                )
        return expression_string

    def _config_vlan_pallette(
        self,
        cap_filter,
        pallette,
        trigger,
        filter,
        generic_size,
        expression_string,
    ):
        vlan_fields = [
            CommonField(cap_filter.priority, 0),
            CommonField(cap_filter.cfi, 0),
            CommonField(cap_filter.id, 0),
            CommonField(cap_filter.protocol, 2),
        ]

        for vlan_field in vlan_fields:
            if vlan_field.field.value != "00":
                expression_string = self._config_common_filter_pallete(
                    vlan_field.field,
                    pallette,
                    trigger,
                    filter,
                    generic_size + vlan_field.offset,
                    expression_string,
                )

        return expression_string

    def _config_ipv4_pallete(
        self,
        cap_filter,
        pallette,
        trigger,
        filter,
        generic_size,
        expression_string,
    ):
        ipv4_fields = [
            CommonField(cap_filter.version, 0),
            CommonField(cap_filter.header_length, 0),
            CommonField(cap_filter.priority, 1),
            CommonField(cap_filter.total_length, 2),
            CommonField(cap_filter.identification, 4),
            CommonField(cap_filter.reserved, 6),
            CommonField(cap_filter.dont_fragment, 6),
            CommonField(cap_filter.more_fragments, 6),
            CommonField(cap_filter.fragment_offset, 6),
            CommonField(cap_filter.time_to_live, 8),
            CommonField(cap_filter.protocol, 9),
            CommonField(cap_filter.header_checksum, 10),
            CommonField(cap_filter.src, 12),
            CommonField(cap_filter.dst, 16),
        ]

        for ipv4_field in ipv4_fields:
            if ipv4_field.field.value != "00":
                expression_string = self._config_common_filter_pallete(
                    ipv4_field.field,
                    pallette,
                    trigger,
                    filter,
                    generic_size + ipv4_field.offset,
                    expression_string,
                )

        return expression_string

    def _config_ipv6_pallete(
        self,
        cap_filter,
        pallette,
        trigger,
        filter,
        generic_size,
        expression_string,
    ):
        ipv6_fields = [
            CommonField(cap_filter.version, 0),
            CommonField(cap_filter.traffic_class, 0),
            CommonField(cap_filter.flow_label, 1),
            CommonField(cap_filter.payload_length, 4),
            CommonField(cap_filter.next_header, 6),
            CommonField(cap_filter.hop_limit, 7),
            CommonField(cap_filter.src, 8),
            CommonField(cap_filter.dst, 24),
        ]

        for ipv6_field in ipv6_fields:
            if ipv6_field.field.value != "00":
                expression_string = self._config_common_filter_pallete(
                    ipv6_field.field,
                    pallette,
                    trigger,
                    filter,
                    generic_size + ipv6_field.offset,
                    expression_string,
                )

        return expression_string

    def _hex_to_str_with_space(self, hex_value):
        return " ".join(
            hex_value[i : i + 2] for i in range(0, len(hex_value), 2)
        )

    def _config_source_address(
        self, src, pallette, trigger, filter, expression_string
    ):
        if src.value is not None:
            pallette["SA1"] = self._hex_to_str_with_space(src.value)
            if src.mask is not None:
                pallette["SAMask1"] = self._hex_to_str_with_space(src.mask)
            negate = ""
            if src.negate is not None and src.negate is True:
                filter["captureFilterSA"] = "notAddr1"
                negate = "!"
            else:
                filter["captureFilterSA"] = "addr1"
            trigger["captureTriggerSA"] = filter["captureFilterSA"]
            if len(expression_string) == 0:
                expression_string = negate + "SA1"
            else:
                expression_string = (
                    expression_string + " and " + negate + "SA1"
                )

        return expression_string

    def _config_destination_address(
        self, dst, pallette, trigger, filter, expression_string
    ):
        if dst.value is not None:
            pallette["DA1"] = self._hex_to_str_with_space(dst.value)
            if dst.mask is not None:
                pallette["DAMask1"] = self._hex_to_str_with_space(dst.mask)
            negate = ""
            if dst.negate is not None and dst.negate is True:
                filter["captureFilterDA"] = "notAddr1"
                negate = "!"
            else:
                filter["captureFilterDA"] = "addr1"
            trigger["captureTriggerDA"] = filter["captureFilterDA"]
            if len(expression_string) == 0:
                expression_string = negate + "DA1"
            else:
                expression_string = (
                    expression_string + " and " + negate + "DA1"
                )
        return expression_string

    def _config_common_filter_pallete(
        self, field, pallette, trigger, filter, offset, expression_string
    ):
        if field.value is not None:
            if pallette.get("pattern1") is None:
                pallette["pattern1"] = field.value
                pallette["patternOffset1"] = offset
                if field.mask is not None:
                    pallette["patternMask1"] = field.mask
                negate = ""
                if field.negate is not None and field.negate is True:
                    filter["captureFilterPattern"] = "notPattern1"
                    negate = "!"
                else:
                    filter["captureFilterPattern"] = "pattern1"
                trigger["captureTriggerPattern"] = filter[
                    "captureFilterPattern"
                ]
                if len(expression_string) == 0:
                    expression_string = negate + "P1"
                else:
                    expression_string = (
                        expression_string + " and " + negate + "P1"
                    )
            elif pallette.get("pattern2") is None:
                pallette["pattern2"] = field.value
                pallette["patternOffset2"] = offset
                if field.mask is not None:
                    pallette["patternMask2"] = field.mask
                negate = ""
                if field.negate is not None and field.negate is True:
                    negate = "!"
                filter["captureFilterPattern"] = "pattern1AndPattern2"
                trigger["captureTriggerPattern"] = filter[
                    "captureFilterPattern"
                ]
                if len(expression_string) == 0:
                    expression_string = negate + "P2"
                else:
                    expression_string = (
                        expression_string + " and " + negate + "P2"
                    )
            else:
                self._api.warning("Cannot apply more than 2 filters.")
        return expression_string

    def set_capture_state(self, request):
        """Starts capture on all ports that have capture enabled."""
        self._capture_request = request
        if request.state == "start":
            self._start_capture()
        elif request.state == "stop":
            self._stop_capture()

    def _start_capture(self):
        with Timer(self._api, "Captures start"):
            if self._capture_request is None:
                return
            ixn_vports = self._api.select_vports()
            if len(ixn_vports) == 0:
                raise Exception("Please configure port before start capture")
            ixn_cap_ports = [
                name
                for name, vport in ixn_vports.items()
                if vport["capture"]["hardwareEnabled"] is True
            ]
            port_names = self._capture_request.port_names
            if (
                port_names is None
                or len(set(ixn_cap_ports) ^ set(port_names)) == 0
            ):
                payload = {"arg1": []}
                for vport in ixn_vports.values():
                    payload["arg1"].append(vport["href"])
                url = (
                    "%s/vport/operations/clearCaptureInfos"
                    % self._api._ixnetwork.href
                )
                self._api._request("POST", url, payload)
                self._api._ixnetwork.StartCapture()
            else:
                url = (
                    "%s/vport/capture/operations/start"
                    % self._api._ixnetwork.href
                )
                for vport_name, vport in ixn_vports.items():
                    if vport_name not in port_names:
                        continue
                    if vport["capture"]["hardwareEnabled"] is False:
                        raise Exception(
                            "Please enable capture in"
                            " %s before start capture" % vport_name
                        )
                    payload = {"arg1": "{0}/capture".format(vport["href"])}
                    try:
                        self._api._request("POST", url, payload)
                    except Exception:
                        pass

    def _stop_capture(self):
        with Timer(self._api, "Captures stop"):
            ixn_vports = self._api.select_vports()
            if len(ixn_vports) == 0:
                raise Exception("Please configure port before stop capture")
            if self._capture_request.port_names:
                payload = {"arg1": []}
                for vport_name, vport in ixn_vports.items():
                    if vport_name in self._capture_request.port_names:
                        payload["arg1"].append(vport["href"])
                url = "{}/vport/operations/clearCaptureInfos".format(
                    self._api._ixnetwork.href
                )

                self._api._request("POST", url, payload)
            else:
                self._api._ixnetwork.StopCapture()

    def results(self, request):
        """Gets capture file and returns it as a byte stream"""
        with Timer(self._api, "Captures stop"):
            capture = self._api._vport.find(
                Name=self._api.special_char(request.port_name)
            ).Capture
            capture.Stop("allTraffic")

            # Internally setting max time_out to 90sec,
            #  with 3sec polling interval.
            # Todo: Need to discuss and incorporate time_out field within model
            retry_count = 30
            port_ready = True
            for x in range(retry_count):
                port_ready = True
                time.sleep(3)
                capture = self._api._vport.find(
                    Name=self._api.special_char(request.port_name)
                ).Capture
                if (
                    capture.HardwareEnabled
                    and capture.DataCaptureState == "notReady"
                ):
                    port_ready = False
                    continue
                if (
                    capture.SoftwareEnabled
                    and capture.ControlCaptureState == "notReady"
                ):
                    port_ready = False
                    continue
                break
            if not port_ready:
                self._api.warning(
                    "Capture was not stopped for this port %s"
                    % (request.port_name)
                )

        self._api._ixnetwork.SaveCaptureFiles(
            self._api._ixnetwork.Globals.PersistencePath + "/capture"
        )

        dc = (
            self._api._ixnetwork.Globals.PersistencePath
            + "/capture/"
            + self._api._vport.Name
            + "_HW.cap"
        )
        cc = (
            self._api._ixnetwork.Globals.PersistencePath
            + "/capture/"
            + self._api._vport.Name
            + "_SW.cap"
        )
        merged_capture = (
            self._api._ixnetwork.Globals.PersistencePath
            + "/capture/"
            + self._api._vport.Name
            + ".cap"
        )

        self._api._ixnetwork.MergeCapture(
            Arg1=cc, Arg2=dc, Arg3=merged_capture
        )

        url = "{}/vport/operations/releaseCapturePorts".format(
            self._api._ixnetwork.href
        )
        payload = {"arg1": [self._api._vport.href]}
        self._api._request("POST", url, payload)

        path = "%s/capture" % self._api._ixnetwork.Globals.PersistencePath
        # Todo: Revert dc to merged capture after fix is available in 9.20
        url = "%s/files?absolute=%s&filename=%s" % (
            self._api._ixnetwork.href,
            path,
            dc,
        )
        pcap_file_bytes = self._api._request("GET", url)
        return io.BytesIO(pcap_file_bytes)


class GetPattern(object):
    """This is validating captureFilterPattern and return expected patterns"""

    def __init__(self, cap_filter_pattern):
        self._new_count = 1
        self.cap_filter_pattern = cap_filter_pattern
        self._validate_pattern(cap_filter_pattern)

    def _validate_pattern(self, cap_filter_pattern):
        if cap_filter_pattern is not None:
            self._new_count = 2

    @property
    def pattern(self):
        return "pattern{0}".format(self._new_count)

    @property
    def pattern_mask(self):
        return "patternMask{0}".format(self._new_count)

    @property
    def pattern_offset(self):
        return "patternOffset{0}".format(self._new_count)

    @property
    def filter_pattern(self):
        if self._new_count == 1:
            return "pattern{0}".format(self._new_count)
        else:
            return "{0}AndPattern{1}".format(
                self.cap_filter_pattern, self._new_count
            )
