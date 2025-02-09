from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Macsec(Base):
    _BASIC = {
        "cipher_suite": {
            "ixn_attr": "cipherSuite",
            "enum_map": {"gcm_aes_128": "aes128", "gcm_aes_256": "aes256", "gcm_aes_xpn_128": "aesxpn128", "gcm_aes_xpn_256": "aesxpn256"},
        },
        "confidentiality_offset": {
            "ixn_attr": "confidentialityOffset",
            "enum_map": {"zero": 0, "thirty": 30, "fifty": 50},
        },
    }

    _TXSC = {
        "system_id": "systemId",
        "port_id": "portId",
        "end_station": "endStation",
        "include_sci": "includeSci",
        "confidentiality": "enableConfidentiality",
    }

    _RXSC = {
        "dut_system_id": "dutSciMac",
        "dut_sci_port_id": "dutSciPortId",
    }

#    _DUT = {
#        "cipher_suite": "dutMsbOfXpn",
#        "cipher_suite": "dutSciMac",
#        "cipher_suite": "dutSciPortId",
#    }
#
#    _TX_SAK = {
#        "system_id": "systemId",
#        "port_id": "portId",
#        "end_station": "endStation",
#        "include_sci": "includeSci",
#        "confidentiality": "enableConfidentiality",
#    }

    def __init__(self, ngpf):
        super(Macsec, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)

    def config(self, device):
        self.logger.debug("Configuring MACsec")
        macsec = device.get("macsec")
        if macsec is None:
            return
        self._config_ethernet_interfaces(device)

    def _is_valid(self, ethernet_name, secy):
        is_valid = True
        if secy is None:
            is_valid = False
        else:
            self.logger.debug("Validating SecY of etherner interface %s" % (ethernet_name))
            basic = secy.get("basic")
            txscs = secy.get("txscs")
            rxscs = secy.get("rxscs")
            crypto_engine = secy.get("crypto_engine")
            advance = secy.get("advance")
            key_generation = basic.key_generation
            if key_generation.choice == "static":
                if txscs is None:
                    self._ngpf.api.add_error(
                        "TxSC not added when key generation is static".format(
                            name=ethernet_name
                        )
                    )
                    is_valid = False
                elif len(txscs) > 1:
                    self._ngpf.api.add_error(
                        "More than one TxSC added when key generation is static".format(
                            name=ethernet_name
                        )
                    )
                    is_valid = False
                if not advance is None:
                    if not advance.static_key.rekey_mode.choice == "dont_rekey":
                        self._ngpf.api.add_error(
                            "Rekey not supported as of now when key generation is static".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
            if crypto_engine.engine_type.choice == "stateless_encryption_only":
                for rxsc in rxscs:
                    if rxsc.static_key.replay_protection == True:
                        self.logger.debug("MACsec validation error 5")
                        self._ngpf.api.add_error(
                            "Replay protectin cannot be true when engine type is stateless_encryption_only".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
            if crypto_engine.engine_type.choice == "stateful_encryption_decryption":
                if rxscs is None:
                    self._ngpf.api.add_error(
                        "RxSC not added when key generation is static".format(
                            name=ethernet_name
                        )
                    )
                    is_valid = False
                elif len(rxscs) > 1:
                    self._ngpf.api.add_error(
                        "More than one RxSC added when key generation is static".format(
                            name=ethernet_name
                        )
                    )
                    is_valid = False
                for rxsc in rxscs:
                    if rxsc.static_key.replay_protection == False:
                        self._ngpf.api.add_error(
                            "Replay protectin cannot be false when engine type is stateful_encryption_decryption".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
                    if not rxsc.static_key.replay_window == 1:
                        self._ngpf.api.add_error(
                            "Replay window cannot be other than 1 when engine type is stateful_encryption_decryption".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
        if is_valid == True:
            self.logger.debug("MACsec validation success")
        else:
            self.logger.debug("MACsec validation failure")
        return is_valid

    def _is_ip_allowed(self, device):
        self.logger.debug("Checking if IPv4/ v6 is allowed")
        is_allowed = True
        macsec = device.get("macsec")
        if macsec is None:
            return is_allowed
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return is_allowed
        for ethernet_interface in ethernet_interfaces:
            secy = ethernet_interface.get("secy")
            if secy.crypto_engine.engine_type.choice == "stateless_encryption_only":
                is_allowed = False
                break
        return is_allowed

    def _config_ethernet_interfaces(self, device):
        self.logger.debug("Configuring MACsec interfaces")
        macsec = device.get("macsec")
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return
        for ethernet_interface in ethernet_interfaces:
            ethernet_name = ethernet_interface.get("eth_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            if not self._is_valid(ethernet_name, ethernet_interface.get("secy")):
                continue
            self._config_secy(device, ethernet_interface)

    def _config_secy(self, device, ethernet_interface):
        self.logger.debug("Configuring SecY")
        secy = ethernet_interface.get("secy")
        if secy is None:
            return
        ethernet_name = ethernet_interface.get("eth_name")
        ixn_ethernet = self._ngpf.api.ixn_objects.get_object(ethernet_name)
        if secy.crypto_engine.engine_type.choice == "stateless_encryption_only":
            self.logger.debug("Configuring SecY: stateless_encryption_only")
            ixn_staticmacsec = self.create_node_elemet(
                ixn_ethernet, "staticMacsec", secy.get("name")
            )
            self._ngpf.set_device_info(secy, ixn_staticmacsec)
            self._config_secy_engine_encryption_only(device, ethernet_interface, ixn_staticmacsec)
            basic = secy.get("basic")
            key_generation = basic.key_generation
            #TODO: set key genertion in IxN
            if key_generation.choice == "static":
                self.logger.debug("Configuring SecY for static key")
                self._config_basic(secy, ixn_staticmacsec)
                self._config_txsc(secy, ixn_staticmacsec)
                self._config_rxsc(secy, ixn_staticmacsec)
        else:
            return

    def _config_basic(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring basic properties")
        basic = secy.get("basic")
        self.logger.debug("Configuring basic: %s" % (basic.key_generation.static.cipher_suite))
        self.configure_multivalues(basic.key_generation.static, ixn_staticmacsec, Macsec._BASIC)

    def _config_txsc(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring TxSC")
        txscs = secy.get("txscs")
        basic = secy.get("basic")
        txsc = txscs[0]
        self.configure_multivalues(txsc.static_key, ixn_staticmacsec, Macsec._TXSC)
        tx_sak_pool = txsc.static_key.sak_pool
        tx_sak_pool_name = tx_sak_pool.name
        tx_sak1 = tx_sak_pool.saks[0].sak
        ixn_tx_sak_pool = self.create_node_elemet(
                ixn_staticmacsec, "txSakPool", tx_sak_pool_name
            )
        cipher_suite = basic.key_generation.static.cipher_suite
        if cipher_suite == "gcm_aes_128" or cipher_suite == "gcm_aes_xpn_128":
            ixn_tx_sak_pool["txSak128"] = self.multivalue(tx_sak1)
        elif cipher_suite == "gcm_aes_256" or cipher_suite == "gcm_aes_xpn_256":
            ixn_tx_sak_pool["txSak256"] = self.multivalue(tx_sak1)
        self.logger.debug("IxN Tx SAK pool %s Tx SAK 1: %s" % (ixn_tx_sak_pool["name"], tx_sak1))

    def _config_rxsc(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring RxSC")
        rxscs = secy.get("rxscs")
        basic = secy.get("basic")
        rxsc = rxscs[0]
        self.configure_multivalues(rxsc.static_key, ixn_staticmacsec, Macsec._RXSC)
        rx_sak_pool = rxsc.static_key.sak_pool
        rx_sak_pool_name = rx_sak_pool.name
        rx_sak1 = rx_sak_pool.saks[0].sak
        ixn_rx_sak_pool = self.create_node_elemet(
                ixn_staticmacsec, "rxSakPool", rx_sak_pool_name
            )
        cipher_suite = basic.key_generation.static.cipher_suite
        if cipher_suite == "gcm_aes_128" or cipher_suite == "gcm_aes_xpn_128":
            ixn_rx_sak_pool["rxSak128"] = self.multivalue(rx_sak1)
        elif cipher_suite == "gcm_aes_256" or cipher_suite == "gcm_aes_xpn_256":
            ixn_rx_sak_pool["rxSak256"] = self.multivalue(rx_sak1)
        self.logger.debug("IxN Rx SAK pool %s Rx SAK 1: %s" % (ixn_rx_sak_pool["name"], rx_sak1))

    def _config_secy_engine_encryption_only(self, device, ethernet_interface, ixn_staticmacsec):
        secy = ethernet_interface.get("secy")
        self._config_secy_engine_encryption_only_tx_pn(secy, ixn_staticmacsec)
        #TODO: tx_xpn
        self._config_secy_engine_encryption_only_traffic(device, ethernet_interface, ixn_staticmacsec)

    def _config_secy_engine_encryption_only_traffic(self, device, ethernet_interface, ixn_staticmacsec):
        ethernet_name = ethernet_interface.get("eth_name")
        secy = ethernet_interface.get("secy")
        self.logger.debug("Configuring stateless encryption traffic from ethernet %s secy %s" % (ethernet_name, secy.get("name")))
        ethernets = device.get("ethernets")
        for ethernet in ethernets:
            if ethernet.get("name") == ethernet_name:
                ipv4_addresses = ethernet.get("ipv4_addresses")
                if ipv4_addresses is None:
                    raise Exception("IPv4 not configured on ethernet %s" % ethernet_name)
                elif len(ipv4_addresses) > 1:
                    raise Exception("More than one IPv4 address configured on ethernet %s" % ethernet_name)
                ipv4_address = ipv4_addresses[0].address
                ipv4_gateway_mac = ipv4_addresses[0].gateway_mac
                if ipv4_gateway_mac is None:
                    raise Exception("IPv4 gateway mac not configured for IPv4 address %s on ethernet %s" % (ethernet_name, ipv4_address))
                elif not ipv4_gateway_mac.choice == "value" or ipv4_gateway_mac.value is None:
                    raise Exception("IPv4 gateway static mac not configured for IPv4 address %s on ethernet %s" % (ethernet_name, ipv4_address))
                ipv4_gateway_static_mac = ipv4_addresses[0].gateway_mac.value
                ixn_staticmacsec["sourceIp"] = self.multivalue(ipv4_address)
                ixn_staticmacsec["dutMac"] = self.multivalue(ipv4_gateway_static_mac)
                break

    def _config_secy_engine_encryption_only_tx_pn(self, secy, ixn_staticmacsec):
        engine_tx_pn = secy.crypto_engine.engine_type.stateless_encryption_only.tx_pn
        if engine_tx_pn is None:
            return
        self.logger.debug("Configuring stateless encryption PN for secy %s" % secy.get("name"))
        if engine_tx_pn.choice == "fixed_pn":
            ixn_staticmacsec["incrementingPn"] = False
            ixn_staticmacsec["fixedPn"] = engine_tx_pn.fixed.pn
        elif engine_tx_pn.choice == "incrementing_pn":
            engine_tx_pn_incr = engine_tx_pn.incrementing
            ixn_staticmacsec["incrementingPn"] = True
            ixn_staticmacsec["packetCountPn"] = engine_tx_pn_incr.count
            ixn_staticmacsec["firstPn"] = engine_tx_pn_incr.first
            ixn_staticmacsec["lastPn"] = engine_tx_pn_incr.first + engine_tx_pn_incr.count - 1
