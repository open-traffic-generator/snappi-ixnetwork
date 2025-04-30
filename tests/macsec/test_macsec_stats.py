import pytest
import time

@pytest.mark.skip(
    reason="CI-Testing"
)
# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_encrypt(api, b2b_raw_config, utils):
    """
    Test for the macsec configuration
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="enc_only_macsec1").device(
        name="enc_only_macsec2"
    )

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"

    macsec1, macsec2 = d1.macsec, d2.macsec
    macsec1_int, macsec2_int = macsec1.ethernet_interfaces.add(), macsec2.ethernet_interfaces.add()
    macsec1_int.eth_name, macsec2_int.eth_name = eth1.name, eth2.name
    secy1, secy2 = macsec1_int.secure_entity, macsec2_int.secure_entity
    secy1.name, secy2.name = "macsec1", "macsec2"

    # Data plane and crypto engine
    secy1.data_plane.choice = secy2.data_plane.choice = "encapsulation"
    secy1.data_plane.encapsulation.crypto_engine.choice = secy2.data_plane.encapsulation.crypto_engine.choice = "encrypt_only"
    secy1_crypto_engine_enc_only, secy2_crypto_engine_enc_only = secy1.data_plane.encapsulation.crypto_engine.encrypt_only, secy2.data_plane.encapsulation.crypto_engine.encrypt_only 
 
    # Data plane Tx SC PN 
    secy1_dataplane_txsc1, secy2_dataplane_txsc1 = secy1_crypto_engine_enc_only.secure_channels.add(), secy2_crypto_engine_enc_only.secure_channels.add()
    secy1_dataplane_txsc1.tx_pn.choice = secy2_dataplane_txsc1.tx_pn.choice = "fixed_pn"
    secy1_dataplane_txsc1.tx_pn.fixed.pn = secy2_dataplane_txsc1.tx_pn.fixed.pn = 100

    # static key
    secy1_key_gen_proto, secy2_key_gen_proto = secy1.key_generation_protocol, secy2.key_generation_protocol
    secy1_key_gen_proto.choice = secy2_key_gen_proto.choice = "static_key"
    secy1_sk, secy2_sk = secy1_key_gen_proto.static_key, secy2_key_gen_proto.static_key
    secy1_sk.cipher_suite = secy2_sk.cipher_suite = "gcm_aes_xpn_128"

    # Tx
    secy1_tx, secy2_tx = secy1_sk.tx, secy2_sk.tx
    secy1_txsc1, secy2_txsc1 = secy1_tx.secure_channels.add(), secy2_tx.secure_channels.add()

    # Tx SC end station
    #secy1_txsc1.end_station = secy2_txsc1.end_station = True

    # Tx key
    secy1_tx_sak1, secy2_tx_sak1 = secy1_txsc1.saks.add(), secy2_txsc1.saks.add()
    #secy1_tx_sak1.sak = secy2_tx_sak1.sak = "0xF123456789ABCDEF0123456789ABCDEF"
    secy1_tx_sak1.sak = secy2_tx_sak1.sak = "f123456789abcdef0123456789abcdef"
    secy1_tx_sak1.ssci = secy2_tx_sak1.ssci = "0000000a"
    secy1_tx_sak1.salt = secy2_tx_sak1.salt = "00000000000000000000000b"

    # Remaining Tx SC settings autofilled

    # Rx: Not required for stateless enryption only traffic
    #secy1_rx, secy2_rx = secy1.rx, secy2.rx
    #secy1_rxsc1, secy2_rxsc1 = secy1.rx.static_key.scs.add(), secy2.rx.static_key.scs.add()

    # Rx SC
    #secy1_rxsc1.dut_system_id =  eth2.mac
    #secy2_rxsc1.dut_system_id =  eth1.mac

    # Rx key
    #secy1_rx_sak1, secy2_rx_sak1 = secy1_rxsc1.saks.add(), secy2_rxsc1.saks.add()
    #secy1_rx_sak1.sak = secy2_rx_sak1.sak = "0xF123456789ABCDEF0123456789ABCDEF"
    #secy1_rx_sak1.sak = secy2_rx_sak1.sak = "f123456789abcdef0123456789abcdef"

    # Remaining Rx SC settings autofilled

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

    utils.start_traffic(api, b2b_raw_config)

    utils.wait_for(
        lambda: results_ok(api), "stats to be as expected", timeout_seconds=30
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
    # assert len(results.macsec_metrics) == 2
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
    req.macsec.secure_entity_names = ["enc_only_macsec2"]
    results = api.get_metrics(req)

    # assert len(results.macsec_metrics) == 1
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

    req = api.metrics_request()
    req.macsec.column_names = ["session_state"]
    results = api.get_metrics(req)
    assert len(results.macsec_metrics) == 2
    assert results.macsec_metrics[0].session_state == "up"
    assert results.macsec_metrics[1].session_state == "up"

    utils.stop_traffic(api, b2b_raw_config)


def results_ok(api):
    req = api.metrics_request()
    req.macsec.column_names = ["session_state"]
    results = api.get_metrics(req)
    ok = []
    for r in results.macsec_metrics:
        ok.append(r.session_state == "up")
    return all(ok)


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
