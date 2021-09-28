# Scenario-1: Simple BGP and Route
```python
device = config.devices.device(name="d1")[-1]
eth = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth.ipv4_addresses.ipv4(name="ip1")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int = bgp.ipv4_interfaces.add(ipv4_name="ip1")
bgp_peer = bgp_int.peers.add(name="bgp1")
v4_routes = bgp_peer.v4_routes.add(name="route1")
v4_routes.addresses.add(address="10.10.0.0")
v4_routes.addresses.add(address="20.20.0.0")
```
- Single ethernet(“eth1”) configurate on top of port “p1”
- Single IPv4(“ip1”) present on top of ethernet(“eth1”)
- Single BGP map with IPv4(“ip1”)
- Two v4_route configure on that bgp_peer
## IxNetwork Mapping
<img src="scr_bgp_1.PNG" alt="drawing" width="500"/>

- Create topology per port
- Ether, IP and BGP can map one to one
- Create network group (NG) according to v4_routes
- Use NG multiplier to accommodate number of address

# Scenario-2: Single Interface and Multiple BGP Peer
```python
device = config.devices.device(name="d1")[-1]
eth1 = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth1.ipv4_addresses.ipv4(name="ip1")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int1 = bgp.ipv4_interfaces.add(ipv4_name="ip1")
bgp_peer1 = bgp_int1.peers.add(name="bgp1")
v4_routes = bgp_peer1.v4_routes.add(name="route1")
v4_routes.addresses.add(address="10.10.0.0")
bgp_int2 = bgp.ipv4_interfaces.add(ipv4_name="ip1")
bgp_peer2 = bgp_int2.peers.add(name="bgp2")
v4_routes = bgp_peer2.v4_routes.add(name="route2")
v4_routes.addresses.add(address="20.20.0.0")
```
- Single Ethernet and IP
- Two BGP peers map to single IP
## IxNetwork Mapping
<img src="scr_bgp_2.PNG" alt="drawing" width="500"/>

- Device multiplier set to 1
- IP stack Multiplier set to 1
- BGP stack Multiplier should set according to the number of BGP peers (here it is 2)
- Compact all values related BGP. And configure those in respective rows.

# Scenario-3: Single Ethernet and Multiple IP and BGP Peer 
```python
device = config.devices.device(name="d1")[-1]
eth1 = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth1.ipv4_addresses.ipv4(name="ip1")
eth1.ipv4_addresses.ipv4(name="ip2")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int1 = bgp.ipv4_interfaces.add(ipv4_name="ip1")
bgp_peer1 = bgp_int1.peers.add(name="bgp1")
v4_routes = bgp_peer1.v4_routes.add(name="route1")
v4_routes.addresses.add(address="10.10.0.0")
bgp_int2 = bgp.ipv4_interfaces.add(ipv4_name="ip2")
bgp_peer2 = bgp_int2.peers.add(name="bgp2")
v4_routes = bgp_peer2.v4_routes.add(name="route2")
v4_routes.addresses.add(address="20.20.0.0")
```
- Single Ethernet on top of single port
- Two IP configure on top of single ethernet
- Two BGP peers map with Two IP
## IxNetwork Mapping
<img src="scr_bgp_3.PNG" alt="drawing" width="500"/>

- Device multiplier set to 1
- IP stack Multiplier should set according to the number of IP address (here it is 2)
- BGP stack Multiplier set to 1
- Compact all values related to IP and BGP. And configure those in respective rows.

# Scenario-4: Multiple Interface and BGP 
```python
device = config.devices.device(name="d1")[-1]
eth1 = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth2 = device.ethernets.ethernet(name='eth2', port_name="p1")[-1]
eth1.ipv4_addresses.ipv4(name="ip1")
eth2.ipv4_addresses.ipv4(name="ip2")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int1 = bgp.ipv4_interfaces.add(ipv4_name="ip1")
bgp_peer1 = bgp_int1.peers.add(name="bgp1")
v4_routes = bgp_peer1.v4_routes.add(name="route1")
v4_routes.addresses.add(address="10.10.0.0")
bgp_int2 = bgp.ipv4_interfaces.add(ipv4_name="ip2")
bgp_peer2 = bgp_int2.peers.add(name="bgp2")
v4_routes = bgp_peer2.v4_routes.add(name="route2")
v4_routes.addresses.add(address="20.20.0.0")
```
- Two interfaces on top of single port
- Two BGP peers map with Two interface 
## IxNetwork Mapping
<img src="scr_bgp_4.PNG" alt="drawing" width="500"/>

