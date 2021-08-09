# class Events(object):
#     def __init__(self, ixnetworkapi):
#         self._api = ixnetworkapi
#
#     def config(self):
#         events = self._api.snappi_config._properties.get("events")
#         if events is None:
#             return
#         ixn_CpdpConvergence = self._api._traffic.Statistics.CpdpConvergence
#         if self.event_allow("rx_rate_threshold"):
#             if self._api.traffic_item.has_latency is True:
#                 raise Exception(
#                     "We are supporting either latency or rx_rate_threshold"
#                 )
#             ixn_CpdpConvergence.Enabled = True
#             ixn_CpdpConvergence.EnableControlPlaneEvents = True
#             ixn_CpdpConvergence.EnableDataPlaneEventsRateMonitor = True
#             if events.rx_rate_threshold.threshold is not None:
#                 ixn_CpdpConvergence.DataPlaneThreshold = (
#                     events.rx_rate_threshold.threshold
#                 )
#         else:
#             ixn_CpdpConvergence.Enabled = False
#
#     def event_allow(self, event_name):
#         events = self._api.snappi_config._properties.get("events")
#         if events is None:
#             return False
#         event = events._properties.get(event_name)
#         if events.enable is True or (
#             event is not None and event.enable is True
#         ):
#             return True
#         else:
#             return False
