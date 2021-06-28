import pytest


def test_diff_latency_mode(api, b2b_raw_config, tx_port, rx_port):
    """
    Ixnetwork supports only one latency mode for all flows

    Validation:
    ixNetwork should throw an error to provide only same mode
        for all flows
    """
    SIZE = 1024

    # flow -f1 config
    f1 = b2b_raw_config.flows[0]

    f1.size.fixed = SIZE

    f1.metrics.enable = True
    f1.metrics.loss = True
    f1.metrics.timestamps = True

    # flow -f2 config
    f2 = b2b_raw_config.flows.flow(name="f2")[-1]
    f2.tx_rx.port.tx_name = tx_port.name
    f2.tx_rx.port.rx_name = rx_port.name

    f2.size.fixed = SIZE

    f2.metrics.enable = True
    f2.metrics.loss = True
    f2.metrics.timestamps = True

    # Latency Config
    f1.metrics.latency.enable = True
    f1.metrics.latency.mode = f1.metrics.latency.STORE_FORWARD

    f2.metrics.latency.enable = True
    f2.metrics.latency.mode = f2.metrics.latency.CUT_THROUGH

    try:
        api.set_config(b2b_raw_config)
    except Exception as e:
        print(e)
        assert str(e) == "Latency mode needs to be same for all flows"


if __name__ == "__main__":
    pytest.main(["-s", __file__])
