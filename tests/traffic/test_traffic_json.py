import snappi
import pytest
from mock import MagicMock
from collections import namedtuple
from snappi_ixnetwork.trafficitem import TrafficItem

expected_raw_type = {
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
                            "/stack[@alias = 'ethernet-1']",
                            "field": [
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ethernet-1']/"
                                    "field[@alias = 'ethernet.header."
                                    "destinationAddress-1']",
                                    "valueType": "singleValue",
                                    "singleValue": "00:00:00:00:00:00",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ethernet-1']"
                                    "/field[@alias = 'ethernet.header."
                                    "sourceAddress-2']",
                                    "valueType": "singleValue",
                                    "singleValue": "00:00:00:00:00:00",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ethernet-1']"
                                    "/field[@alias = 'ethernet.header."
                                    "etherType-3']",
                                    "valueType": "auto",
                                    "activeFieldChoice": False,
                                    "auto": True,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ethernet-1']"
                                    "/field[@alias = 'ethernet.header."
                                    "pfcQueue-4']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                            ],
                        },
                        {
                            "xpath": "/traffic/trafficItem[1]/configElement[1]"
                            "/stack[@alias = 'ipv4-2']",
                            "field": [
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.version-1']",
                                    "valueType": "singleValue",
                                    "singleValue": 4,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.header"
                                    "Length-2']",
                                    "valueType": "auto",
                                    "activeFieldChoice": False,
                                    "auto": True,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.raw-3']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.tos."
                                    "precedence-4']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.tos."
                                    "delay-5']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.tos."
                                    "throughput-6']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.tos."
                                    "reliability-7']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.tos."
                                    "monetary-8']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.priority."
                                    "tos.unused-9']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.priority.ds."
                                    "phb.defaultPHB.defaultPHB-10']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": True,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.ds.phb."
                                    "defaultPHB.unused-11']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": True,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.ds.phb."
                                    "classSelectorPHB.classSelectorPHB-12']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.ds.phb."
                                    "classSelectorPHB.unused-13']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.ds.phb."
                                    "assuredForwardingPHB.assured"
                                    "ForwardingPHB-14']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.ds.phb."
                                    "assuredForwardingPHB.unused-15']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.priority.ds."
                                    "phb.expeditedForwardingPHB.expedited"
                                    "ForwardingPHB-16']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.priority.ds.phb."
                                    "expeditedForwardingPHB.unused-17']"
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.total"
                                    "Length-18']",
                                    "valueType": "auto",
                                    "activeFieldChoice": False,
                                    "auto": True,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header."
                                    "identification-19']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.flags."
                                    "reserved-20']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']"
                                    "/field[@alias = 'ipv4.header.flags."
                                    "fragment-21']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']"
                                    "/field[@alias = 'ipv4.header.flags."
                                    "lastFragment-22']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']"
                                    "/field[@alias = 'ipv4.header."
                                    "fragmentOffset-23']",
                                    "valueType": "singleValue",
                                    "singleValue": 0,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/"
                                    "field[@alias = 'ipv4.header.ttl-24']",
                                    "valueType": "singleValue",
                                    "singleValue": 64,
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.protocol-25']",
                                    "valueType": "auto",
                                    "activeFieldChoice": False,
                                    "auto": True,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.checksum-26']",
                                    "valueType": "auto",
                                    "activeFieldChoice": False,
                                    "auto": True,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.srcIp-27']",
                                    "valueType": "singleValue",
                                    "singleValue": "0.0.0.0",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                                {
                                    "xpath": "/traffic/trafficItem[1]/config"
                                    "Element[1]/stack[@alias = 'ipv4-2']/field"
                                    "[@alias = 'ipv4.header.dstIp-28']",
                                    "valueType": "singleValue",
                                    "singleValue": "0.0.0.0",
                                    "activeFieldChoice": False,
                                    "auto": False,
                                },
                            ],
                        },
                    ],
                }
            ],
        }
    ],
}

expected_device_type = {
    "xpath": "/traffic",
    "trafficItem": [
        {
            "xpath": "/traffic/trafficItem[1]",
            "name": "f1",
            "srcDestMesh": "manyToMany",
            "trafficType": "ipv4",
            "endpointSet": [
                {
                    "xpath": "/traffic/trafficItem[1]/endpointSet[1]",
                    "sources": ["/topology[1]/deviceGroup[1]"],
                    "destinations": ["/topology[2]/deviceGroup[1]"],
                }
            ],
        }
    ],
}


def test_create_traffic_raw():
    config = snappi.Api().config()
    api = MagicMock()
    tr_obj = TrafficItem(api)
    ports = {"p1": "/vport[1]", "p2": "/vport[2]"}
    tr_obj.get_ports_encap = MagicMock(return_value=ports)
    tr_obj.get_device_encap = MagicMock(return_value={})
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.port.tx_name = "p1"
    f1.tx_rx.port.rx_name = "p2"
    f1.packet.ethernet().ipv4()
    tr_obj.copy_flow_packet(config)
    tr_raw = tr_obj.create_traffic(config)
    assert tr_raw == expected_raw_type


