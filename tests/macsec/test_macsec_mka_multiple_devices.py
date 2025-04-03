import pytest
import time


# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_encrypt_with_mka_multiple_devices(api, b2b_raw_config, utils):
    """
    Test for the macsec configuration
    """
    config = b2b_raw_config
    api.set_config(api.config())
    config.flows.clear()
    #ixnetwork = api._ixnetwork

    p1, p2 = config.ports
    d1, d2, d3, d4 = config.devices.device(name="enc_only_macsec1").device(name="enc_only_macsec2").device(name="enc_only_macsec3").device(name="enc_only_macsec4")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth3, eth4 = d3.ethernets.add(), d4.ethernets.add()

    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth3.connection.port_name, eth4.connection.port_name = p1.name, p2.name

    eth1.mac, eth2.mac = "00:00:11:00:00:01", "00:00:22:00:00:02"
    eth3.mac, eth4.mac = "00:00:33:00:00:01", "00:00:44:00:00:02"

    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    ip3, ip4 = eth3.ipv4_addresses.add(), eth4.ipv4_addresses.add()

    eth1.name, eth2.name = "eth1", "eth2"
    eth3.name, eth4.name = "eth3", "eth4"

    ip1.name, ip2.name = "ip1", "ip2"
    ip3.name, ip4.name = "ip3", "ip4"

    ####################
    # MACsec
    ####################
    macsec1, macsec2 = d1.macsec, d2.macsec
    macsec3, macsec4 = d3.macsec, d4.macsec

    macsec1_int, macsec2_int = macsec1.ethernet_interfaces.add(), macsec2.ethernet_interfaces.add()
    macsec3_int, macsec4_int = macsec3.ethernet_interfaces.add(), macsec4.ethernet_interfaces.add()

    macsec1_int.eth_name, macsec2_int.eth_name = eth1.name, eth2.name
    macsec3_int.eth_name, macsec4_int.eth_name = eth3.name, eth4.name

    secy1, secy2 = macsec1_int.secure_entity, macsec2_int.secure_entity
    secy3, secy4 = macsec3_int.secure_entity, macsec4_int.secure_entity

    secy1.name, secy2.name = "macsec1", "macsec2"
    secy3.name, secy4.name = "macsec3", "macsec4"

    # Data plane and crypto engine
    secy1.data_plane.choice = secy2.data_plane.choice = "encapsulation"
    secy3.data_plane.choice = secy4.data_plane.choice = "encapsulation"

    secy1.data_plane.encapsulation.crypto_engine.choice = secy2.data_plane.encapsulation.crypto_engine.choice = "encrypt_only"
    secy3.data_plane.encapsulation.crypto_engine.choice = secy4.data_plane.encapsulation.crypto_engine.choice = "encrypt_only"

    # Data plane and crypto engine
    secy1_crypto_engine_enc_only, secy2_crypto_engine_enc_only = secy1.data_plane.encapsulation.crypto_engine.encrypt_only, secy2.data_plane.encapsulation.crypto_engine.encrypt_only 
    secy3_crypto_engine_enc_only, secy4_crypto_engine_enc_only = secy3.data_plane.encapsulation.crypto_engine.encrypt_only, secy4.data_plane.encapsulation.crypto_engine.encrypt_only 

    # Data plane Tx SC
    secy1_dataplane_txsc1, secy2_dataplane_txsc1 = secy1_crypto_engine_enc_only.secure_channels.add(), secy2_crypto_engine_enc_only.secure_channels.add()
    secy3_dataplane_txsc1, secy4_dataplane_txsc1 = secy3_crypto_engine_enc_only.secure_channels.add(), secy4_crypto_engine_enc_only.secure_channels.add()

    # Fixed PN
    secy1_dataplane_txsc1.tx_pn.choice = secy2_dataplane_txsc1.tx_pn.choice = "fixed_pn"
    secy3_dataplane_txsc1.tx_pn.choice = secy4_dataplane_txsc1.tx_pn.choice = "fixed_pn"
 
    ####################
    # MKA
    ####################
    secy1_key_gen_proto, secy2_key_gen_proto = secy1.key_generation_protocol, secy2.key_generation_protocol
    secy3_key_gen_proto, secy4_key_gen_proto = secy3.key_generation_protocol, secy4.key_generation_protocol

    secy1_key_gen_proto.choice = secy2_key_gen_proto.choice = "mka"
    secy3_key_gen_proto.choice = secy4_key_gen_proto.choice = "mka"

    kay1, kay2 = secy1_key_gen_proto.mka, secy2_key_gen_proto.mka
    kay3, kay4 = secy3_key_gen_proto.mka, secy4_key_gen_proto.mka

    kay1.name, kay2.name = "mka1", "mka2"
    kay3.name, kay4.name = "mka3", "mka4"

    # Basic properties
    kay1.basic.key_derivation_function = kay2.basic.key_derivation_function = "aes_cmac_128"
    kay3.basic.key_derivation_function = kay4.basic.key_derivation_function = "aes_cmac_128"

    # Key source: PSK
    kay1_key_src, kay2_key_src = kay1.basic.key_source, kay2.basic.key_source
    kay3_key_src, kay4_key_src = kay3.basic.key_source, kay4.basic.key_source

    kay1_key_src.choice = kay2_key_src.choice = "psk"
    kay3_key_src.choice = kay4_key_src.choice = "psk"

    kay1_psk_chain, kay2_psk_chain = kay1_key_src.psks, kay2_key_src.psks
    kay3_psk_chain, kay4_psk_chain = kay3_key_src.psks, kay4_key_src.psks

    # PSK 1
    kay1_psk1, kay2_psk1 = kay1_psk_chain.add(), kay2_psk_chain.add()
    kay3_psk1, kay4_psk1 = kay3_psk_chain.add(), kay4_psk_chain.add()

    kay1_psk1.cak_name = kay2_psk1.cak_name = kay3_psk1.cak_name = kay4_psk1.cak_name = "0xF123456789ABCDEF0123456789ABCDEFF123456789ABCDEF0123456789ABCD01"
    kay1_psk1.cak_value = kay2_psk1.cak_value = kay3_psk1.cak_value = kay4_psk1.cak_value = "0xF123456789ABCDEF0123456789ABCD01"

    kay1_psk1.start_offset_time.hh = kay2_psk1.start_offset_time.hh = kay3_psk1.start_offset_time.hh = kay4_psk1.start_offset_time.hh = 0
    kay1_psk1.start_offset_time.mm = kay2_psk1.start_offset_time.mm = kay3_psk1.start_offset_time.mm = kay4_psk1.start_offset_time.mm = 0

    kay1_psk1.end_offset_time.hh = kay2_psk1.end_offset_time.hh = kay3_psk1.end_offset_time.hh = kay4_psk1.end_offset_time.hh = 0
    kay1_psk1.end_offset_time.hh = kay2_psk1.end_offset_time.hh = kay3_psk1.end_offset_time.hh = kay4_psk1.end_offset_time.hh = 0

    # Rekey mode
    kay1_rekey_mode, kay2_rekey_mode, kay3_rekey_mode, kay4_rekey_mode = kay1.basic.rekey_mode, kay2.basic.rekey_mode, kay3.basic.rekey_mode, kay4.basic.rekey_mode
    kay1_rekey_mode.choice = kay2_rekey_mode.choice = kay3_rekey_mode.choice = kay4_rekey_mode.choice = "dont_rekey"

    # Remaining basic properties autofilled

    # Key server
    kay1_key_server, kay2_key_server, kay3_key_server, kay4_key_server = kay1.key_server, kay2.key_server, kay3.key_server, kay4.key_server
    kay1_key_server.cipher_suite = kay2_key_server.cipher_suite = kay3_key_server.cipher_suite = kay4_key_server.cipher_suite = "gcm_aes_128"

    # Tx SC
    kay1_tx, kay2_tx, kay3_tx, kay4_tx = kay1.tx, kay2.tx, kay3.tx, kay4.tx 
    kay1_txsc1, kay2_txsc1, kay3_txsc1, kay4_txsc1 = kay1_tx.secure_channels.add(), kay2_tx.secure_channels.add(), kay3_tx.secure_channels.add(), kay4_tx.secure_channels.add()

    kay1_txsc1.name, kay2_txsc1.name, kay3_txsc1.name, kay4_txsc1.name = "txsc1", "txsc2", "txsc3", "txsc4"
    kay1_txsc1.system_id, kay2_txsc1.system_id, kay3_txsc1.system_id, kay4_txsc1.system_id = eth1.mac, eth2.mac, eth3.mac, eth4.mac
    # Remaining Tx SC settings autofilled

    ####################
    # Traffic
    ####################
    # Gratuitous ARP is sent so that DUT can learn our IP. Grat ARP source/destination are local address
    # DUT MAC needs to be configured manually stateless encyption only engine cannot decrypt any packet including DUT ARP
    ip1.address = "10.1.1.1"
    ip2.address = "10.1.1.2"
    ip3.address = "10.1.1.3"
    ip4.address = "10.1.1.4"

    ip1.prefix = ip2.prefix = ip3.prefix = ip4.prefix =24

    ip1.gateway = ip2.address
    ip2.gateway = ip1.address

    ip3.gateway = ip4.address
    ip4.gateway = ip3.address

    ip1.gateway_mac.choice = "value"
    ip1.gateway_mac.value = eth2.mac

    ip2.gateway_mac.choice = "value"
    ip2.gateway_mac.value = eth1.mac

    ip3.gateway_mac.choice = "value"
    ip3.gateway_mac.value = eth4.mac

    ip4.gateway_mac.choice = "value"
    ip4.gateway_mac.value = eth3.mac

    # Flows
    f1 = config.flows.flow(name="f1")[-1]
    f2 = config.flows.flow(name="f2")[-1]

    # IP
    f1.packet.ethernet().macsec().ipv4()
    f2.packet.ethernet().macsec().ipv4()

    # DSCP
    f1_ip = f1.packet[-1]
    f2_ip = f2.packet[-1]

    f1_ip.priority.choice = f1_ip.priority.DSCP
    f1_ip.priority.dscp.phb.values = [
    f1_ip.priority.dscp.phb.CS2,
    f1_ip.priority.dscp.phb.CS1,
    f1_ip.priority.dscp.phb.CS5,
    ]

    f2_ip.priority.choice = f2_ip.priority.DSCP
    f2_ip.priority.dscp.phb.values = [
    f2_ip.priority.dscp.phb.CS2,
    f2_ip.priority.dscp.phb.CS1,
    f2_ip.priority.dscp.phb.CS5,
    ]
 
    f1_ip.priority.dscp.ecn.value = 3
    f2_ip.priority.dscp.ecn.value = 3

    # IPv4 traffic from IP to IP endpoints
    f1.tx_rx.device.tx_names = [ip1.name]
    f2.tx_rx.device.tx_names = [ip3.name]

    f1.tx_rx.device.rx_names = [ip2.name]
    f2.tx_rx.device.rx_names = [ip4.name]

    # Rate
    f1.rate.pps = 5
    f2.rate.pps = 5

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
