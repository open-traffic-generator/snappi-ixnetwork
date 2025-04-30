@pytest.mark.skip(
    reason="CI-Testing"
)
def test_vlan_fields(api, b2b_raw_config_vports, utils, tx_vport, rx_vport):
    """
    Configure three raw vlan flows with ,
    - fixed pattern for all vlan fields
    - list pattern for all vlan fields
    - counter pattern for all vlan fields
    Validate,
    - fetch the vlan header via restpy framework and validate
      against expected.
    """
    # fixed
    flow1 = b2b_raw_config_vports.flows[0]
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    # Vlan fields config
    priority = 7
    cfi = 1
    vlan_id = 1

    flow1.packet.ethernet().vlan()
    eth, vlan = flow1.packet[0], flow1.packet[1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.value = priority

    vlan.cfi.value = cfi

    vlan.id.value = vlan_id

    vlan.tpid.value = vlan.tpid.X8100

    # List
    flow2 = b2b_raw_config_vports.flows.flow(name="f2")[-1]
    flow2.tx_rx.port.tx_name = tx_vport.name
    flow2.tx_rx.port.rx_name = rx_vport.name
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    # Vlan fields config
    priority_lst = [i for i in range(7)]
    cfi_lst = [0, 1]
    vlan_id_lst = [i for i in range(4094)]
    tpid_lst = [i for i in range(65536)]

    flow2.packet.ethernet().vlan()
    eth, vlan = flow2.packet[0], flow2.packet[1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.values = priority_lst

    vlan.cfi.values = cfi_lst

    vlan.id.values = vlan_id_lst

    vlan.tpid.values = tpid_lst

    # Counter
    flow3 = b2b_raw_config_vports.flows.flow(name="f3")[-1]
    flow3.tx_rx.port.tx_name = tx_vport.name
    flow3.tx_rx.port.rx_name = rx_vport.name
    source = "00:0C:29:E3:53:EA"
    destination = "00:0C:29:E3:53:F4"
    ether_type = 33024

    flow3.packet.ethernet().vlan()
    eth, vlan = flow3.packet[0], flow3.packet[1]
    eth.src.value = source
    eth.dst.value = destination
    eth.ether_type.value = ether_type

    vlan.priority.increment.start = 0
    vlan.priority.increment.step = 1
    vlan.priority.increment.count = 7

    vlan.cfi.increment.start = 0
    vlan.cfi.increment.step = 1
    vlan.cfi.increment.count = 1

    vlan.id.increment.start = 1
    vlan.id.increment.step = 1
    vlan.id.increment.count = 4094

    vlan.tpid.increment.start = 0
    vlan.tpid.increment.step = 1
    vlan.tpid.increment.count = 65535

    api.set_config(b2b_raw_config_vports)

    # fixed validation
    f1_attrs = {
        "VLAN Priority": str(priority),
        "Canonical Format Indicator": str(cfi),
        "VLAN-ID": str(vlan_id),
        "Protocol-ID": format(vlan.tpid.X8100, "x"),
    }
    utils.validate_config(api, "f1", "vlan", **f1_attrs)

    # list validation
    f2_attrs = {
        "VLAN Priority": [str(p) for p in priority_lst],
        "Canonical Format Indicator": [str(c) for c in cfi_lst],
        "VLAN-ID": [str(v) for v in vlan_id_lst],
        "Protocol-ID": [format(v, "x") for v in tpid_lst],
    }
    utils.validate_config(api, "f2", "vlan", **f2_attrs)

    # counter validation
    f3_attrs = {
        "VLAN Priority": (
            str(vlan.priority.increment.start),
            str(vlan.priority.increment.step),
            str(vlan.priority.increment.count),
        ),
        "Canonical Format Indicator": (
            str(vlan.cfi.increment.start),
            str(vlan.cfi.increment.step),
            str(vlan.cfi.increment.count),
        ),
        "VLAN-ID": (
            str(vlan.id.increment.start),
            str(vlan.id.increment.step),
            str(vlan.id.increment.count),
        ),
        "Protocol-ID": (
            str(vlan.tpid.increment.start),
            str(vlan.tpid.increment.step),
            str(vlan.tpid.increment.count),
        ),
    }

    utils.validate_config(api, "f3", "vlan", **f3_attrs)
