from inspect import stack
import json
import copy
import time
from snappi_ixnetwork.timer import Timer


class CreateConfig(object):
    def __init__(self, ixnapi):
        self._api = ixnapi
        self.vport_index = 1
        self.topo_index = 1
        self.traffic_index = 1
        self._imports = dict()
        self.port_to_topo = dict()
        self.snappi_config = None
        self.running_config = None
        self.stateful_config = None
        self.name_to_obj_map = {
            'ports': {}, 'devices': {},
            'flows': {}, 'layer1': {}
        }

    def _export_config(self):
        href = '%sresourceManager' % self._api._ixnetwork.href
        url = '%s/operations/exportconfig' % href
        payload = {
            'arg1': href,
            'arg2': [
                "/vport", "/topology", "/traffic/trafficItem"
            ],
            'arg3': True,
            'arg4': 'json'
        }
        res = self._api._request('POST', url=url, payload=payload)
        return json.loads(res['result'])

    def _importconfig(self, imports):
        imports['xpath'] = '/'
        href = '%sresourceManager' % self._api._ixnetwork.href
        url = '%s/operations/importconfig' % href
        import json
        payload = {
            'arg1': href,
            'arg2': json.dumps(imports),
            'arg3': False
        }
        res = self._api._request('POST', url=url, payload=payload)
        return res

    def _append_unique_names(self, name, node, obj):
        if self.name_to_obj_map.get(node) is not None and\
                name in self.name_to_obj_map.get(node):
            raise Exception("name \"{}\" is not unique".format(name))
        self.name_to_obj_map[node][name] = obj
        return

    def _get_obj_by_name(self, name, node):
        node = self.name_to_obj_map.get(node)
        if node.get(name) is None:
            raise Exception("Invalid name provided")
        return node[name]

    def _validate_and_config(self, config):
        self.snappi_config = config
        imports = dict()
        self.stateful_config = copy.deepcopy(config)
        with Timer(self._api, "port config"):
            self._api.vport.config()
        with Timer(self._api, "Export config"):
            conf = self._export_config()
        with Timer(self._api, "Remove Traffic and Topology"):
            self.remove_traffic_and_topo()
        with Timer(self._api, "Apply json config"):
            imports.update(
                self.create_topology(self.stateful_config, conf['vport'])
            )
            devices = self.create_devices(self.stateful_config)
            for i, t in enumerate(imports.get('topology')):
                imports['topology'][i]['deviceGroup'] = devices[i]
            tr = self.create_traffic(self.stateful_config)
            imports['traffic'] = {}
            imports['traffic'].update(tr)
            self._importconfig(imports)

    def config(self, config):
        self._validate_and_config(config)

    def remove_traffic_and_topo(self):
        if len(self._api._ixnetwork.Traffic.TrafficItem.find()) > 0:
            start_states = [
                'txStopWatchExpected', 'locked', 'started',
                'startedWaitingForStats', 'startedWaitingForStreams',
                'stoppedWaitingForStats'
            ]
            state = self._api._ixnetwork.Traffic.State
            if state in start_states:
                self._api._ixnetwork.Traffic.StopStatelessTrafficBlocking()
            url = '%s/traffic/trafficItem' % self._api._ixnetwork.href
            self._api._request('DELETE', url)
            self._api._ixnetwork.Traffic.TrafficItem.find().refresh()
        if len(self._api._ixnetwork.Topology.find()) > 0:
            state = self._api._ixnetwork.Topology.find().Status
            states = ['started', 'starting', 'mixed']
            if state not in states:
                url = '%s/topology' % self._api._ixnetwork.href
                self._api._request('DELETE', url)
                return
            self._api._ixnetwork.Topology.find().Stop()
            count = 0
            while True:
                state = self._api._ixnetwork.Topology.find().Status
                if state not in states:
                    break
                if count >= 60:
                    self._api._ixnetwork.Topology.find().Abort()
                    break
                time.sleep(1)
                count += 1
            url = '%s/topology' % self._api._ixnetwork.href
            self._api._request('DELETE', url)
        return

    def create_topology(self, config, vports):
        imports = {'topology': []}
        for i, p in enumerate(config.ports):
            p._properties['xpath'] = vports[i]['xpath']
            t_xpath = '/topology[%d]' % self.topo_index
            p._properties['topo_xpath'] = t_xpath
            imports['topology'].append({
                'name': '%s' % p.name,
                'xpath': t_xpath,
                'ports': [vports[i]['xpath']]
            })
            self._append_unique_names(p.name, 'ports', p)
            self.topo_index += 1
        return imports

    def create_vports(self, config):
        ports = list()
        topos = list()
        imports = dict()
        for p in config.ports:
            if p._properties.get('name') is None:
                raise Exception("name shall not be None for port")
            if p._properties.get('location') is None:
                raise Exception("location shall not be None for port")
            p_xpath = '/vport[%d]' % self.vport_index
            ports.append({
                'name': p.name,
                'xpath': p_xpath
            })
            self._append_unique_names(p.name, 'ports', p)
            t_xpath = '/topology[%d]' % self.topo_index
            topos.append({
                'name': '%s' % p.name,
                'location': p.location,
                'xpath': t_xpath
            })
            p._properties['xpath'] = p_xpath
            p._properties['topo_xpath'] = t_xpath
            self.vport_index += 1
            self.topo_index += 1
        imports['vport'] = ports
        imports['topology'] = topos
        return imports

    def create_l1Config(self, config):
        pass

    def create_devices(self, config):
        topos = [
            p.name for p in config.ports
        ]
        dev_indices = [1 for i in range(len(topos))]
        dev_lists = [list() for i in range(len(topos))]
        for i, d in enumerate(config.devices):
            dev = dict()
            if d._properties.get('name') is None:
                raise Exception("name shall not be None for device")
            if d._properties.get('container_name') is None:
                raise Exception(
                    "container_name shall not be None for device"
                )
            if d._properties.get('device_count') is None:
                dev['multiplier'] = 1
            else:
                dev['multiplier'] = d._properties['device_count']
            dev['name'] = d.name
            self._append_unique_names(d.name, 'devices', d)
            index = topos.index(d.container_name)
            t_path = config.ports[index]._properties['topo_xpath']
            dev['xpath'] = '%s/deviceGroup[%d]' % (t_path, dev_indices[index])
            d._properties['xpath'] = dev['xpath']
            eth = self.create_ethernet(d)
            if len(eth) > 0:
                dev['ethernet'] = eth
            dev_lists[index].append(dev)
            dev_indices[index] += 1
        return dev_lists

    def create_ethernet(self, device):
        eth_list = list()
        if device._properties.get('ethernet') is None:
            return eth_list
        ethernet = device.ethernet
        eth = dict()
        eth['xpath'] = '%s/ethernet[1]' % device._properties['xpath']
        ethernet._properties['xpath'] = eth['xpath']
        if ethernet._properties.get('name') is None:
            raise Exception("name shall not be None for ethernet")
        eth['name'] = ethernet.name
        self._append_unique_names(ethernet.name, 'devices', ethernet)
        ipv4 = self.create_ipv4(ethernet)
        ipv6 = self.create_ipv6(ethernet)
        if len(ipv4) > 0:
            eth['ipv4'] = ipv4
            ethernet._parent._properties['type'] = 'ipv4'
        if len(ipv6) > 0:
            eth['ipv6'] = ipv6
        ethernet._properties['ixn_params'] = {
            'mtu': 'mtu',
            'mac': 'mac'
        }
        ethernet._properties['type'] = 'ethernetVlan'
        params = self.config_dev_pattern(ethernet)
        if len(params) > 0:
            eth.update(params)
        eth_list.append(eth)
        return eth_list

    def create_ipv4(self, ethernet):
        ip_list = list()
        if ethernet._properties.get('ipv4') is None:
            return list()
        ipv4 = ethernet.ipv4
        ip = dict()
        ip['xpath'] = '%s/ipv4[1]' % ethernet._properties['xpath']
        ipv4._properties['xpath'] = ip['xpath']
        if ipv4._properties.get('name') is None:
            raise Exception("name shall not be None for ipv4")
        ip['name'] = ipv4.name
        self._append_unique_names(ipv4.name, 'devices', ipv4)
        ipv4._properties['ixn_params'] = {
            'address': 'address',
            'gateway': 'gatewayIp',
            'prefix': 'prefix'
        }
        ipv4._properties['type'] = 'ipv4'
        params = self.config_dev_pattern(ipv4)
        if len(params) > 0:
            ip.update(params)
        ip_list.append(ip)
        return ip_list

    def create_ipv6(self, ethernet):
        ip_list = list()
        if ethernet._properties.get('ipv6') is None:
            return list()
        index = 2
        if ethernet._properties.get('ipv4') is None:
            index = 1
        ipv6 = ethernet.ipv6
        ip = dict()
        ip['xpath'] = '%s/ipv6[%d]' % (ethernet._properties['xpath'], index)
        ipv6._properties['xpath'] = ip['xpath']
        if ipv6._properties.get('name') is None:
            raise Exception("name shall not be None for ipv6")
        ip['name'] = ipv6.name
        self._append_unique_names(ipv6.name, 'devices', ipv6)
        ipv6._properties['ixn_params'] = {
            'address': 'address',
            'gateway': 'gatewayIp',
            'prefix': 'prefix'
        }
        ipv6._properties['type'] = 'ipv6'
        params = self.config_dev_pattern(ipv6)
        if len(params) > 0:
            ip.update(params)
        ip_list.append(ip)
        return ip_list

    def config_dev_pattern(self, obj):
        param_dt = dict()
        param_list = obj._properties.get('ixn_params')
        for param in param_list:
            if obj._properties.get(param) is None:
                continue
            param_obj = getattr(obj, param)
            types = [int, str, list, dict]
            patterns = ['value', 'value', 'values', 'incr/dec']
            try:
                ind = types.index(type(param_obj))
            except TypeError:
                raise Exception("please provide the valid, for %s" % param)
            choice = patterns[ind]

            mv = dict()
            mv['xpath'] = "/multivalue[@source = '{} {}']".format(
                obj._properties['xpath'], param_list[param]
            )
            mv['clearOverlays'] = False
            pattern = dict()
            if choice == 'value':
                pattern['xpath'] = '%s/singleValue' % mv['xpath']
                pattern["value"] = param_obj
                mv['singleValue'] = pattern
            if choice == 'values':
                pattern['xpath'] = '%s/valueList' % mv['xpath']
                pattern["values"] = param_obj
                mv['valueList'] = pattern
            if choice == 'increment' or choice == 'decrement':
                pattern['xpath'] = '%s/counter' % mv['xpath']
                if param_obj.get('start') is not None:
                    pattern['start'] = param_obj.start
                if param_obj.get('step') is not None:
                    pattern['step'] = param_obj.step
                pattern['direction'] = (
                    'increment' if param_obj.get('direction') is None else
                    param_obj.get('direction')
                )
                mv['counter'] = pattern
            param_dt[param] = mv
        return param_dt

    def create_traffic(self, config):
        flows = config.flows
        tr = {
            'xpath': '/traffic',
            'trafficItem': []
        }
        for i, f in enumerate(flows):
            if f._properties.get('name') is None:
                raise Exception("name shall not be null for flows")
            if f._properties.get('tx_rx') is None:
                msg = "Please configure the flow endpoint" \
                    "for flow indexed at %s" % i
                raise Exception(msg)
            if f.tx_rx.choice is None:
                msg = "Flow endpoint needs to be either port or device"
                raise Exception(msg)
            if f.tx_rx.choice == "port":
                tr_type = 'raw'
                ep = getattr(f.tx_rx, 'port')
                node = 'ports'
                tx_objs = [
                    '%s/protocols' % self._get_obj_by_name(
                        ep.tx_name, node
                    )._properties['xpath']
                ]
                rx_objs = [
                    '%s/protocols' % self._get_obj_by_name(
                        ep.rx_name, node
                    )._properties['xpath']
                ]
            else:
                ep = getattr(f.tx_rx, 'device')
                node = 'devices'
                tr_type = self._get_obj_by_name(
                    ep.tx_names[0], node
                )._properties['type']
                tx_objs = [
                    self._get_obj_by_name(n, node)._properties['xpath']
                    for n in ep.tx_names
                ]
                rx_objs = [
                    self._get_obj_by_name(n, node)._properties['xpath']
                    for n in ep.rx_names
                ]
            tr_xpath = '/traffic/trafficItem[%d]' % self.traffic_index
            tr['trafficItem'].append(
                {
                    'xpath': tr_xpath,
                    'name': '%s' % f.name
                }
            )
            self._append_unique_names(f.name, 'flows', f)
            tr['trafficItem'][-1]['endpointSet'] = [{
                'xpath': tr['trafficItem'][-1]['xpath'] + '/endpointSet[1]'
            }]
            tr['trafficItem'][-1]['endpointSet'][0]['sources'] = [
                o for o in tx_objs
            ]
            tr['trafficItem'][-1]['endpointSet'][0]['destinations'] = [
                o for o in rx_objs
            ]
            tr['trafficItem'][-1]['trafficType'] = tr_type
            if tr_type == 'raw':
                tr['trafficItem'][-1]['configElement'] =\
                    self.config_raw_stack(tr_xpath, f.packet)
            self.traffic_index += 1
        return tr

    def config_raw_stack(self, xpath, packet):
        ce_path = '%s/configElement[1]' % xpath
        config_elem = {
            'xpath': ce_path,
            'stack': []
        }
        for i, header in enumerate(packet):
            stack_name = self._api.traffic_item._TYPE_TO_HEADER.get(
                header._choice
            )
            header_xpath = '%s/stack[@alias = \'%s-%d\']' % (
                ce_path, stack_name, i + 1
            )
            self._api.traffic_item._append_header(
                header, header_xpath, config_elem['stack']
            )
        fcs_xpath = '%s/stack[@alias = \'%s-%d\']' % (
            ce_path, 'fcs', len(packet) + 1
        )
        config_elem['stack'].append({'xpath': fcs_xpath, 'field': []})
        return [config_elem]
