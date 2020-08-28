import json


class TrafficItem(object):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    """
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

        for flow in self._api.config.flows:
            args = {
                'Name': flow.name
            }
            traffic_item = self._api.find_item(traffic_items, 'Name', flow.name)
            if traffic_item is None:
                traffic_items.add(**args)
            else:
                traffic_item.update(**args)

    def state(self):
        """Set state of config.flows onto Ixnetwork.Traffic.TrafficItem
        """
        pass
