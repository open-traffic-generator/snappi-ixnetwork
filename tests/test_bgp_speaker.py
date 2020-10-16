import pytest
from abstract_open_traffic_generator.port import Port
from abstract_open_traffic_generator.device import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *

def test_bgp_speaker(serializer, api):
    """This is the configuration steps in https://github.com/Azure/sonic-mgmt/blob/master/tests/bgp/test_bgp_speaker.py

    logging.info("Start exabgp on ptf")
    for i in range(0, 3):
        local_ip = str(speaker_ips[i].ip)
        ptfhost.exabgp(name="bgps%d" % i,
                       state="started",
                       local_ip=local_ip,
                       router_id=local_ip,
                       peer_ip=lo_addr,
                       local_asn=bgp_speaker_asn,
                       peer_asn=mg_facts['minigraph_bgp_asn'],
                       port=str(port_num[i]))
    
    """
    local_ip = ['10.10.0.1', '20.20.0.1', '30.30.0.1']
    peer_ip = '40.40.0.1'
    local_asn = '65000'
    peer_asn = '65000'
    device = Device(name='device',
                    device_count=3,
                    choice=Bgpv4(name='bgpv4',
                                 router_id=Pattern(local_ip),
                                 dut_ipv4_address=Pattern(peer_ip),
                                 as_number = Pattern(local_asn),
                                 dut_as_number = Pattern(peer_asn),
                                 ipv4=Ipv4(name='ipv4',
                                           local_ip=Pattern(local_ip),
                                           peer_ip=Pattern(peer_ip),
                                           ethernet=Ethernet()
                                           )
                                )
                    )
    
    port = Port(name='port1', devices=[device])
    config = Config(ports=[port])
    state = State(ConfigState(config=config, state='set'))
    print(serializer.json(state))
    api.set_state(state)

    api.set_state(State(FlowTransmitState(state='start')))