def test_create_traffic_raw2():
    config = snappi.Api().config()
    api = MagicMock()
    tr_obj = TrafficItem(api)
    ports = {"p1": "/vport[1]", "p2": "/vport[2]"}
    tr_obj.get_ports_encap = MagicMock(return_value=ports)
    tr_obj.get_device_encap = MagicMock(return_value={})
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.port.tx_name = "p1"
    f1.tx_rx.port.rx_name = "p2"
    f1.packet.ethernet().ipv4()
    eth = f1.packet[0]
    eth.dst.value = "00:00:00:00:00:00"
    tr_obj.copy_flow_packet(config)
    tr_raw = tr_obj.create_traffic(config)
    assert tr_raw == expected_raw_type


@pytest.mark.parametrize("v4_or_v6", [4, 6])
def test_create_traffic_device(v4_or_v6):
    config = snappi.Api().config()
    api = MagicMock()
    tr_obj = TrafficItem(api)
    ports = {"p1": "/vport[1]", "p2": "/vport[2]"}
    ixn_obj_info = namedtuple("IxNobjInfo", ["xpath", "names"])
    devices = {
        "d1": {
            "dev_info": ixn_obj_info("/topology[1]/deviceGroup[1]", []),
            "type": "ipv4",
        },
        "d2": {
            "dev_info": ixn_obj_info("/topology[1]/deviceGroup[2]", []),
            "type": "ipv6",
        },
        "d3": {
            "dev_info": ixn_obj_info("/topology[1]/deviceGroup[1]", []),
            "type": "ipv4",
        },
        "d4": {
            "dev_info": ixn_obj_info("/topology[1]/deviceGroup[2]", []),
            "type": "ipv6",
        },
    }
    tr_obj.get_ports_encap = MagicMock(return_value=ports)
    tr_obj.get_device_info = MagicMock(return_value=devices)
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = ["d1" if v4_or_v6 == 4 else "d2"]
    f1.tx_rx.device.rx_names = ["d3" if v4_or_v6 == 4 else "d4"]
    f1.packet.ethernet().ipv4()
    tr_device = tr_obj.create_traffic(config)
    expected_device_type["trafficItem"][0]["endpointSet"][0]["sources"] = [
        devices[f1.tx_rx.device.tx_names[0]]["dev_info"].xpath
    ]
    expected_device_type["trafficItem"][0]["endpointSet"][0][
        "destinations"
    ] = [devices[f1.tx_rx.device.rx_names[0]]["dev_info"].xpath]
    expected_device_type["trafficItem"][0]["trafficType"] = "ipv%s" % v4_or_v6
    assert tr_device == expected_device_type
    ixn_stack = expected_raw_type["trafficItem"][0]["configElement"][0][
        "stack"
    ]

    ixn_stack[0]["field"][0] = {
        "xpath": ixn_stack[0]["field"][0]["xpath"],
        "valueType": "auto",
        "activeFieldChoice": False,
        "auto": True,
    }

    stacks = [
        {"xpath": ixn_stack[0]["xpath"]},
        {"xpath": ixn_stack[1]["xpath"]},
    ]
    snappi_stack = tr_obj._configure_packet(stacks, f1.packet)
    assert snappi_stack == ixn_stack


def test_configure_size():
    config = snappi.Api().config()
    api = MagicMock()
    tr_obj = TrafficItem(api)
    config_elem = [
        {
            "xpath": "/traffic/trafficItem[1]/configElement[1]",
            "frameSize": {
                "xpath": "/traffic/trafficItem[1]/configElement[1]/frameSize"
            },
        }
    ]
    f1 = config.flows.flow(name="f1")[-1]
    tr_obj._configure_size(config_elem, f1.size)

    assert config_elem[0]["frameSize"]["type"] == "fixed"
    assert config_elem[0]["frameSize"]["fixedSize"] == 64


def test_configure_rate():
    config = snappi.Api().config()
    api = MagicMock()
    tr_obj = TrafficItem(api)
    config_elem = [
        {
            "xpath": "/traffic/trafficItem[1]/configElement[1]",
            "frameRate": {
                "xpath": "/traffic/trafficItem[1]/configElement[1]/frameRate"
            },
        }
    ]
    f1 = config.flows.flow(name="f1")[-1]
    tr_obj._configure_rate(config_elem, f1.rate)
    assert config_elem[0]["frameRate"]["type"] == "framesPerSecond"
    assert config_elem[0]["frameRate"]["rate"] == 1000


def test_configure_duration():
    config = snappi.Api().config()
    api = MagicMock()
    tr_obj = TrafficItem(api)
    config_elem = [
        {
            "xpath": "/traffic/trafficItem[1]/configElement[1]",
            "transmissionControl": {
                "xpath": "/traffic/trafficItem[1]/configElement[1]"
                "/transmissionControl"
            },
        }
    ]
    f1 = config.flows.flow(name="f1")[-1]
    tr_obj._configure_duration(config_elem, 1, f1.duration)
    assert config_elem[0]["transmissionControl"]["type"] == "continuous"
    assert config_elem[0]["transmissionControl"]["minGapBytes"] == 12
    assert config_elem[0]["transmissionControl"]["startDelay"] == 0.0
    assert config_elem[0]["transmissionControl"]["startDelayUnits"] == "bytes"


if __name__ == "__main__":
    pytest.main(["-s", __file__])
