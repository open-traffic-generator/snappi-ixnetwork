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
    phb = ['PHB_DEFAULT'] + ['PHB_CS%d' % i for i in range(1, 8)] + \
          ['PHB_AF%d' % i for j in range(11, 51, 10) for i in range(j, j + 3)]
    phb = phb + ['PHB_EF46']
    af_ef = [
        '10', '12', '14', '18', '20', '22', '26',
        '28', '30', '34', '36', '38', '46'
    ]
    for i, p in enumerate(phb):
        ipv4.priority.choice = 'dscp'
        ipv4.priority.dscp.phb.value = getattr(ipv4.priority.dscp, p)
        api.set_config(b2b_raw_config)
        if i == 0:
            attrs = {'Default PHB': str(i)}
        elif i > 0 and i < 8:
            attrs = {'Class selector PHB': str(i * 8)}
        elif i > 7 and i < (len(phb) - 1):
            attrs = {'Assured forwarding PHB': af_ef[i - 8]}
        else:
            attrs = {'Expedited forwarding PHB': af_ef[-1]}
        utils.validate_config(api, 'ipv4', **attrs)


def test_ip_priority_tos(api, b2b_raw_config, utils):
    """
    Configure a raw IPv4 flow with,
    - all Tos values

    Validate,
    - Fetch the IPv4 header config via restpy and validate
      against expected
    """

    f = b2b_raw_config.flows[0]
    # import snappi
    # b2b_raw_config = snappi.Api().config()
    # f = b2b_raw_config.flows.flow()[-1]
    # ipv4 = f.packet.ethernet().ipv4()[-1]
    # ipv4 = ipv4.ipv4
    ipv4 = f.packet.ethernet().ipv4()[-1]
    api.set_config(b2b_raw_config)
    precedence = [
        "PRE_ROUTINE",
        "PRE_PRIORITY",
        "PRE_IMMEDIATE",
        "PRE_FLASH",
        "PRE_FLASH_OVERRIDE",
        "PRE_CRITIC_ECP",
        "PRE_INTERNETWORK_CONTROL",
        "PRE_NETWORK_CONTROL"
    ]
    flag = 0
    for i, p in enumerate(precedence):
        ipv4.priority.choice = 'tos'
        ipv4.priority.tos.precedence.value = getattr(ipv4.priority.tos, p)
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
        utils.validate_config(api, 'ipv4', **attrs)
        flag = int(not flag)
