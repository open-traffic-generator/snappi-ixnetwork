### Abstract

In snappi_IxNetwork we simulate object of devices, interfaces, protocol interfaces and routes according to snappi object. 
In order to build up a multiple device (say 1000 device in each port) we normally end up with millions of objects which will impact performance 
(sometime IxNetwork not support those many object). 
We have designed an optimization technique for the compaction of these objects. 

The compaction mechanism will help to simplify IxNetwork Scenarios by cumulating elements with identical sub-hierarchies 
(network device, L23 Protocol stacks, network groups, route ranges). 
The technique will help to reduce the memory need and the necessary processing time for running the scenario.


### Details of the solution 

In snappi we create and store objects in a tree structure right from device to various layered protocol stack and network ranges. 
These objects get stored in a hierarchical manner. 
We will leverage these nodes to segregate the group with the help of dependent node and its attributes. 
We traverse from the top of our node to extreme bottom till our supported layer. 
This goes on recursively till we cover the leave of the node. 
Then as per below diagram we will check the relevant information which can be clubbed and fit within snappi_IxNetwork existing design paradigm.


### Compactor Diagram

# ![diagram](compactor_diagram.png)
