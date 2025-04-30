import pytest
import time

@pytest.mark.skip(
    reason="CI-Testing"
)
# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_encrypt_with_mka(api, b2b_raw_config, utils):
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
    # MACsec
    ####################
    macsec1, macsec2 = d1.macsec, d2.macsec
    macsec1_int, macsec2_int = macsec1.ethernet_interfaces.add(), macsec2.ethernet_interfaces.add()
    macsec1_int.eth_name, macsec2_int.eth_name = eth1.name, eth2.name
    secy1, secy2 = macsec1_int.secure_entity, macsec2_int.secure_entity
    secy1.name, secy2.name = "macsec1", "macsec2"

    # Data plane and crypto engine
    secy1.data_plane.choice = secy2.data_plane.choice = "encapsulation"
    secy1.data_plane.encapsulation.crypto_engine.choice = secy2.data_plane.encapsulation.crypto_engine.choice = "encrypt_only"

    # Data plane and crypto engine
    secy1.data_plane.choice = secy2.data_plane.choice = "encapsulation"
    secy1.data_plane.encapsulation.crypto_engine.choice = secy2.data_plane.encapsulation.crypto_engine.choice = "encrypt_only"
    secy1_crypto_engine_enc_only, secy2_crypto_engine_enc_only = secy1.data_plane.encapsulation.crypto_engine.encrypt_only, secy2.data_plane.encapsulation.crypto_engine.encrypt_only 

    # Data plane Tx SC
    secy1_dataplane_txsc1, secy2_dataplane_txsc1 = secy1_crypto_engine_enc_only.secure_channels.add(), secy2_crypto_engine_enc_only.secure_channels.add()

    # Fixed PN
    secy1_dataplane_txsc1.tx_pn.choice = secy2_dataplane_txsc1.tx_pn.choice = "fixed_pn"
 
    # OR incrementing PN
    #secy1_dataplane_txsc1.tx_pn.choice = secy2_dataplane_txsc1.tx_pn.choice = "incrementing_pn"
    #secy1_dataplane_txsc1.tx_pn.incrementing.starting_pn = secy2_dataplane_txsc1.tx_pn.incrementing.starting_pn = 1
    #secy1_dataplane_txsc1.tx_pn.incrementing.count = secy2_dataplane_txsc1.tx_pn.incrementing.count = 10000

    ####################
    # MKA
    ####################
    secy1_key_gen_proto, secy2_key_gen_proto = secy1.key_generation_protocol, secy2.key_generation_protocol
    secy1_key_gen_proto.choice = secy2_key_gen_proto.choice = "mka"
    kay1, kay2 = secy1_key_gen_proto.mka, secy2_key_gen_proto.mka
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

    kay1_psk1.start_offset_time.hh = kay2_psk1.start_offset_time.hh = 0 
    kay1_psk1.start_offset_time.mm = kay2_psk1.start_offset_time.mm = 0

    kay1_psk1.end_offset_time.hh = kay2_psk1.end_offset_time.hh = 0
    kay1_psk1.end_offset_time.hh = kay2_psk1.end_offset_time.hh = 22

    # PSK 2
    kay1_psk2, kay2_psk2 = kay1_psk_chain.add(), kay2_psk_chain.add()
    kay1_psk2.cak_name = kay2_psk2.cak_name = "0xF123456789ABCDEF0123456789ABCDEFF123456789ABCDEF0123456789ABCD02"
    kay1_psk2.cak_value = kay2_psk2.cak_value = "0xF123456789ABCDEF0123456789ABCD02"

    kay1_psk2.start_offset_time.hh = kay2_psk2.start_offset_time.hh = 0
    kay1_psk2.start_offset_time.mm = kay2_psk2.start_offset_time.mm = 22 

    kay1_psk2.end_offset_time.hh = kay2_psk2.end_offset_time.hh = 0
    kay1_psk2.end_offset_time.hh = kay2_psk2.end_offset_time.hh = 0

    # Rekey mode
    kay1_rekey_mode, kay2_rekey_mode = kay1.basic.rekey_mode, kay2.basic.rekey_mode
    #kay1_rekey_mode.choice = kay2_rekey_mode.choice = "dont_rekey"
    kay1_rekey_mode.choice = kay2_rekey_mode.choice = "timer_based"
    kay1_rekey_timer_based, kay2_rekey_timer_based = kay1_rekey_mode.timer_based, kay2_rekey_mode.timer_based
    kay1_rekey_timer_based.choice = kay2_rekey_timer_based.choice = "fixed_count"
    kay1_rekey_timer_based.fixed_count = kay2_rekey_timer_based.fixed_count = 20
    kay1_rekey_timer_based.interval = kay2_rekey_timer_based.interval = 200

    # Remaining basic properties autofilled

    # Key server
    kay1_key_server, kay2_key_server = kay1.key_server, kay2.key_server
    kay1_key_server.cipher_suite = kay2_key_server.cipher_suite = "gcm_aes_128"

    # Tx SC
    kay1_tx, kay2_tx = kay1.tx, kay2.tx 
    kay1_txsc1, kay2_txsc1 = kay1_tx.secure_channels.add(), kay2_tx.secure_channels.add()
    kay1_txsc1.name, kay2_txsc1.name = "txsc1", "txsc2"
    kay1_txsc1.system_id, kay2_txsc1.system_id = eth1.mac, eth2.mac 
    # Remaining Tx SC settings autofilled

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

    # Flow
    f1 = config.flows.flow(name="f1")[-1]

    # IP
    f1.packet.ethernet().macsec().ipv4()

    # DSCP
    ip = f1.packet[-1]
    ip.priority.choice = ip.priority.DSCP
    ip.priority.dscp.phb.values = [
    ip.priority.dscp.phb.CS2,
    ip.priority.dscp.phb.CS1,
    ip.priority.dscp.phb.CS5,
    ]
    ip.priority.dscp.ecn.value = 3


    # Ethernet/VLAN traffic from secY to secY endpoints
    #f1.tx_rx.device.tx_names = [secy1.name]
    #f1.tx_rx.device.rx_names = [secy2.name]

    # Ethernet/VLAN traffic from ethernet to ethernet endpoints
    #f1.tx_rx.device.tx_names = [eth1.name]
    #f1.tx_rx.device.rx_names = [eth2.name]

    # IPv4 traffic from IP to IP endpoints
    f1.tx_rx.device.tx_names = [ip1.name]
    f1.tx_rx.device.rx_names = [ip2.name]

    # Rate
    f1.rate.pps = 10

    utils.start_traffic(api, config)

    ####################
    # MKA stats
    ####################
    utils.wait_for(
        lambda: results_mka_ok(api), "stats to be as expected", timeout_seconds=20
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
    req.mka.peer_names = ["enc_only_macsec1"]
    results = api.get_metrics(req)
    assert len(results.mka_metrics) == 1
    assert results.mka_metrics[0].name == "enc_only_macsec1"
    print(f"\n\nMKA Result : enc_only_macsec1\n")
    for mka_res in results.mka_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[mka_res.name][i]
            if "session_state" in enum:
                assert getattr(mka_res, enum) == val
            else:
                assert getattr(mka_res, enum) >= val
            print(f"{enum} : {getattr(mka_res, enum)}")

    req = api.metrics_request()
    req.mka.peer_names = ["enc_only_macsec2"]
    results = api.get_metrics(req)
    assert len(results.mka_metrics) == 1
    assert results.mka_metrics[0].name == "enc_only_macsec2"
    print(f"\n\nMKA Result : enc_only_macsec2")
    for mka_res in results.mka_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[mka_res.name][i]
            if "session_state" in enum:
                assert getattr(mka_res, enum) == val
            else:
                assert getattr(mka_res, enum) >= val
            print(f"{enum} : {getattr(mka_res, enum)}")


    ####################
    # MACsec stats
    ####################
    utils.wait_for(
        lambda: results_macsec_ok(api), "stats to be as expected", timeout_seconds=30
    )

    enums = [
        "session_state",
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
        "enc_only_macsec1": ["up", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "enc_only_macsec2": ["up", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    }
    req = api.metrics_request()
    req.macsec.secure_entity_names = ["enc_only_macsec1"]
    results = api.get_metrics(req)
    assert len(results.macsec_metrics) == 1
    assert results.macsec_metrics[0].name == "enc_only_macsec1"
    print(f"\n\nMACsec Result : enc_only_macsec1")
    for macsec_res in results.macsec_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[macsec_res.name][i]
            if "session_state" in enum:
                assert getattr(macsec_res, enum) == val
            else:
                assert getattr(macsec_res, enum) >= val
            print(f"{enum} : {getattr(macsec_res, enum)}")

    req = api.metrics_request()
    req.macsec.secure_entity_names = ["enc_only_macsec2"]
    results = api.get_metrics(req)

    assert len(results.macsec_metrics) == 1
    assert results.macsec_metrics[0].name == "enc_only_macsec2"
    print(f"\n\nMACsec Result : enc_only_macsec2")
    for macsec_res in results.macsec_metrics:
        for i, enum in enumerate(enums):
            val = expected_results[macsec_res.name][i]
            if "session_state" in enum:
                assert getattr(macsec_res, enum) == val
            else:
                assert getattr(macsec_res, enum) >= val
            print(f"{enum} : {getattr(macsec_res, enum)}")

    utils.stop_traffic(api, config)


def results_macsec_ok(api):
    req = api.metrics_request()
    req.macsec.column_names = ["session_state"]
    results = api.get_metrics(req)
    ok = []
    for r in results.macsec_metrics:
        ok.append(r.session_state == "up")
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
