import logging

import pytest
import snappi

from snappi_ixnetwork.trafficitem import TrafficItem

PORTS = {"tx": "/vport[1]", "rx1": "/vport[2]", "rx2": "/vport[3]"}


def _ti():
    # helpers do not use instance state
    ti = TrafficItem.__new__(TrafficItem)
    ti.logger = logging.getLogger("test")
    return ti


def _flow(tx="tx", rx_name=None, rx_names=None):
    flow = snappi.Api().config().flows.flow(name="f")[-1]
    ep = flow.tx_rx.port
    ep.tx_name = tx
    if rx_name is not None:
        ep.rx_name = rx_name
    if rx_names is not None:
        ep.rx_names = rx_names
    return flow


def test_rx_names_multiple_ports():
    flow = _flow(rx_names=["rx1", "rx2"])
    tx, rx = _ti()._get_port_endpoints(flow.tx_rx.port, PORTS, "f")
    assert tx == ["/vport[1]/protocols"]
    assert rx == ["/vport[2]/protocols", "/vport[3]/protocols"]
    assert _ti()._get_mesh_type(flow) == "manyToMany"


def test_rx_name_single_port():
    flow = _flow(rx_name="rx1")
    _, rx = _ti()._get_port_endpoints(flow.tx_rx.port, PORTS, "f")
    assert rx == ["/vport[2]/protocols"]
    assert _ti()._get_mesh_type(flow) == "oneToOne"


@pytest.mark.parametrize(
    "kwargs, exc",
    [
        ({}, ValueError),
        ({"rx_name": "rx1", "rx_names": ["rx2"]}, ValueError),
        ({"rx_names": ["rx1", "rx1"]}, ValueError),
        ({"rx_names": ["rx1", "nope"]}, NameError),
    ],
)
def test_rx_names_invalid(kwargs, exc):
    flow = _flow(**kwargs)
    with pytest.raises(exc):
        _ti()._get_port_endpoints(flow.tx_rx.port, PORTS, "f")
