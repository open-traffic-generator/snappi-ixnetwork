import snappi
import pytest

def test_device_vxlan(api, b2b_raw_config):
    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name='d1').device(name='d2')

    e1, e2 = d1.ethernets.ethernet()[-1], d2.ethernets.ethernet()[-1]
    e1.port_name, e2.port_name = p1.name, p2.name
    e1.name, e2.name = 'e1', 'e2'
    e1.mac, e2.mac = '00:01:00:00:00:01', '00:01:00:00:00:02'

    # v4_loopback
    l1 = d1.ipv4_loopbacks.add()
    l1.name = "loopback1"
    l1.eth_name = 'e1'
    l1.address = '221.0.1.1'

    # v6_loopback
    l2 = d1.ipv6_loopbacks.add()
    l2.name = "loopback2"
    l2.eth_name = 'e1'
    l2.address = '2000::1'

    # Create two vxlan tunnels, v4&v6
    vxlanv4 = d1.vxlan.v4_tunnels.add()
    vxlanv6 = d1.vxlan.v6_tunnels.add()

    vxlanv4.vni = 1
    vxlanv4.source_interface = l1.name
    vxlanv4.name = "vxlanv4"

    # unicast communication
    vtep = vxlanv4.destination_ip_mode.unicast.vteps.add()
    vtep.remote_vtep_address = "120.1.1.2"
    vtep.arp_suppression_cache.add("00:1b:6e:80:00:01", "20.1.1.1")
    vtep.arp_suppression_cache.add("00:1b:6e:80:00:02", "20.1.1.2")

    # device connected to VXLAN
    e3 = d1.ethernets.ethernet()[-1]
    e3.name = "e3"
    e3.mac = "00:01:00:00:00:08"
    e3.connection.vxlan_name = vxlanv4.name
    i3 = e3.ipv4_addresses.add()
    i3.name = "i3"
    i3.address = "30.0.0.1"
    i3.gateway = "30.0.0.2"

    # unicast communication
    vtep = vxlanv4.destination_ip_mode.unicast.vteps.add()
    vtep.remote_vtep_address = "120.1.1.2"
    vtep.arp_suppression_cache.add("00:1b:6e:80:00:01", "20.1.1.1")
    vtep.arp_suppression_cache.add("00:1b:6e:80:00:02", "20.1.1.2")

    vxlanv6.vni = 2
    vxlanv6.source_interface = l2.name
    vxlanv6.name = "vxlanv6"

    # multicast communication
    vxlanv6.destination_ip_mode.multicast.address = "ff03::1"

    print(b2b_raw_config.serialize())
    api.set_config(b2b_raw_config)


if __name__ == "__main__":
    pytest.main(["-s", __file__])