- Add device multiplier (say 2 in this example) according to the number of interfaces
- Compact all values related to Ethernet, IP and BGP. And configure those in respective rows
- Stack Multiplier should be 1 for all those stack

# Scenario-5: 2Eth > 2IP in each eth > 2 BGP Peer in each IP
```python
device = config.devices.device(name="d1")[-1]
eth1 = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth2 = device.ethernets.ethernet(name='eth2', port_name="p1")[-1]
eth1.ipv4_addresses.ipv4(name="ip11")
eth1.ipv4_addresses.ipv4(name="ip12")
eth2.ipv4_addresses.ipv4(name="ip21")
eth2.ipv4_addresses.ipv4(name="ip22")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int1 = bgp.ipv4_interfaces.add(ipv4_name="ip11")
bgp_int1.peers.add(name="bgp11")
bgp_int1.peers.add(name="bgp12")
bgp_int2 = bgp.ipv4_interfaces.add(ipv4_name="ip12")
bgp_int2.peers.add(name="bgp13")
bgp_int2.peers.add(name="bgp14")
bgp_int3 = bgp.ipv4_interfaces.add(ipv4_name="ip21")
bgp_int3.peers.add(name="bgp21")
bgp_int3.peers.add(name="bgp22")
bgp_int4 = bgp.ipv4_interfaces.add(ipv4_name="ip22")
bgp_int4.peers.add(name="bgp23")
bgp_int4.peers.add(name="bgp24")
```
## IxNetwork Mapping
<img src="scr_bgp_5.PNG" alt="drawing" width="500"/>

- DG Multiplier(2) 
- IP stack Multiplier (3) 
- BGP stack Multiplier (2)

# Scenario-6: 2Eth > 1IP in each eth > 2 BGP Peer in one IP and 1 BGP Peer in another IP
```python
device = config.devices.device(name="d1")[-1]
eth1 = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth2 = device.ethernets.ethernet(name='eth2', port_name="p1")[-1]
eth1.ipv4_addresses.ipv4(name="ip11")
eth2.ipv4_addresses.ipv4(name="ip21")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int1 = bgp.ipv4_interfaces.add(ipv4_name="ip11")
bgp_int1.peers.add(name="bgp11")
bgp_int1.peers.add(name="bgp12")
bgp_int3 = bgp.ipv4_interfaces.add(ipv4_name="ip21")
bgp_int3.peers.add(name="bgp21")
```
## IxNetwork Mapping
<img src="scr_bgp_6.PNG" alt="drawing" width="500"/>

- IxNetwork: DG Multiplier(2) 
- IP stack Multiplier (1) 
- BGP stack Multiplier (2) 
- Max within Two BGP Peer. And disable one Peer within another set

# Scenario-7: Single BGP run on top of two interface present in two different port
```python
device = config.devices.device(name="d1")[-1]
eth1 = device.ethernets.ethernet(name='eth1', port_name="p1")[-1]
eth2 = device.ethernets.ethernet(name='eth2', port_name="p2")[-1]
eth1.ipv4_addresses.ipv4(name="ip1")
eth2.ipv4_addresses.ipv4(name="ip2")
bgp = device.bgp
bgp.router_id = "1.1.1.1"
bgp_int1 = bgp.ipv4_interfaces.add(ipv4_name="ip1")
bgp_int1.peers.add(name="bgp1")
bgp_int2 = bgp.ipv4_interfaces.add(ipv4_name="ip2")
bgp_int2.peers.add(name="bgp2")
```
## IxNetwork Mapping
<img src="scr_bgp_7.PNG" alt="drawing" width="500"/>

- Plan to put same router ID ("1.1.1.1") within two DG present in two ports

Note: Not sure this is a valid case/ this assumption also true
