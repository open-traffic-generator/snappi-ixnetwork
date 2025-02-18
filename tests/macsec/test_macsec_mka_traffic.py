import pytest
import time


# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_stateless_encryption_with_mka(api, b2b_raw_config, utils):
    """
    Test for the macsec configuration
    """
    config = b2b_raw_config
    api.set_config(api.config())
    config.flows.clear()
    #ixnetwork = api._ixnetwork

    p1, p2 = config.ports
    d1, d2 = config.devices.device(name="enc_only_macsec1").device(name="enc_only_macsec2")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"

    ####################
    # MKA
    ####################
    mka1, mka2 = d1.mka, d2.mka
    mka1_int, mka2_int = mka1.ethernet_interfaces.add(), mka2.ethernet_interfaces.add()
    mka1_int.eth_name, mka2_int.eth_name = eth1.name, eth2.name
    kay1, kay2 = mka1_int.kay, mka2_int.kay
    kay1.name, kay2.name = "mka1", "mka2"

    # Basic properties
    kay1.basic.key_derivation_function = kay2.basic.key_derivation_function = "aes_cmac_128"

    # Key source: PSK
    kay1_key_src, kay2_key_src = kay1.basic.key_source, kay2.basic.key_source
    kay1_key_src.choice = kay2_key_src.choice = "psk"
    kay1_psk_chain, kay2_psk_chain = kay1_key_src.psks, kay2_key_src.psks

    # PSK 1
    kay1_psk1, kay2_psk1 = kay1_psk_chain.add(), kay2_psk_chain.add()
    kay1_psk1.cak_name = kay2_psk1.cak_name = "0xF123456789ABCDEF0123456789ABCDEFF123456789ABCDEF0123456789ABCD01"
    kay1_psk1.cak_value = kay2_psk1.cak_value = "0xF123456789ABCDEF0123456789ABCD01"
    kay1_psk1.start_time = kay2_psk1.start_time = "00:00"
    kay1_psk1.end_time = kay2_psk1.end_time = "00:00"

    # PSK 2
    kay1_psk2, kay2_psk2 = kay1_psk_chain.add(), kay2_psk_chain.add()
    kay1_psk2.cak_name = kay2_psk2.cak_name = "0xF123456789ABCDEF0123456789ABCDEFF123456789ABCDEF0123456789ABCD02"
    kay1_psk2.cak_value = kay2_psk2.cak_value = "0xF123456789ABCDEF0123456789ABCD02"
    kay1_psk2.start_time = kay2_psk2.start_time = "00:00"
    kay1_psk2.end_time = kay2_psk2.end_time = "00:00"

    # Rekey mode
    kay1_rekey_mode, kay2_rekey_mode = kay1.basic.rekey_mode, kay2.basic.rekey_mode
    kay1_rekey_mode.choice = kay2_rekey_mode.choice = "dont_rekey"
    #kay1_rekey_mode.choice = kay2_rekey_mode.choice = "timer_based"
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

    ####################
    # MACsec
    ####################
    macsec1, macsec2 = d1.macsec, d2.macsec
    macsec1_int, macsec2_int = macsec1.ethernet_interfaces.add(), macsec2.ethernet_interfaces.add()
    macsec1_int.eth_name, macsec2_int.eth_name = eth1.name, eth2.name
    secy1, secy2 = macsec1_int.secy, macsec2_int.secy
    secy1.name, secy2.name = "macsec1", "macsec2"

    # crypto_engine
    secy1.crypto_engine.choice = secy2.crypto_engine.choice = "stateless_encryption_only" 
    secy1.crypto_engine.stateless_encryption_only.tx_pn.choice = "incrementing_pn"

    ####################
    # Traffic
    ####################
    # Gratuitous ARP is sent so that DUT can learn our IP. Grat ARP source/destination are local address
    # DUT MAC needs to be configured manually stateless encyption only engine cannot decrypt any packet including DUT ARP
    ip1.address = "10.1.1.1"
    ip2.address = "10.1.1.2"

    ip1.prefix = 24
    ip2.prefix = 24

    ip1.gateway = ip2.address
    ip2.gateway = ip1.address

    ip1.gateway_mac.choice = "value"
    ip1.gateway_mac.value = eth2.mac

    ip2.gateway_mac.choice = "value"
    ip2.gateway_mac.value = eth1.mac

    #traffic
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [secy1.name]
    f1.tx_rx.device.rx_names = [secy2.name]
    f1.packet.ethernet()
    f1.rate.pps = 10

    utils.start_traffic(api, config)

    ####################
    # MACsec stats
    ####################
    print("Sleeping for 30 secoonds: start")
    time.sleep(30)
    print("Sleeping for 30 secoonds: end")
    utils.wait_for(
        lambda: results_macsec_ok(api), "stats to be as expected", timeout_seconds=10
    )

    enums = [
        "out_pkts_protected",
        "out_pkts_encrypted",
        "in_pkts_ok",
        "in_pkts_bad",
        "in_pkts_bad_tag",
        "in_pkts_late",
        "in_pkts_no_sci",
        "in_pkts_not_using_sa",
        "in_pkts_not_valid",
        "in_pkts_unknown_sci",
        "in_pkts_unused_sa",
        "in_pkts_invalid",
        "in_pkts_untagged",
        "out_octets_protected",
        "out_octets_encrypted",
        "in_octets_validated",
        "in_octets_decrypted",
    ]
    expected_results = {
        "enc_only_macsec1": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "enc_only_macsec2": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    }
    req = api.metrics_request()
    req.macsec.secy_names = ["enc_only_macsec1"]
    results = api.get_metrics(req)
    assert len(results.macsec_metrics) == 1
    assert results.macsec_metrics[0].name == "enc_only_macsec1"
    print(f"MACsec Result : enc_only_macsec1")
    for macsec_res in results.macsec_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[macsec_res.name][i]
            if "session_state" in enum:
                assert getattr(macsec_res, enum) == val
            else:
                assert getattr(macsec_res, enum) >= val
            print(f"{enum} : {getattr(macsec_res, enum)}")

    req = api.metrics_request()
    req.macsec.secy_names = ["enc_only_macsec2"]
    results = api.get_metrics(req)

    assert len(results.macsec_metrics) == 1
    assert results.macsec_metrics[0].name == "enc_only_macsec2"
    print(f"MACsec Result : enc_only_macsec2")
    for macsec_res in results.macsec_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[macsec_res.name][i]
            if "session_state" in enum:
                assert getattr(macsec_res, enum) == val
            else:
                assert getattr(macsec_res, enum) >= val
            print(f"{enum} : {getattr(macsec_res, enum)}")

    ####################
    # MKA stats
    ####################
    utils.wait_for(
        lambda: results_mka_ok(api), "stats to be as expected", timeout_seconds=10
    )
    enums = [
        "mkpdu_tx",
        "mkpdu_rx",
        "live_peer_count",
        "potential_peer_count",
        "latest_key_tx_peer_count",
        "latest_key_rx_peer_count",
        "malformed_mkpdu",
        "icv_mismatch",
    ]
    expected_results = {
        "enc_only_macsec1": [0, 0, 0, 0, 0, 0, 0, 0],
        "enc_only_macsec2": [0, 0, 0, 0, 0, 0, 0, 0],
    }
    req = api.metrics_request()
    req.mka.kay_names = ["enc_only_macsec1"]
    results = api.get_metrics(req)
    assert len(results.mka_metrics) == 1
    assert results.mka_metrics[0].name == "enc_only_macsec1"
    print(f"MKA Result : enc_only_macsec1")
    for mka_res in results.mka_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[mka_res.name][i]
            if "session_state" in enum:
                assert getattr(mka_res, enum) == val
            else:
                assert getattr(mka_res, enum) >= val
            print(f"{enum} : {getattr(mka_res, enum)}")

    req = api.metrics_request()
    req.mka.kay_names = ["enc_only_macsec2"]
    results = api.get_metrics(req)
    assert len(results.mka_metrics) == 1
    assert results.mka_metrics[0].name == "enc_only_macsec2"
    print(f"MKA Result : enc_only_macsec2")
    for mka_res in results.mka_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[mka_res.name][i]
            if "session_state" in enum:
                assert getattr(mka_res, enum) == val
            else:
                assert getattr(mka_res, enum) >= val
            print(f"{enum} : {getattr(mka_res, enum)}")

    utils.stop_traffic(api, config)


def results_macsec_ok(api):
    #req = api.metrics_request()
    #req.macsec.column_names = ["session_state"]
    #results = api.get_metrics(req)
    ok = []
    #for r in results.macsec_metrics:
    #    ok.append(r.session_state == "up")
    return all(ok)

def results_mka_ok(api):
    req = api.metrics_request()
    req.mka.column_names = ["session_state"]
    results = api.get_metrics(req)
    ok = []
    for r in results.mka_metrics:
        ok.append(r.session_state == "up")
    return all(ok)

if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
