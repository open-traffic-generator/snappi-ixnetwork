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

    def results(self, ping_request, req_type=None):
        responses = []
        v4_names = []
        for device in self._api._config.devices:
            for eth in device.ethernets:
                for ip in eth.ipv4_addresses:
                    v4_names.append(ip.name)
        v6_names = []
        for device in self._api._config.devices:
            for eth in device.ethernets:
                for ip in eth.ipv6_addresses:
                    v6_names.append(ip.name)
        if req_type == None:
            raise Exception(
                "req_type variable is mandatory to decide ipv4 or ipv6"
            )
        else:
            with Timer(self._api, "Ping requests completed in"):
                for endpoint in ping_request.requests:
                    response = {}
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
                                response["result"] = "succeeded"
                            else:
                                response["result"] = "failed"
                    response["src_name"] = src_name
                    response["dst_ip"] = dst_ip
                    responses.append(response)
                return responses
