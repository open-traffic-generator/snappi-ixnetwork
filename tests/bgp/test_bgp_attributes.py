def test_bgp_attributes(api, utils):
    """
    Configure bgp attributes and validate against restpy
    """
    config = api.config()
    community = "1:2"
    aspaths = [1, 2]
    med = 50
    origin = "egp"

    v4_rr_attr = {
        "address": "200.1.0.1",
        "prefix": "32",
        "count": "1000",
        "step": "2",
    }

    v6_rr_attr = {
        "address": "4000::1",
        "prefix": "64",
        "count": "500",
        "step": "3",
    }

    (port,) = config.ports.port(name="tx", location=utils.settings.ports[0])

    config.options.port_options.location_preemption = True
    ly = config.layer1.layer1()[-1]
    ly.name = "ly"
    ly.port_names = [port.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    (device,) = config.devices.device(name="device")

    # device config
    eth = device.ethernets.add()
    eth.name = "eth"
    eth.port_name = port.name
    eth.mac = "00:00:00:00:00:11"
    ipv4 = eth.ipv4_addresses.add()
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    bgpv4 = device.bgp
    bgpv4.router_id = "192.0.0.1"
    bgpv4_int = bgpv4.ipv4_interfaces.add()
    bgpv4_int.ipv4_name = ipv4.name
    bgpv4_peer = bgpv4_int.peers.add()
    bgpv4_peer.name = "rx_bgpv4"
    bgpv4_peer.as_type = "ebgp"
    bgpv4_peer.peer_address = "22.1.1.1"
    bgpv4_peer.as_number = 65200

    rr = bgpv4_peer.v4_routes.add(name="rr")
    rr.addresses.add(
        address=v4_rr_attr["address"],
        prefix=int(v4_rr_attr["prefix"]),
        count=int(v4_rr_attr["count"]),
        step=int(v4_rr_attr["step"]),
    )

    # Community
    manual_as_community = rr.communities.add()
    manual_as_community.type = manual_as_community.MANUAL_AS_NUMBER
    manual_as_community.as_number = int(community.split(":")[0])
    manual_as_community.as_custom = int(community.split(":")[1])

    # AS Path
    as_path = rr.as_path
    as_path_segment = as_path.segments.add()
    as_path_segment.type = as_path_segment.AS_SEQ
    as_path_segment.as_numbers = aspaths

    # MED
    rr.advanced.multi_exit_discriminator = med

    # Origin
    rr.advanced.origin = rr.advanced.EGP

    # v6
    ipv6 = eth.ipv6_addresses.add()
    ipv6.name = "ipv6"
    ipv6.address = "2000::1"
    ipv6.prefix = 64
    ipv6.gateway = "2000::2"
    bgpv6 = device.bgp
    bgpv6.router_id = "192.0.0.1"
    bgpv6_int =  bgpv6.ipv6_interfaces.add()
    bgpv6_int.ipv6_name = ipv6.name
    bgp6_peer = bgpv6_int.peers.add()
    bgp6_peer.name = "rx_bgpv6"
    bgp6_peer.as_type = "ebgp"
    bgp6_peer.peer_address = "2000::2"
    bgp6_peer.as_number = 65200

    rrv6 = bgp6_peer.v6_routes.add(name="rrv6")
    rrv6.addresses.add(
        address=v6_rr_attr["address"],
        prefix=int(v6_rr_attr["prefix"]),
        count=int(v6_rr_attr["count"]),
        step=int(v6_rr_attr["step"]),
    )

    # Community
    manual_as_community = rrv6.communities.add()
    manual_as_community.type = manual_as_community.MANUAL_AS_NUMBER
    manual_as_community.as_number = int(community.split(":")[0])
    manual_as_community.as_custom = int(community.split(":")[1])

    # As Path
    as_path = rrv6.as_path
    as_path_segment = as_path.segments.add()
    as_path_segment.type = as_path_segment.AS_SEQ
    as_path_segment.as_numbers = aspaths

    # MED
    rrv6.advanced.multi_exit_discriminator = med

    # Origin
    rrv6.advanced.origin = rr.advanced.EGP

    api.set_config(config)

    validate_route_range(api, v4_rr_attr, v6_rr_attr)

    validate_community_config(api, community, aspaths, med, origin)


def validate_route_range(api, v4_rr_attr, v6_rr_attr):
    v4_rr = (
        api._ixnetwork.Topology.find()
        .DeviceGroup.find()
        .NetworkGroup.find()
        .Ipv4PrefixPools.find()
    )
    assert v4_rr.NetworkAddress == v4_rr_attr["address"]
    assert v4_rr.NumberOfAddressesAsy == v4_rr_attr["count"]
    assert v4_rr.PrefixAddrStep == v4_rr_attr["step"]
    assert v4_rr.PrefixLength == v4_rr_attr["prefix"]

    v6_rr = (
        api._ixnetwork.Topology.find()
        .DeviceGroup.find()
        .NetworkGroup.find()
        .Ipv6PrefixPools.find()
    )
    assert v6_rr.NetworkAddress == v6_rr_attr["address"]
    assert v6_rr.NumberOfAddressesAsy == v6_rr_attr["count"]
    assert v6_rr.PrefixAddrStep == v6_rr_attr["step"]
    assert v6_rr.PrefixLength == v6_rr_attr["prefix"]


def validate_community_config(api, community, aspaths, med, origin):
    """
    Validate BGP Attributes Config
    """

    ixnetwork = api._ixnetwork
    bgpv4 = (
        ixnetwork.Topology.find()
        .DeviceGroup.find()
        .NetworkGroup.find()
        .Ipv4PrefixPools.find()
        .BgpIPRouteProperty.find()
    )

    bgpv6 = (
        ixnetwork.Topology.find()
        .DeviceGroup.find()
        .NetworkGroup.find()
        .Ipv6PrefixPools.find()
        .BgpV6IPRouteProperty.find()
    )

    # bgpv4_attributes validation
    as_number = bgpv4.BgpCommunitiesList.find().AsNumber
    last_two_octets = bgpv4.BgpCommunitiesList.find().LastTwoOctets
    assert as_number == community.split(":")[0]
    assert last_two_octets == community.split(":")[1]

    as_paths = bgpv4.AsPathASString
    as_paths = as_paths[0].replace('}', '').replace('{', '')
    as_paths = as_paths.split(',')
    as_paths = [int(ele) for ele in as_paths]
    assert as_paths == aspaths

    assert int(bgpv4.MultiExitDiscriminator.Values[0]) == med
    assert bgpv4.Origin.Values[0] == origin

    # bgpv6_attributes validation
    as_number = bgpv6.BgpCommunitiesList.find().AsNumber
    last_two_octets = bgpv6.BgpCommunitiesList.find().LastTwoOctets
    assert as_number == community.split(":")[0]
    assert last_two_octets == community.split(":")[1]

    as_paths = bgpv6.AsPathASString
    as_paths = as_paths[0].replace('}', '').replace('{', '')
    as_paths = as_paths.split(',')
    as_paths = [int(ele) for ele in as_paths]
    assert as_paths == aspaths

    assert int(bgpv6.MultiExitDiscriminator.Values[0]) == med
    assert bgpv6.Origin.Values[0] == origin
