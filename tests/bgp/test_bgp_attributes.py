def test_bgp_attributes(api, utils):
    """
    Configure bgp attributes and validate against restpy
    """
    config = api.config()
    community = "1:2"
    aspaths = [1, 2]
    med = 50
    origin = 'egp'

    port, = (
        config.ports
        .port(name='tx', location=utils.settings.ports[0])
    )

    config.options.port_options.location_preemption = True
    ly = config.layer1.layer1()[-1]
    ly.name = 'ly'
    ly.port_names = [port.name]
    ly.ieee_media_defaults = False
    ly.auto_negotiate = False
    ly.speed = utils.settings.speed
    ly.media = utils.settings.media

    device, = (
        config.devices
        .device(name="device", container_name=port.name)
    )

    # device config
    eth = device.ethernet
    eth.name = "eth"
    eth.mac = '00:00:00:00:00:11'
    ipv4 = eth.ipv4
    ipv4.name = "ipv4"
    ipv4.address = "21.1.1.1"
    ipv4.prefix = 24
    ipv4.gateway = "21.1.1.2"
    bgpv4 = ipv4.bgpv4
    bgpv4.name = "rx_bgpv4"
    bgpv4.local_address = '21.1.1.1'
    bgpv4.as_type = "ebgp"
    bgpv4.dut_address = "22.1.1.1"
    bgpv4.as_number = 65200

    rr = bgpv4.bgpv4_routes.bgpv4route(name="rr")[-1]
    rr.addresses.bgpv4routeaddress(address="200.1.0.1",
                                   prefix=32)

    # Community
    manual_as_community = (
        rr.communities.bgpcommunity()[-1])
    manual_as_community.community_type = manual_as_community.MANUAL_AS_NUMBER
    manual_as_community.as_number = int(community.split(":")[0])
    manual_as_community.as_custom = int(community.split(":")[1])

    # AS Path
    as_path = rr.as_path
    as_path_segment = as_path.as_path_segments.bgpaspathsegment()[-1]
    as_path_segment.segment_type = as_path_segment.AS_SEQ
    as_path_segment.as_numbers = aspaths

    # MED
    rr.advanced.multi_exit_discriminator = med

    # Origin
    rr.advanced.origin = rr.advanced.EGP

    # v6
    ipv6 = eth.ipv6
    ipv6.name = "ipv6"
    ipv6.address = "2000::1"
    ipv6.prefix = 64
    ipv6.gateway = "2000::2"
    bgpv6 = ipv6.bgpv6
    bgpv6.name = "rx_bgpv6"
    bgpv6.local_address = "2000::1"
    bgpv6.as_type = "ebgp"
    bgpv6.dut_address = "2000::2"
    bgpv6.as_number = 65200

    rrv6 = bgpv6.bgpv6_routes.bgpv6route(name="rrv6")[-1]
    rrv6.addresses.bgpv6routeaddress(address="4000::1",
                                     prefix=64)

    # Community
    manual_as_community = (
        rrv6.communities.bgpcommunity()[-1])
    manual_as_community.community_type = manual_as_community.MANUAL_AS_NUMBER
    manual_as_community.as_number = int(community.split(":")[0])
    manual_as_community.as_custom = int(community.split(":")[1])

    # As Path
    as_path = rrv6.as_path
    as_path_segment = as_path.as_path_segments.bgpaspathsegment()[-1]
    as_path_segment.segment_type = as_path_segment.AS_SEQ
    as_path_segment.as_numbers = aspaths

    # MED
    rrv6.advanced.multi_exit_discriminator = med

    # Origin
    rrv6.advanced.origin = rr.advanced.EGP

    api.set_config(config)

    validate_community_config(api,
                              community,
                              aspaths,
                              med,
                              origin)


def validate_community_config(api,
                              community,
                              aspaths,
                              med,
                              origin):
    """
    Validate BGP Attributes Config
    """

    ixnetwork = api._ixnetwork
    bgpv4 = (ixnetwork.Topology.find().
             DeviceGroup.find().NetworkGroup.find().
             Ipv4PrefixPools.find().BgpIPRouteProperty.find())

    bgpv6 = (ixnetwork.Topology.find().
             DeviceGroup.find().NetworkGroup.find().
             Ipv6PrefixPools.find().BgpV6IPRouteProperty.find())

    # bgpv4_attributes validation
    as_number = (bgpv4.BgpCommunitiesList.find().AsNumber)
    last_two_octets = (bgpv4.BgpCommunitiesList.find().LastTwoOctets)
    assert as_number == community.split(":")[0]
    assert last_two_octets == community.split(":")[1]

    as_paths = bgpv4.AsPathASString
    as_paths = [ele.replace('<', '').replace('>', '').split(",")
                for ele in as_paths][0]
    as_paths = [int(ele) for ele in as_paths]
    assert as_paths == aspaths

    assert int(bgpv4.MultiExitDiscriminator.Values[0]) == med
    assert bgpv4.Origin.Values[0] == origin

    # bgpv6_attributes validation
    as_number = (bgpv6.BgpCommunitiesList.find().AsNumber)
    last_two_octets = (bgpv6.BgpCommunitiesList.find().LastTwoOctets)
    assert as_number == community.split(":")[0]
    assert last_two_octets == community.split(":")[1]

    as_paths = bgpv6.AsPathASString
    as_paths = [ele.replace('<', '').replace('>', '').split(",")
                for ele in as_paths][0]
    as_paths = [int(ele) for ele in as_paths]
    assert as_paths == aspaths

    assert int(bgpv6.MultiExitDiscriminator.Values[0]) == med
    assert bgpv6.Origin.Values[0] == origin
