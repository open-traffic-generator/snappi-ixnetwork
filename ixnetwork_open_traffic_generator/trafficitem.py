import json


class TrafficItem(object):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    
    """
    _BIT_RATE_UNITS_TYPE = {
        'bps' : 'bitsPerSec',
        'kbps' : 'kbitsPerSec',
        'mbps' : 'mbitsPerSec',
        'gbps' : 'mbytesPerSec'
    }
    
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        
    def config(self):
        """Configure config.flows onto Ixnetwork.Traffic.TrafficItem
        
        CRUD
        ----
        - DELETE any TrafficItem.Name that does not exist in config.flows
        - CREATE TrafficItem for any config.flows[*].name that does not exist
        - UPDATE TrafficItem for any config.flows[*].name that exists
        """
        traffic_items = self._api.assistant.Ixnetwork.Traffic.TrafficItem
        for traffic_item in traffic_items.find():
            if self.find_item(self._config.flows, 'name', traffic_item.Name) is None:
                traffic_item.remove()
        traffic_items.find()

        if (self._api.config.flows) :
            for flow in self._api.config.flows:
                args = {
                    'Name': flow.name
                }
                traffic_item = self._api.find_item(traffic_items, 'Name', flow.name)
                if traffic_item is None:
                    traffic_item = traffic_items.add(**args)[-1]
                else:
                    traffic_item.update(**args)
                self._api.ixn_objects[flow.name] = traffic_item
                self._configure_endpoints(traffic_item, flow.endpoint)
                
                # TBD - Need to rework if EndpointSetId=1 will not true for all case
                ixn_config_element = traffic_item.ConfigElement.find(EndpointSetId = 1)
                self._configure_size(ixn_config_element, flow.size)
                self._configure_rate(ixn_config_element, flow.rate)
                self._configure_flow(traffic_item, flow.packet)

    def _configure_endpoints(self, traffic_item, endpoints):
        """
        Setting TrafficType according to choice then configured endpoint accordingly
        """
        if (endpoints.choice == "port"):
            traffic_item.TrafficItemType = 'raw'
            self._configure_port_endpoints(traffic_item, endpoints.port)
        else:
            traffic_item.TrafficItemType = 'l2L3'
            self._configure_device_endpoints(traffic_item, endpoints.device)


    def _get_ixn_ports(self, ports):
        ixn_ports = list()
        for port in ports:
            vport = self._api.assistant.Ixnetwork.Vport.find(Name = port)
            ixn_ports.append(vport.Protocols.find())
        return ixn_ports

    def _configure_port_endpoints(self, ixn_traffic, port):
        """ Configure Port within Endpoint Set
        """
        args = {
            'Sources': self._get_ixn_ports([port.tx_port])[0],
            'Destinations' : self._get_ixn_ports(port.rx_ports)
        }
        ixn_traffic.EndpointSet.add(**args)
        

    # TBD - Use self._api.ixn_objects To get that ixn_object
    def _get_ixn_devices(self, devices):
        ixn_devices = list()
        for device in devices:
            ixn_topology = self._api.assistant.Ixnetwork.Topology.find(Name = device)
            if len(ixn_topology):
                ixn_devices.append(ixn_topology[0])
        return ixn_devices

    def _configure_device_endpoints(self, ixn_traffic, device):
        """ Configure Device (protocol or network group) within Endpoint Set
        """
        return
        
        args = {
                'Sources': self._get_ixn_devices(device.tx_devices),
            }
        ixn_endpoint = ixn_traffic.EndpointSet.add(**args)


    def _configure_flow(self, ixn_traffic, packets):
        """ Create Traffic Packet
        """
        for packet in packets:
            try:
                method = getattr(self, "_configure_%s" %packet.choice)
            except Exception as e:
                print("Error - Method %s not implimented" %packet.choice)
                return

            method(ixn_traffic, packet)


    def _configure_pfcpause(self, ixn_traffic, packet):
        pfcpause = packet.pfcpause
        pfcPause_template = self._api.assistant.Ixnetwork.Traffic.ProtocolTemplate.find(StackTypeId='^pfcPause')


    def _configure_size(self, ixn_config_element, size):
        """ Configure frameSize within /traffic/trafficItem[*]/configElement[*]/frameSize
        """

        # TBD - IxNetwork is not accepting float in FixedSize
        ixn_frame_size = ixn_config_element.FrameSize
        if size.choice == 'fixed':
            ixn_frame_size.Type = "fixed"
            ixn_frame_size.FixedSize = size.fixed
        elif size.choice == 'increment':
            ixn_frame_size.Type = "increment"
            ixn_frame_size.IncrementFrom = size.increment.start
            ixn_frame_size.IncrementTo = size.increment.end
            ixn_frame_size.IncrementStep = size.increment.step
        elif size.choice == 'random':
            ixn_frame_size.Type = "random"
            ixn_frame_size.RandomMin = size.random.min
            ixn_frame_size.RandomMax = size.random.max
        else:
            print('Warning - We need to implement this %s choice' %size.choice)
            
    def _configure_rate(self, ixn_config_element, rate):
        """ Configure frameRate within /traffic/trafficItem[*]/configElement[*]/frameRate
        """
        ixn_frame_rate = ixn_config_element.FrameRate
        if (rate.unit == 'line'):
            ixn_frame_rate.Type = 'percentLineRate'
        elif (rate.unit == 'pps'):
            ixn_frame_rate.Type = 'framesPerSecond'
        else:
            ixn_frame_rate.Type = 'bitsPerSecond'
            ixn_frame_rate.BitRateUnitsType = TrafficItem._BIT_RATE_UNITS_TYPE[rate.unit]
        ixn_frame_rate.Rate = rate.value
        



    def state(self):
        """Set state of config.flows onto Ixnetwork.Traffic.TrafficItem
        """
        pass
