import pytest
import time


# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_mka(api, b2b_raw_config, utils):
    """
    Test for the mka configuration
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="mka_dev1").device(name="mka_dev2")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    eth1.name, eth2.name = "eth1", "eth2"

    mka1, mka2 = d1.mka, d2.mka
    mka1_int, mka2_int = mka1.ethernet_interfaces.add(), mka2.ethernet_interfaces.add()
    mka1_int.eth_name, mka2_int.eth_name = eth1.name, eth2.name
    kay1, kay2 = mka1_int.kay, mka2_int.kay
    kay1.name, kay2.name = "mka1", "mka2"

    # Basic properties
    # Key source
    kay1.basic.key_source.choice = kay2.basic.key_source.choice = "psk"

    # Rekey mode
    kay1_rekey_mode, kay2_rekey_mode = kay1.basic.rekey_mode, kay2.basic.rekey_mode
    kay1_rekey_mode.choice = kay2_rekey_mode.choice = "timer_based"
    kay1_rekey_timer_based, kay2_rekey_timer_based = kay1_rekey_mode.timer_based, kay2_rekey_mode.timer_based
    kay1_rekey_timer_based.choice = kay2_rekey_timer_based.choice = "fixed_count"
    kay1_rekey_timer_based.fixed_count = kay2_rekey_timer_based.fixed_count = 20
    kay1_rekey_timer_based.interval = kay2_rekey_timer_based.interval = 200

    # Remaining basic properties autofilled

    # Tx SC
    kay1_txsc1, kay2_txsc1 = kay1.txscs.add(), kay2.txscs.add() 
    kay1_txsc1.name, kay2_txsc1.name = "txsc1", "txsc2"
    kay1_txsc1.system_id, kay2_txsc1.system_id = eth1.mac, eth2.mac 
    # Remaining Tx SC settings autofilled

    utils.start_traffic(api, b2b_raw_config)
    print("Sleeping for 30 secoonds: start")
    time.sleep(30)
    print("Sleeping for 30 secoonds: end")
    utils.stop_traffic(api, b2b_raw_config)


def results_ok(api):
    #req = api.metrics_request()
    #req.mka.column_names = ["session_state"]
    #results = api.get_metrics(req)
    ok = []
    #for r in results.mka_metrics:
    #    ok.append(r.session_state == "up")
    return all(ok)


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
