def test_counter_ip_dscp(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - all Dscp values

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """
    f = b2b_raw_config.flows[0]
    f.packet.ethernet().ipv4()
    ipv4 = f.packet[1]
    phb = ['DEFAULT'] + ['CS%d' % i for i in range(1, 8)] + \
          ['AF%d' % i for j in range(11, 51, 10) for i in range(j, j + 3)]
    phb = phb + ['EF46']
    af_ef = [
        '10', '12', '14', '18', '20', '22', '26',
        '28', '30', '34', '36', '38', '46'
    ]
    for i, p in enumerate(phb):
        # https://github.com/open-traffic-generator/snappi/issues/25
        # currently assigning the choice as work around
        ipv4.priority.choice = ipv4.priority.DSCP
        ipv4.priority.dscp.phb.value = getattr(ipv4.priority.dscp.phb, p)
        api.set_config(b2b_raw_config)
        if i == 0:
            attrs = {'Default PHB': str(i)}
        elif i > 0 and i < 8:
            attrs = {'Class selector PHB': str(i * 8)}
        elif i > 7 and i < (len(phb) - 1):
            attrs = {'Assured forwarding PHB': af_ef[i - 8]}
        else:
            attrs = {'Expedited forwarding PHB': af_ef[-1]}
        utils.validate_config(api, 'f1', 'ipv4', **attrs)


def test_ip_priority_tos(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - all Tos values

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """

    f = b2b_raw_config.flows[0]
    ipv4 = f.packet.ethernet().ipv4()[-1]
    api.set_config(b2b_raw_config)
    precedence = [
        "ROUTINE",
        "PRIORITY",
        "IMMEDIATE",
        "FLASH",
        "FLASH_OVERRIDE",
        "CRITIC_ECP",
        "INTERNETWORK_CONTROL",
        "NETWORK_CONTROL"
    ]
    flag = 0
    for i, p in enumerate(precedence):
        # https://github.com/open-traffic-generator/snappi/issues/25
        # currently assigning the choice as work around
        ipv4.priority.choice = ipv4.priority.TOS
        ipv4.priority.tos.precedence.value = getattr(
            ipv4.priority.tos.precedence, p
        )
        ipv4.priority.tos.delay.value = flag
        ipv4.priority.tos.throughput.value = flag
        ipv4.priority.tos.reliability.value = flag
        ipv4.priority.tos.monetary.value = flag
        ipv4.priority.tos.unused.value = flag

        api.set_config(b2b_raw_config)
        attrs = {
            'Precedence': str(i),
            'Delay': str(flag),
            'Throughput': str(flag),
            'Reliability': str(flag),
            'Monetary': str(flag),
            # 'Unused': str(flag) <restpy returns 0 for unused even if set 1>
        }
        utils.validate_config(api, 'f1', 'ipv4', **attrs)
        flag = int(not flag)
