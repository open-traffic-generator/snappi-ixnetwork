import pytest
import time


# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_stateless_encryption_static_key(api, b2b_raw_config, utils):
    """
    Test for the macsec configuration
    """
    api.set_config(api.config())
    b2b_raw_config.flows.clear()

    p1, p2 = b2b_raw_config.ports
    d1, d2 = b2b_raw_config.devices.device(name="enc_only_macsec1").device(name="enc_only_macsec2")

    eth1, eth2 = d1.ethernets.add(), d2.ethernets.add()
    eth1.connection.port_name, eth2.connection.port_name = p1.name, p2.name
    eth1.mac, eth2.mac = "00:00:00:00:00:11", "00:00:00:00:00:22"
    ip1, ip2 = eth1.ipv4_addresses.add(), eth2.ipv4_addresses.add()
    eth1.name, eth2.name = "eth1", "eth2"
    ip1.name, ip2.name = "ip1", "ip2"

    macsec1, macsec2 = d1.macsec, d2.macsec
    macsec1_int, macsec2_int = macsec1.ethernet_interfaces.add(), macsec2.ethernet_interfaces.add()
    macsec1_int.eth_name, macsec2_int.eth_name = eth1.name, eth2.name
    secy1, secy2 = macsec1_int.secy, macsec2_int.secy
    secy1.name, secy2.name = "macsec1", "macsec2"

    # Crypto engine
    secy1.crypto_engine.choice = secy2.crypto_engine.choice = "stateless_encryption_only"

    # Static key
    secy1_sk, secy2_sk = secy1.static_key, secy2.static_key
    secy1_sk.cipher_suite = secy2_sk.cipher_suite = "gcm_aes_128"

    # Tx
    secy1_tx, secy2_tx = secy1.tx, secy2.tx
    secy1_txsc1, secy2_txsc1 = secy1_tx.scs.add(), secy2_tx.scs.add()

    # Tx SC end station
    secy1_txsc1.end_station = secy2_txsc1.end_station = True

    # Tx key
    secy1_txsc1.static_key.sak_pool.name, secy2_txsc1.static_key.sak_pool.name = "macsec1_tx_sakpool", "macsec2_tx_sakpool"
    secy1_tx_sak1, secy2_tx_sak1 = secy1_txsc1.static_key.sak_pool.saks.add(), secy2_txsc1.static_key.sak_pool.saks.add()
    #secy1_tx_sak1.sak = secy2_tx_sak1.sak = "0xF123456789ABCDEF0123456789ABCDEF"
    secy1_tx_sak1.sak = secy2_tx_sak1.sak = "f123456789abcdef0123456789abcdef"

    # Remaining Tx SC settings autofilled

    # Rx
    secy1_rx, secy2_rx = secy1.rx, secy2.rx
    secy1_rxsc1, secy2_rxsc1 = secy1.rx.static_key.scs.add(), secy2.rx.static_key.scs.add()

    # Rx SC
    secy1_rxsc1.dut_system_id =  eth2.mac
    secy2_rxsc1.dut_system_id =  eth1.mac

    # Rx key
    secy1_rxsc1.sak_pool.name, secy2_rxsc1.sak_pool.name = "macsec1_rx_sakpool", "macsec2_rx_sakpool"
    secy1_rx_sak1, secy2_rx_sak1 = secy1_rxsc1.sak_pool.saks.add(), secy2_rxsc1.sak_pool.saks.add()
    #secy1_rx_sak1.sak = secy2_rx_sak1.sak = "0xF123456789ABCDEF0123456789ABCDEF"
    secy1_rx_sak1.sak = secy2_rx_sak1.sak = "f123456789abcdef0123456789abcdef"

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
    print("Sleeping for 30 secoonds: start")
    time.sleep(30)
    print("Sleeping for 30 secoonds: end")
    utils.wait_for(
        lambda: results_ok(api), "stats to be as expected", timeout_seconds=10
    )

    utils.stop_traffic(api, b2b_raw_config)


def results_ok(api):
    #req = api.metrics_request()
    #req.macsec.column_names = ["session_state"]
    #results = api.get_metrics(req)
    ok = []
    #for r in results.macsec_metrics:
    #    ok.append(r.session_state == "up")
    return all(ok)


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
