import pytest


def test_flow_rates(api, settings):
    """
    This will test supported Flow Rate
        - unit (Union[pps, bps, kbps, mbps, gbps, line]): The value is a unit of this
        - value (Union[float, int]): The actual rate
    """
    config = api.config()

    tx, rx = (
        config.ports
        .port(name='tx', location=settings.ports[0])
        .port(name='rx', location=settings.ports[1])
    )

    l1 = config.layer1.layer1()[0]
    l1.name = 'l1'
    l1.port_names = [rx.name, tx.name]
    l1.media = settings.media
    l1.speed = settings.speed

    rate_line, rate_pps, rate_bps, rate_kbps, rate_gbps = (
        config.flows
        .flow(name='rate_line')
        .flow(name='rate_pps')
        .flow(name='rate_bps')
        .flow(name='rate_kbps')
        .flow(name='rate_gbps')
    )

    rate_line.tx_rx.port.tx_name = tx.name
    rate_line.tx_rx.port.rx_name = rx.name
    rate_line.rate.percentage = 100

    rate_pps.tx_rx.port.tx_name = tx.name
    rate_pps.tx_rx.port.rx_name = rx.name
    rate_pps.rate.pps = 2000

    rate_bps.tx_rx.port.tx_name = tx.name
    rate_bps.tx_rx.port.rx_name = rx.name
    rate_bps.rate.bps = 700

    rate_kbps.tx_rx.port.tx_name = tx.name
    rate_kbps.tx_rx.port.rx_name = rx.name
    rate_kbps.rate.kbps = 800

    rate_gbps.tx_rx.port.tx_name = tx.name
    rate_gbps.tx_rx.port.rx_name = rx.name
    rate_gbps.rate.gbps = 10

    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
