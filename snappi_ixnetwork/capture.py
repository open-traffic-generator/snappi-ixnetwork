import json
import time
import io
from snappi_ixnetwork.timer import Timer


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

    _IPV4_OFFSET_MAP = {
        "version": "14",
        "headeer_length": "14",
        "priority": "15",
        "total_length": "16",
        "identification": "18",
        "reserved": "20",
        "dont_fragment": "20",
        "more_fragments": "20",
        "fragment_offset": "20",
        "time_to_live": "22",
        "protocol": "23",
        "header_checksum": "24",
        "src": "26",
        "dst": "30",
    }

    _VLAN_OFFSET_MAP = {
        "priority": "34",
        "cfi": "34",
        "id": "34",
        "protocol": "36",
    }

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._capture_request = None

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
                    reset["captureTriggerEnable"] = False
                    self._import(reset)
                capture = {
                    "xpath": vports[port_name]["xpath"] + "/capture",
                    "captureMode": capture_mode,
                    "hardwareEnabled": True,
                    "softwareEnabled": False,
                }
                pallette = {"xpath": capture["xpath"] + "/filterPallette"}
                filter = {"xpath": capture["xpath"] + "/filter"}
                trigger = {"xpath": capture["xpath"] + "/trigger"}
                if len(capture_item.filters) > 0:
                    filter["captureFilterEnable"] = True
                    trigger["captureTriggerEnable"] = True
                    filter["captureFilterEnable"] = True
                    for cap_filter in capture_item.filters:
                        if cap_filter.parent.choice == "ethernet":
                            self._config_ethernet_pallette(
                                cap_filter, pallette, trigger, filter
                            )
                        elif cap_filter.parent.choice == "custom":
                            self._config_custom_pallete(
                                cap_filter, pallette, trigger, filter
                            )
                        else:
                            self._config_missing_pallete(
                                cap_filter, pallette, trigger, filter
                            )
                imports.append(capture)
                imports.append(pallette)
                imports.append(filter)
                imports.append(trigger)
        self._import(imports)

    def reset_capture_request(self):
        self._capture_request = None

    def _config_missing_pallete(self, cap_filter, pallette, trigger, filter):
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
                    if (
                        cap_field.negate is not None
                        and cap_field.negate is True
                    ):
                        filter["captureFilterPattern"] = "notPattern1"
                    else:
                        filter[
                            "captureFilterPattern"
                        ] = new_pattern.filter_pattern
                    trigger["triggerFilterPattern"] = filter[
                        "captureFilterPattern"
                    ]

    def _config_custom_pallete(self, cap_filter, pallette, trigger, filter):
        if cap_filter.value is not None:
            pallette["pattern1"] = cap_filter.value
            if cap_filter.mask is not None:
                pallette["patternMask1"] = cap_filter.mask
            if cap_filter.offset is not None:
                pallette["patternOffset1"] = cap_filter.offset
            if cap_filter.negate is not None and cap_filter.negate is True:
                filter["captureFilterPattern"] = "notPattern1"
            else:
                filter["captureFilterPattern"] = "pattern1"
            trigger["triggerFilterPattern"] = filter["captureFilterPattern"]

    def _config_ethernet_pallette(self, cap_filter, pallette, trigger, filter):
        if cap_filter.src.value is not None:
            pallette["SA1"] = cap_filter.src.value
            if cap_filter.src.mask is not None:
                pallette["SAMask1"] = cap_filter.src.mask
            if (
                cap_filter.src.negate is not None
                and cap_filter.src.negate is True
            ):
                filter["captureFilterSA"] = "notAddr1"
            else:
                filter["captureFilterSA"] = "addr1"
            trigger["triggerFilterSA"] = filter["captureFilterSA"]
        if cap_filter.dst.value is not None:
            pallette["DA1"] = cap_filter.dst.value
            if cap_filter.dst.mask is not None:
                pallette["DAMask1"] = cap_filter.dst.mask
            if (
                cap_filter.dst.negate is not None
                and cap_filter.dst.negate is True
            ):
                filter["captureFilterDA"] = "notAddr1"
            else:
                filter["captureFilterDA"] = "addr1"
            trigger["triggerFilterDA"] = filter["captureFilterDA"]

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

        payload = {"arg1": [self._api._vport.href]}
        url = "%s/vport/operations/getCaptureInfos" % self._api._ixnetwork.href
        response = self._api._request("POST", url, payload)
        file_name = response["result"][0]["arg6"]
        file_id = response["result"][0]["arg1"]

        url = "%s/vport/operations/saveCaptureInfo" % self._api._ixnetwork.href
        payload = {"arg1": self._api._vport.href, "arg2": file_id}
        self._api._request("POST", url, payload)

        url = "{}/vport/operations/releaseCapturePorts".format(
            self._api._ixnetwork.href
        )
        payload = {"arg1": [self._api._vport.href]}
        self._api._request("POST", url, payload)

        path = "%s/capture" % self._api._ixnetwork.Globals.PersistencePath
        url = "%s/files?absolute=%s&filename=%s.cap" % (
            self._api._ixnetwork.href,
            path,
            file_name,
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
