import json
import time
import re
from snappi_ixnetwork.timer import Timer


class Vport(object):
    """Transforms OpenAPI objects into IxNetwork objects

    Args
    ----
    - ixnetworkapi (Api): instance of the Api class

    Transformations
    ---------------
    - /components/schemas/Port to /vport
    - /components/schemas/Layer1 to /vport/l1Config/...

    Process
    -------
    - Remove any vports that are not in the config.ports
    - Add any vports that are in the config.ports
    - If the location of the config.ports.location is different than the
      the /vport -connectedTo property set it to None
    - If the config.ports.location is None don't connect the ports
      else connect the port, get the vport type, set the card mode based on the
      config.layer1.speed

    Notes
    -----
    - Uses resourcemanager to set the vport location and l1Config as it is the
      most efficient way. DO NOT use the AssignPorts API as it is too slow. 
    - Only setup l1Config if location is connected. 
    - Given a connected location and speed the vport -type, card resource mode
      and l1Config sub node are derived.

    """
    _SPEED_MAP = {
        'speed_400_gbps': 'speed400g',
        'speed_200_gbps': 'speed200g',
        'speed_100_gbps': 'speed100g',
        'speed_50_gbps': 'speed50g',
        'speed_40_gbps': 'speed40g',
        'speed_25_gbps': 'speed25g',
        'speed_10_gbps': 'speed10g',
        'speed_1_gbps': 'speed1000',
        'speed_100_fd_mbps': 'speed100fd',
        'speed_100_hd_mbps': 'speed100hd',
        'speed_10_fd_mbps': 'speed10fd',
        'speed_10_hd_mbps': 'speed10hd'
    }
    _VM_SPEED_MAP = {
        'speed_400_gbps': 'speed400g',
        'speed_200_gbps': 'speed200g',
        'speed_100_gbps': 'speed100g',
        'speed_90_gbps': 'speed90g',
        'speed_80_gbps': 'speed80g',
        'speed_70_gbps': 'speed70g',
        'speed_60_gbps': 'speed60g',
        'speed_50_gbps': 'speed50g',
        'speed_40_gbps': 'speed40g',
        'speed_30_gbps': 'speed30g',
        'speed_25_gbps': 'speed25g',
        'speed_20_gbps': 'speed20g',
        'speed_10_gbps': 'speed10g',
        'speed_9_gbps': 'speed9000',
        'speed_8_gbps': 'speed8000',
        'speed_7_gbps': 'speed7000',
        'speed_6_gbps': 'speed6000',
        'speed_5_gbps': 'speed5000',
        'speed_4_gbps': 'speed4000',
        'speed_3_gbps': 'speed3000',
        'speed_2_gbps': 'speed2000',
        'speed_1_gbps': 'speed1000',
        'speed_100_mbps': 'speed100',
        'speed_100_fd_mbps': 'speed100',
        'speed_100_hd_mbps': 'speed100',
        'speed_10_fd_mbps': 'speed100',
        'speed_10_hd_mbps': 'speed100'
    }

    _SPEED_MODE_MAP = {
        'speed_1_gbps': 'normal',
        'speed_10_gbps': 'tengig',
        'speed_25_gbps': 'twentyfivegig',
        'speed_40_gbps': 'fortygig',
        'speed_50_gbps': 'fiftygig',
        'speed_100_gbps':
            '^(?!.*(twohundredgig|fourhundredgig)).*hundredgig.*$',
        'speed_200_gbps': 'twohundredgig',
        'speed_400_gbps': 'fourhundredgig'
    }

    _ADVERTISE_MAP = {
        'advertise_one_thousand_mbps': 'speed1000',
        'advertise_one_hundred_fd_mbps': 'speed100fd',
        'advertise_one_hundred_hd_mbps': 'speed100hd',
        'advertise_ten_fd_mbps': 'speed10fd',
        'advertise_ten_hd_mbps': 'speed10hd'
    }
    _FLOW_CONTROL_MAP = {
        'ieee_802_1qbb': 'ieee802.1Qbb',
        'ieee_802_3x': 'ieee802.3x'
    }

    _RESULT_COLUMNS = [
        ('frames_tx', 'Frames Tx.', int),
        ('frames_rx', 'Valid Frames Rx.', int),
        ('frames_tx_rate', 'Frames Tx. Rate', float),
        ('frames_rx_rate', 'Valid Frames Rx. Rate', float),
        ('bytes_tx', 'Bytes Tx.', int),
        ('bytes_rx', 'Bytes Rx.', int),
        ('bytes_tx_rate', 'Bytes Tx. Rate', float),
        ('bytes_rx_rate', 'Bytes Rx. Rate', float),
        ('pfc_class_0_frames_rx', 'Rx Pause Priority Group 0 Frames', int),
        ('pfc_class_1_frames_rx', 'Rx Pause Priority Group 1 Frames', int),
        ('pfc_class_2_frames_rx', 'Rx Pause Priority Group 2 Frames', int),
        ('pfc_class_3_frames_rx', 'Rx Pause Priority Group 3 Frames', int),
        ('pfc_class_4_frames_rx', 'Rx Pause Priority Group 4 Frames', int),
        ('pfc_class_5_frames_rx', 'Rx Pause Priority Group 5 Frames', int),
        ('pfc_class_6_frames_rx', 'Rx Pause Priority Group 6 Frames', int),
        ('pfc_class_7_frames_rx', 'Rx Pause Priority Group 7 Frames', int),
    ]

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._layer1_check = []
        self._ip_to_chassis_ = dict()

    def _export_config(self, arg2):
        href = '%sresourceManager' % self._api._ixnetwork.href
        url = '%s/operations/exportconfig' % href
        payload = {
            'arg1': href,
            'arg2': arg2,
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
            'arg3': False,
            'arg4': 'suppressErrorsWarnings',
            'arg5': False
        }
        # self._api._ixnetwork.ResourceManager.ImportConfig(**payload)
        try:
            res = self._api._request('POST', url=url, payload=payload)
        except Exception:
            return
        return res

    def _parse_location(self, ind, snappi):
        sep = '/' if '/' in snappi.ports[0].location else ';'
        loc = [
            p.location.split(sep)[:]
            if ind == ':' else p.location.split(sep)[ind]
            for p in snappi.ports
        ]
        return loc

    def config(self, config):
        self.get_chassis(config)
        self.get_vports(config)
        pass

    def get_vports(self, snappi):
        self._build_port_collection(snappi)
        url = '%s/vport' % self._api._ixnetwork.href
        ixn_ports = self._api._request('GET', url)
        if ixn_ports is None or ixn_ports == []:
            self.create_vports(snappi)
            return
        loc_snappi = [p.location for p in snappi.ports]
        loc_ixn = [
            v['location']
            for v in ixn_ports
        ]
        common = list(set(loc_snappi) & set(loc_ixn))
        add_ports = list(set(loc_snappi) ^ set(common))
        remove_ports = list(set(loc_ixn) ^ set(common))
        if len(remove_ports) > 0:
            seq_ids = [
                (v['id'], v['location'])
                for v in ixn_ports if v['location'] in remove_ports
            ]
            self.release_vports(seq_ids)
            self.remove_vports(seq_ids)
        if len(add_ports) > 0:
            if len(common) > 0:
                seq_ids = [
                    (v['id'], v['location']) 
                    for v in ixn_ports if v['location'] in common
                ]
                self.release_vports(seq_ids)
            self.create_vports(snappi)
        if len(common) == len(snappi.ports):
            self.set_vport_xpath(snappi)
            self.set_l1config(snappi)
        return

    def set_vport_xpath(self, snappi):
        vports = self._api._request(
            'GET', '%s/vport' % self._api._ixnetwork.href
        )
        for p in snappi.ports:
            for v in vports:
                if v['location'] == p.location:
                    p._properties['xpath'] = '/vport[%d]' % v['id']
                    p._properties['vid'] = v['id']
        return

    def create_vports(self, snappi):
        vports = []
        seq_id = 1
        for p in snappi.ports:
            xpath = '/vport[%d]' % seq_id
            vports.append(
                {
                    'xpath': xpath,
                    'location': p.location,
                    'name': p.name,
                }
            )
            p._properties['xpath'] = xpath
            p._properties['vid'] = seq_id
            seq_id += 1
        self._importconfig({'vport': vports})
        self.set_l1config(snappi)
        return vports

    def set_l1config(self, snappi):
        vports = list()
        update = False
        for p in snappi.ports:
            id = p._properties.get('vid')
            url = '%s/vport/%d' % (self._api._ixnetwork.href, id)
            vport = self._api._request('Get', url)
            xpath = p._properties.get('xpath')
            res = self._api._request('GET', '%s/l1Config' % url)
            curr = self._api._request(
                'GET', '%s/l1Config/%s' % (url, res['currentType'])
            )
            v = dict()
            v['xpath'] = xpath
            v['l1Config'] = {
                'xpath': '%s/l1Config' % xpath,
                'currentType': res['currentType'],
                res['currentType']: {
                    'xpath': '%s/l1Config/%s' % (xpath, res['currentType'])
                }
            }
            s = self._SPEED_MAP[self._ports[p.name]['speed']]
            if curr['speed'] != s:
                v['l1Config'][res['currentType']]['speed'] = s
            if curr['media'] != self._ports[p.name]['media']:
                v['l1Config'][res['currentType']]['media'] =\
                    self._ports[p.name]['media']
            if 'linkdown' in vport['connectionState'].lower():
                update = True
            vports.append(v)
        if update:
            self._importconfig({'vport': vports})
        return

    def _build_port_collection(self, snappi):
        loc = self._parse_location(':', snappi)
        self._ports = dict()
        for i, l in enumerate(loc):
            name = snappi.ports[i].name
            p = dict()
            p['chassis'] = l[0]
            p['card'] = l[1]
            p['port'] = l[-1]
            for l1 in snappi.layer1:
                if name in l1.port_names:
                    p.update(l1.serialize('dict'))
            self._get_rg_status_(
                l[0], int(l[1]), int(l[-1]), p['speed']
            )
            self._ports[name] = p
        return

    def _get_rg_status_(self, chassis_ip, card, port, speed):
        url = '%savailableHardware/chassis/%d/card/%d'
        agg_support = None
        res = None
        chassis_id = self._ip_to_chassis_[chassis_ip]['id']
        url = url % (self._api._ixnetwork.href, chassis_id, card)
        if self._ip_to_chassis_[chassis_ip].get('card') is None:
            res = self._api._request('GET', url)
            agg_support = res['aggregationSupported']
        else:
            agg_support =\
                self._ip_to_chassis_[chassis_ip]['card'][card][
                    'aggregationSupported'
                ]
        if res is not None:
            if self._ip_to_chassis_[chassis_ip].get('card') is None:
                self._ip_to_chassis_[chassis_ip]['card'] = dict()
            self._ip_to_chassis_[chassis_ip]['card'].update({card: res})
        if agg_support:
            self._set_rg_on_card(url, port, speed)
            res = self._api._request('GET', url)
            self._ip_to_chassis_[chassis_ip]['card'].update({card: res})
        return

    def _set_rg_on_card(self, url, port, speed):
        res = self._api._request('GET', '%s/aggregation' % url)
        for agg in res:
            if '%s/port/%d' % (url, port) not in agg['resourcePorts']:
                continue
            if '%s/port/%d' % (url, port) in agg['activePorts']:
                if len(agg['resourcePorts']) == len(agg['activePorts']):
                    continue
            if re.match(self._SPEED_MODE_MAP[speed], res['mode']) is not None:
                break
            agg_url = agg["links"][0]["href"]
            for m in agg['availableModes']:
                reg = re.match(self._SPEED_MODE_MAP[speed], res['mode'])
                if reg is None:
                    continue
                payload = {
                    'mode': m
                }
                self._request('PATCH', agg_url, payload)
        return

    def assign_location(self, snappi, vports):
        pass

    def remove_vports(self, seq_ids):
        url_patt = '{}/vport/{}'
        for id in seq_ids:
            url = url_patt.format(self._api._ixnetwork.href, id[0])
            self._api._request('DELETE', url)

    def release_vports(self, seq_ids):
        url = '%s/vport/operations/releaseport' % self._api._ixnetwork.href
        vports = [
            '%s/vport/%d' % (self._api._ixnetwork.href, id[0])
            for id in seq_ids if id[1] != ''
        ]
        payload = {
            'arg1': vports
        }
        self._api._request('POST', url, payload)
        return

    def get_chassis(self, snappi):
        chassis = list(set(self._parse_location(0, snappi)))
        available_chassis = [
            c.Ip
            for c in self._api._ixnetwork.AvailableHardware.Chassis.find()
        ]
        common = list(set(chassis) & set(available_chassis))
        need_to_connect = list(set(chassis) ^ set(common))
        need_to_remove = list(set(available_chassis) ^ set(common))
        if len(need_to_connect) > 0:
            self.connect_to_chassis(need_to_connect)
        if len(need_to_remove) > 0:
            self.remove_chassis(need_to_remove)
        self._ip_to_chassis()

    def _ip_to_chassis(self):
        chassis = self._api._request(
            'GET',
            url='%s/availableHardware/chassis' % self._api._ixnetwork.href
        )
        for c in chassis:
            self._ip_to_chassis_[c['ip']] = c
        return

    def connect_to_chassis(self, chassis_list, timeout=60):
        for c in chassis_list:
            self._api._ixnetwork.AvailableHardware.Chassis.add(Hostname=c)
        url = '%s/availableHardware/chassis' % self._api._ixnetwork.href
        count = 0
        while True:
            res = self._api._request('GET', url)
            state = None
            if res != []:
                state = [
                    True if c['state'] == 'ready' else False
                    for c in res
                ]
                if all(state):
                    break
            if count >= timeout:
                if state is not None:
                    state = [
                        (c['hostname'], c['state'])
                        for c in res
                    ]
                raise Exception("Could not connect to chassis {}".format(
                    state
                ))
            count += 1
        return

    def remove_chassis(self, chassis_list):
        chassis = self._api._ixnetwork.AvailableHardware.Chassis.find()
        for c in chassis:
            if c.Ip in chassis_list:
                c.remove()
        return
