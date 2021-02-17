import pytest


@pytest.fixture
def ixn_session(api):
    api.set_config(api.config())
    ixn = api.assistant.Session.Ixnetwork
    return ixn


@pytest.mark.l1_manual
@pytest.mark.parametrize('speed', ['speed_100_gbps', 'speed_40_gbps',
                                   'speed_25_gbps', 'speed_10_gbps',
                                   'speed_50_gbps'])
def test_layer1_uhd(api, ixn_session, utils, speed):
    """
    Layer1 test specific to UHD devices.
    script will fetch the port location and figure out the card group,
    then configures the port with supported speed in each test iteration.
    Validation: validate the speed configured and the fanout ports via
    restpy.
    """
    chassis = ixn_session.AvailableHardware.Chassis.find()
    if chassis.ChassisType != 'Ixia UHD':
        pytest.skip('Skipping as the chassis is not UHD')
    port = utils.settings.ports[0].split('/')[-1]
    config = api.config()
    res_map, index = get_resource(chassis, speed, port)
    port = 'localuhd/' + res_map[speed][0][0]
    assert res_map is not None
    p1 = config.ports.port(
        name='p1',
        location=port)[-1]
    l1 = config.layer1.layer1()[-1]
    l1.port_names = [p1.name]
    l1.speed = speed
    l1.media = utils.settings.media
    l1.auto_negotiate = True
    l1.ieee_media_defaults = False
    l1.auto_negotiation.link_training = False
    l1.auto_negotiation.rs_fec = True
    api.set_config(config)
    card = chassis.Card.find()[index]

    assert card.Aggregation.find().Mode == res_map[speed][-1]
    assert len(card.Aggregation.find().ActivePorts) == len(res_map[speed][0])


def get_resource(chassis, speed, port):
    res_map = get_speed_to_resource_map(chassis)
    for mod in res_map:
        for p in res_map[mod][speed][0]:
            import re
            if re.match('^%s' % port, p):
                return (res_map[mod], mod)
    return None


def get_speed_to_resource_map(chassis):
    rg_map = {
        'uhdOneHundredEightByHundredGigNonFanOut': {
            'name': 'speed_100_gbps', 'fanout': 8
        },
        'uhdOneHundredEightByFortyGigNonFanOut': {
            'name': 'speed_40_gbps', 'fanout': 8
        },
        'uhdOneHundredThirtyTwoByTwentyFiveGigFanOut': {
            'name': 'speed_25_gbps', 'fanout': 32
        },
        'uhdOneHundredThirtyTwoByTenGigFanOut': {
            'name': 'speed_10_gbps', 'fanout': 32
        },
        'uhdOneHundredSixteenByFiftyGigFanOut': {
            'name': 'speed_50_gbps', 'fanout': 16
        },
    }
    ret = dict()
    cards = chassis.Card.find()
    non_fanout = 8
    for i, card in enumerate(cards):
        if not card.AggregationSupported:
            continue
        modes = card.Aggregation.find().AvailableModes
        val = dict()
        stop = (non_fanout * (i + 1)) + 1
        start = (non_fanout * i) + 1
        for m in modes:
            if m not in rg_map:
                continue
            fan = int(rg_map[m]['fanout'] / non_fanout)
            if fan > 1:
                val[rg_map[m]['name']] = ([
                    "{}.{}".format(x, d)
                    for x in range(start, stop) for d in range(1, fan + 1)
                ], m)
            else:
                val[rg_map[m]['name']] = ([
                    str(x) for x in range(start, stop)
                ], m)
        ret[i] = val
    return ret
