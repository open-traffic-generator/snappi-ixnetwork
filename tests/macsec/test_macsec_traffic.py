import pytest
import time


# @pytest.mark.skip(reason="Revisit CI/CD fail")
def test_stateless_encryption(api, b2b_raw_config, utils):
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

    macsec1, macsec2 = d1.macsec, d2.macsec
    macsec1_int, macsec2_int = macsec1.ethernet_interfaces.add(), macsec2.ethernet_interfaces.add()
    macsec1_int.eth_name, macsec2_int.eth_name = eth1.name, eth2.name
    secy1, secy2 = macsec1_int.secy, macsec2_int.secy
    secy1.name, secy2.name = "macsec1", "macsec2"

    # TODO: crypto_engine to be optional
    secy1.crypto_engine.engine_type.choice = secy2.crypto_engine.engine_type.choice = "stateless_encryption_only" 

    # static key
    secy1.basic.key_generation.choice = secy2.basic.key_generation.choice = "static"
    secy1.basic.key_generation.static.cipher_suite = secy2.basic.key_generation.static.cipher_suite = "gcm_aes_128"

    # Tx SC
    secy1_txsc1, secy2_txsc1 = secy1.txscs.add(), secy2.txscs.add() 

    # Tx key
    secy1_txsc1.static_key.sak_pool.name, secy2_txsc1.static_key.sak_pool.name = "macsec1_tx_sakpool", "macsec2_tx_sakpool" 
    secy1_tx_sak1, secy2_tx_sak1 = secy1_txsc1.static_key.sak_pool.saks.add(), secy2_txsc1.static_key.sak_pool.saks.add()
    #secy1_tx_sak1.sak = secy2_tx_sak1.sak = "0xF123456789ABCDEF0123456789ABCDEF"
    secy1_tx_sak1.sak = secy2_tx_sak1.sak = "f123456789abcdef0123456789abcdef"

    # Remaining Tx SC settings autofilled

    # Rx SC
    secy1_rxsc1, secy2_rxsc1 = secy1.rxscs.add(), secy2.rxscs.add() 
    secy1_rxsc1.static_key.dut_system_id =  eth2.mac
    secy2_rxsc1.static_key.dut_system_id =  eth1.mac

    # Rx key
    secy1_rxsc1.static_key.sak_pool.name, secy2_rxsc1.static_key.sak_pool.name = "macsec1_rx_sakpool", "macsec2_rx_sakpool" 
    secy1_rx_sak1, secy2_rx_sak1 = secy1_rxsc1.static_key.sak_pool.saks.add(), secy2_rxsc1.static_key.sak_pool.saks.add()
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

    #traffic
    f1 = config.flows.flow(name="f1")[-1]
    f1.tx_rx.device.tx_names = [secy1.name]
    f1.tx_rx.device.rx_names = [secy2.name]
    f1.packet.ethernet()

    utils.start_traffic(api, config)
    print("Sleeping for 10 secoonds: start")
    time.sleep(10)
    print("Sleeping for 10 secoonds: end")
    utils.stop_traffic(api, config)


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
