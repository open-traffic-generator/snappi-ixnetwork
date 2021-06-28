import pytest


@pytest.mark.skip(reason="need to fix pfcpause")
def test_flow_sizes(api, settings):
    """
    This will test supported Flow Size
            'float': 'fixed',
            'int': 'fixed',
            'SizeIncrement': 'increment',
            'SizeRandom': 'random',
    """
    config = api.config()
    api.set_config(config)

    tx, rx = config.ports.port(name="tx", location=settings.ports[0]).port(
        name="rx", location=settings.ports[1]
    )

    l1 = config.layer1.layer1()[0]
    l1.name = "l1"
    l1.port_names = [rx.name, tx.name]
    l1.media = settings.media
    l1.speed = settings.speed

    fixed_size, increment_size, random_size = (
        config.flows.flow(name="Fixed Size")
        .flow(name="Increment Size")
        .flow(name="Random Size")
    )

    fixed_size.tx_rx.port.tx_name = tx.name
    fixed_size.tx_rx.port.rx_name = rx.name
    (pfc,) = fixed_size.packet.pfcpause()
    pfc.src.value = "00:AB:BC:AB:BC:AB"
    pfc.dst.value = "00:AB:BC:AB:BC:AB"
    pfc.ether_type
    pfc.class_enable_vector.value = 65535
    pfc.control_op_code
    pfc.pause_class_0.value = 65535
    pfc.pause_class_1.value = 65535
    pfc.pause_class_2.value = 65535
    pfc.pause_class_3.value = 65535
    pfc.pause_class_4.value = 65535
    pfc.pause_class_5.value = 65535
    pfc.pause_class_6.value = 65535
    pfc.pause_class_7.value = 65535
    fixed_size.size.fixed = 44

    increment_size.tx_rx.port.tx_name = tx.name
    increment_size.tx_rx.port.rx_name = rx.name
    increment_size.size.increment.start = 100
    increment_size.size.increment.step = 10
    increment_size.size.increment.end = 1200

    random_size.tx_rx.port.tx_name = tx.name
    random_size.tx_rx.port.rx_name = rx.name
    random_size.size.random.min = 72
    random_size.size.random.max = 1518

    api.set_config(config)


if __name__ == "__main__":
    pytest.main(["-s", __file__])
