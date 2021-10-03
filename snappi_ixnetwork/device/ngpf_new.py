import json

from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.device.bgp import Bgp
from snappi_ixnetwork.device.ethernet import Ethernet
from snappi_ixnetwork.device.compactor import Compactor
from snappi_ixnetwork.device.createixnconfig import CreateIxnConfig

class New(Base):
    _DEVICE_ENCAP_MAP = {
        "DeviceEthernet": "ethernetVlan",
        "DeviceIpv4": "ipv4",
        "DeviceIpv6": "ipv6",
        "bgpv4": "ipv4",
        "bgpv6": "ipv6",
    }

    def __init__(self, ixnetworkapi):
        super(New, self).__init__()
        self._api = ixnetworkapi
        self._ixn_config = {}
        self._ixn_topo_objects = {}
        self._ethernet = Ethernet(self)
        self._bgp = Bgp(self)
        self.compactor = Compactor()
        self._createixnconfig = CreateIxnConfig(self)

    def set_device_info(self, snappi_obj, ixn_obj):
        name = snappi_obj.get("name")
        class_name = snappi_obj.__class__.__name__
        if class_name not in New._DEVICE_ENCAP_MAP:
            raise Exception(
                "Mapping is missing for {0}".format(class_name)
            )
        self._api.set_device_encap(
            name, New._DEVICE_ENCAP_MAP[class_name]
        )
        self._api.set_ixn_object(name, ixn_obj)

    def config(self):
        self._ixn_topo_objects = {}
        self.working_dg = None
        self._ixn_config = self.att_dict()
        self._ixn_config["xpath"] = "/"
        with Timer(self._api, "Convert device config :"):
            self._configure_topology()
        with Timer(self._api, "Create IxNetwork config :"):
            self._createixnconfig.create(
                self._ixn_config["topology"], "topology"
            )
        with Timer(self._api, "Push IxNetwork config :"):
            self._pushixnconfig()

    def _get_topology_name(self, port_name):
        return "Topology %s" % port_name

    def _configure_topology(self):
        self.stop_topology()
        self._api._remove(self._api._topology, [])
        ixn_topos = self.create_node(self._ixn_config, "topology")
        for device in self._api.snappi_config.devices:
            self._configure_device_group(device, ixn_topos)

        for ixn_topo in self._ixn_topo_objects.values():
            self.compactor.compact(ixn_topo.get(
                "deviceGroup"
            ))

    def _configure_device_group(self, device, ixn_topos):
        """map ethernet with a ixn deviceGroup with multiplier = 1"""
        for ethernet in device.get("ethernets"):
            port_name = ethernet.get("port_name")
            if port_name in self._ixn_topo_objects:
                ixn_topo = self._ixn_topo_objects[port_name]
            else:
                ixn_topo = self.add_element(ixn_topos)
                ixn_topo["name"] = self._get_topology_name(port_name)
                ixn_topo["ports"] = [self._api.get_ixn_object(port_name).xpath]
                self._ixn_topo_objects[port_name] = ixn_topo
            ixn_dg = self.create_node_elemet(
                ixn_topo, "deviceGroup", device.get("name")
            )
            ixn_dg["multiplier"] = 1
            self.working_dg = ixn_dg
            self._ethernet.config(ethernet, ixn_dg)
        self._bgp.config(device)


    def _pushixnconfig(self):
        resource_manager = self._api._ixnetwork.ResourceManager
        ixn_cnf = json.dumps(self._ixn_config, indent=2)
        print(ixn_cnf)
        errata = resource_manager.ImportConfig(
            ixn_cnf, False
        )
        for item in errata:
            self._api.warning(item)

    def stop_topology(self):
        glob_topo = self._api._globals.Topology.refresh()
        if glob_topo.Status == "started":
            self._api._ixnetwork.StopAllProtocols("sync")
