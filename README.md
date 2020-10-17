# Keysight IxNetwork Open Traffic Generator
[![Build](https://github.com/open-traffic-generator/ixnetwork/workflows/Build/badge.svg)](https://github.com/open-traffic-generator/ixnetwork/actions)
[![pypi](https://img.shields.io/pypi/v/ixnetwork-open-traffic-generator.svg)](https://pypi.org/project/ixnetwork-open-traffic-generator)
[![python](https://img.shields.io/pypi/pyversions/ixnetwork-open-traffic-generator.svg)](https://pypi.python.org/pypi/ixnetwork-open-traffic-generator)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](https://en.wikipedia.org/wiki/MIT_License)

The Keysight IxNetwork implementation of the open-traffic-generator models.

# Getting Started
## Install the client
```
pip install --upgrade ixnetwork-open-traffic-generator
```
## Start scripting
```python
"""A simple test that demonstrates the following:
- A port that transmits an ethernet/vlan/ipv4/tcp flow 
for a specified duration and a port that receives the packets.
- While the flow is transmitting the script prints out tx and rx statistics.
- Once all the packets have been transmitted the script will end. 
"""
import abstract_open_traffic_generator.port as port
import abstract_open_traffic_generator.flow as flow
import abstract_open_traffic_generator.config as config
import abstract_open_traffic_generator.control as control
import abstract_open_traffic_generator.result as result
from ixnetwork_open_traffic_generator.ixnetworkapi import IxNetworkApi
import pandas

tx_port = port.Port(name='Tx Port', location='10.36.74.26;02;13')
rx_port = port.Port(name='Rx Port', location='10.36.74.26;02;14')
flow = flow.Flow(name='Tx Port to Rx Port Flow',
                 tx_rx=flow.TxRx(
                     flow.PortTxRx(tx_port_name=tx_port.name,
                                   rx_port_names=[rx_port.name])),
                 packet=[
                     flow.Header(flow.Ethernet()),
                     flow.Header(flow.Vlan()),
                     flow.Header(flow.Ipv4()),
                     flow.Header(flow.Tcp())
                 ],
                 size=flow.Size(128),
                 rate=flow.Rate(unit='pps', value=1000),
                 duration=flow.Duration(flow.FixedPackets(10000)))
config = config.Config(ports=[tx_port, rx_port],
                       flows=[flow],
                       options=config.Options(port_options=port.Options(
                           location_preemption=True)))

api = IxNetworkApi(address='10.36.66.49', port=11009)
api.set_state(control.State(control.ConfigState(config=config, state='set')))
state = control.State(control.FlowTransmitState(state='start'))
api.set_state(state)

request = result.PortRequest(
    column_names=['name', 'location', 'frames_tx', 'frames_rx'])
while True:
    results = api.get_port_results(request)
    df = pandas.DataFrame.from_dict(results)
    print(df)
    if df.frames_tx.sum() >= config.flows[0].duration.packets.packets:
        break
```

