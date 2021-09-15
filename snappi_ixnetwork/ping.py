from snappi_ixnetwork.timer import Timer


class Ping(object):
    """Transforms OpenAPI objects into IxNetwork objects

    Args
    ----
    - ixnetworkapi (Api): instance of the Api class

    Process
    -------
    - Ping to the interfaces and return response

    Notes
    -----
    """

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi

    def results(self, ping_request):
        responses = []
        v4_names = [
            device.ethernet.ipv4.name for device in self._api._config.devices
        ]
        v6_names = [
            device.ethernet.ipv6.name for device in self._api._config.devices
        ]
        with Timer(self._api, "Ping requests completed in"):
            for endpoint in ping_request.endpoints:
                response = {}
                req_type = endpoint.parent.choice
                src_name = endpoint.get("src_name")
                dst_ip = endpoint.get("dst_ip")
                if req_type == "ipv4":
                    if src_name not in v4_names:
                        msg = (
                            src_name
                            + """ is not available in the configured v4 interface names """
                            + str(v4_names)
                        )
                        raise Exception(msg)
                    ip_obj = (
                        self._api._ixnetwork.Topology.find()
                        .DeviceGroup.find()
                        .Ethernet.find()
                        .Ipv4.find(Name=src_name)
                    )
                elif req_type == "ipv6":
                    if src_name not in v6_names:
                        msg = (
                            src_name
                            + """ is not available in the configured v6 interface names """
                            + str(v6_names)
                        )
                        raise Exception(msg)
                    ip_obj = (
                        self._api._ixnetwork.Topology.find()
                        .DeviceGroup.find()
                        .Ethernet.find()
                        .Ipv6.find(Name=src_name)
                    )
                self._api.info("Sending ping to %s" % dst_ip)
                ping_status = ip_obj.SendPing(DestIP=dst_ip)
                for reply in ping_status:
                    if dst_ip in reply["arg3"]:
                        if reply["arg2"]:
                            response["result"] = "success"
                        else:
                            response["result"] = "failure"
                response["src_name"] = src_name
                response["dst_ip"] = dst_ip
                responses.append(response)
            return responses
