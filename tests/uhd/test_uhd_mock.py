import snappi
from mock import MagicMock
from snappi_ixnetwork.snappi_api import Api as ixn_api
from snappi_ixnetwork.trafficitem import TrafficItem


def test_uhd_port_locations():
    api = ixn_api()
    api._ixnetwork = lambda x: None
    api._ixnetwork.Globals = lambda y: None
    api._ixnetwork.Globals.ProductVersion = "UHD"
    api._traffic = lambda z: None
    api._traffic.State = "Stopped"
    config = snappi.Api().config()
    api._config = config
    port = config.ports.port(location="a;b;c", name="p1").port(
        location="localuhd/a", name="p2"
    )
    api._validate_instance(config)
    assert port[0].location == "localuhd/b.c"
    assert port[1].location == "localuhd/a"


expected_global = {
    "xpath": "/traffic",
    "trafficItem": [
        {
            "xpath": "/traffic/trafficItem[1]",
            "name": "f1",
            "srcDestMesh": "oneToOne",
            "endpointSet": [
                {
                    "xpath": "/traffic/trafficItem[1]/endpointSet[1]",
                    "sources": ["/vport[1]/protocols"],
                    "destinations": ["/vport[2]/protocols"],
                }
            ],
            "trafficType": "raw",
            "configElement": [
                {
                    "xpath": "/traffic/trafficItem[1]/configElement[1]",
                    "stack": [
                        {
                            "xpath": "/traffic/trafficItem[1]/configElement[1]"
                            "/stack[@alias = 'globalPause-1']",
                            "field": [
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'globalPause-1'"
                                    "]/field[@alias = 'globalPause.header."
                                    "header.dstAddress-1']",
                                    "valueType": "singleValue",
                                    "singleValue": "01:80:c2:00:00:01",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'globalPause-1']"
                                    "/field[@alias = 'globalPause.header."
                                    "header.srcAddress-2']",
                                    "valueType": "singleValue",
                                    "singleValue": "00:00:00:00:00:00",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'globalPause-1'"
                                    "]/field[@alias = 'globalPause.header."
                                    "header.ethertype-3']",
                                    "valueType": "singleValue",
                                    "singleValue": "8808",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'globalPause-1"
                                    "']/field[@alias = 'globalPause.header."
                                    "macControl.controlOpcode-4']",
                                    "valueType": "singleValue",
                                    "singleValue": 1,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'globalPause-1'"
                                    "]/field[@alias = 'globalPause.header."
                                    "macControl.pfcQueue0-5']",
                                    "valueType": "singleValue",
                                    "singleValue": "0",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}


def test_global_pause_header():
    config = snappi.Api().config()
    api = ixn_api()
    api._ixnetwork = lambda x: None
    api._ixnetwork.Globals = lambda y: None
    api._ixnetwork.Globals.ProductVersion = "UHD"
    tr_obj = TrafficItem(api)
    ports = {"p1": "/vport[1]", "p2": "/vport[2]"}
    tr_obj.get_ports_encap = MagicMock(return_value=ports)
    tr_obj.get_device_encap = MagicMock(return_value={})
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.port.tx_name = "p1"
    f1.tx_rx.port.rx_name = "p2"
    f1.packet.ethernetpause()
    tr_obj.copy_flow_packet(config)
    tr_raw = tr_obj.create_traffic(config)
    assert tr_raw == expected_global


def test_enable_min_frame_size():
    config = snappi.Api().config()
    api = ixn_api()
    tr_obj = TrafficItem(api)
    api._ixnetwork = lambda x: None
    api._ixnetwork.Globals = lambda y: None
    api._ixnetwork.Globals.ProductVersion = "ABC"
    api._traffic = lambda x: None
    api._traffic.EnableMinFrameSize = False
    f1 = config.flows.flow()[-1]
    f1.name = "flow1"
    f1.packet.pfcpause()
    tr_obj._config = config

    tr_obj._configure_options()
    assert api._traffic.EnableMinFrameSize is True
    api._ixnetwork.Globals.ProductVersion = "UHD"

    api._traffic.EnableMinFrameSize = False
    tr_obj._configure_options()
    assert api._traffic.EnableMinFrameSize is False
