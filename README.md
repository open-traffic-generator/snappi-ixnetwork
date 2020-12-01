# Keysight IxNetwork Open Traffic Generator
[![Build](https://github.com/open-traffic-generator/ixnetwork/workflows/Build/badge.svg)](https://github.com/open-traffic-generator/ixnetwork/actions)
[![pypi](https://img.shields.io/pypi/v/ixnetwork-open-traffic-generator.svg)](https://pypi.org/project/ixnetwork-open-traffic-generator)
[![python](https://img.shields.io/pypi/pyversions/ixnetwork-open-traffic-generator.svg)](https://pypi.python.org/pypi/ixnetwork-open-traffic-generator)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](https://en.wikipedia.org/wiki/MIT_License)

The Keysight IxNetwork implementation of the open-traffic-generator models.  
To start contributing, please see [contributing.md](contributing.md).

# Getting Started
## Install client package
```
python -m pip install --upgrade ixnetwork-open-traffic-generator
```
## Start scripting
```python
# for constructing traffic configuration
from abstract_open_traffic_generator import (
    port, flow, config, control, result
)
# for making API calls
from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi

# provide API server and port addresses
api = IxNetworkApi(address='127.0.0.1', port=11009)
tx = port.Port(name='Tx Port', location='127.0.0.1;2;1')
rx = port.Port(name='Rx Port', location='127.0.0.1;2;2')

# configure one TCP flow (with default protocol headers) to send 10000 packets,
# each of 128 bytes at 10% of max line rate
flw = flow.Flow(
    name='Flow %s->%s' % (tx.name, rx.name),
    tx_rx=flow.TxRx(
        flow.PortTxRx(tx_port_name=tx.name, rx_port_name=rx.name)
    ),
    packet=[
        flow.Header(flow.Ethernet()),
        flow.Header(flow.Vlan()),
        flow.Header(flow.Ipv4()),
        flow.Header(flow.Tcp())
    ],
    size=flow.Size(128),
    rate=flow.Rate(value=10, unit='line'),
    duration=flow.Duration(flow.FixedPackets(packets=10000))
)

# push configuration and start transmitting flows
cfg = config.Config(ports=[tx, rx], flows=[flw])
api.set_state(control.State(control.ConfigState(config=cfg, state='set')))
api.set_state(control.State(control.FlowTransmitState(state='start')))

# fetch tx port stats and wait until total frames sent is correct
while 10000 != sum([
    p['frames_tx'] for p in api.get_port_results(
        result.PortRequest(port_names=[tx.name], column_names=['frames_tx'])
    )
]):
    continue

```
