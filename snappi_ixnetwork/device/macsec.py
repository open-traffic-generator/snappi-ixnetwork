from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Macsec(Base):
    _CIPHER = {
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
        "end_station": "endStation",
        "include_sci": "includeSci",
    }

    _TXSC_STATIC_KEY = {
        "system_id": "systemId",
        "port_id": "portId",
        "confidentiality": "enableConfidentiality",
    }

    _RXSC_STATIC_KEY = {
        "dut_system_id": "dutSciMac",
        "dut_sci_port_id": "dutSciPortId",
        "dut_msb_xpn": "dutMsbOfXpn",
    }

    def __init__(self, ngpf):
        super(Macsec, self).__init__()
        self._ngpf = ngpf
        self.is_dynamic_key = False
        self.logger = get_ixnet_logger(__name__)

    def config(self, device):
        self.logger.debug("Configuring MACsec")
        macsec = device.get("macsec")
        if macsec is None:
            return
        self.is_dynamic_key = self._is_dynamic_key(device)
        self._config_ethernet_interfaces(device)

    def _is_valid(self, ethernet_name, secy):
        is_valid = True
        if secy is None:
            is_valid = False
        else:
            self.logger.debug("Validating SecY of etherner interface %s" % (ethernet_name))
            static_key = secy.get("static_key")
            tx = secy.get("tx")
            rx = secy.get("rx")
            txscs = rxscs = tx_rekey_mode = replay_protection = replay_window = None
            if not tx is None:
                txscs = tx.scs
                if not tx.static_key is None:
                    tx_rekey_mode = tx.static_key.rekey_mode
            if not rx is None:
                replay_protection = rx.replay_protection
                replay_window = rx.replay_window
                if not rx.static_key is None:
                    rxscs = rx.static_key.scs
            crypto_engine = secy.get("crypto_engine")
            if not self.is_dynamic_key:
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
            if crypto_engine is None:
                self._ngpf.api.add_error(
                    "Replay protectin cannot be true when engine type is stateless_encryption_only".format(
                        name=ethernet_name
                    )
                )
                is_valid = False
            elif crypto_engine.choice == "stateless_encryption_only":
                if not tx_rekey_mode is None:
                    if tx_rekey_mode.choice == "pn_based":
                        self._ngpf.api.add_error(
                            "PN based rekey not supported when engine type is stateless_encryption_only".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
                if not replay_protection is None:
                    if replay_protection == True:
                        self._ngpf.api.add_error(
                            "Replay protectin cannot be true when engine type is stateless_encryption_only".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
                if not replay_protection is None:
                    if replay_protection == True:
                        self._ngpf.api.add_error(
                            "Replay protectin cannot be true when engine type is stateless_encryption_only".format(
                                name=ethernet_name
                            )
                        )
                        is_valid = False
            else:
                self._ngpf.api.add_error(
                    "SecY crypto_engine is not set to stateless_encryption_only. Only tateless_encryption_only engine type is supported as of now.".format(
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
            if secy.crypto_engine.choice == "stateless_encryption_only":
                is_allowed = False
                break
        return is_allowed

    def _is_dynamic_key(self, device):
        self.logger.debug("Checking if MKA is confgured")
        is_mka = False
        mka = device.get("mka")
        if not mka is None:
            is_mka = True
        return is_mka

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
        if secy.crypto_engine.choice == "stateless_encryption_only":
            self.logger.debug("Configuring SecY: stateless_encryption_only")
            ixn_staticmacsec = self.create_node_elemet(
                ixn_ethernet, "staticMacsec", secy.get("name")
            )
            self._ngpf.set_device_info(secy, ixn_staticmacsec)
            if not self.is_dynamic_key:
                self._config_cipher(secy, ixn_staticmacsec)
            self._config_secy_engine_encryption_only(device, ethernet_interface, ixn_staticmacsec)
            self._config_tx(secy, ixn_staticmacsec)
        if not secy.crypto_engine.choice == "stateless_encryption_only":
            self._config_rx(secy, ixn_staticmacsec)

    def _config_cipher(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring cipher from static key")
        static_key = secy.get("static_key")
        self.configure_multivalues(static_key, ixn_staticmacsec, Macsec._CIPHER)

    def _config_tx(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring Tx properties")
        tx = secy.get("tx")
        if tx is None:
            return
        self._config_txsc(secy, ixn_staticmacsec)
        if not self.is_dynamic_key:
            self._config_rekey_mode(tx.static_key.rekey_mode, ixn_staticmacsec)

    def _config_rx(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring Rx properties")
        rx = secy.get("rx")
        if rx is None:
            return
        #TODO: replay protection, replay window.
        self.logger.debug("replay_protection %s replay_window %s" % (rx.replay_protection, rx.replay_window))
        if not self.is_dynamic_key:
            self._config_rxsc(secy, ixn_staticmacsec)

    def _config_txsc(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring TxSC")
        tx = secy.get("tx")
        txscs = tx.get("scs")
        txsc = txscs[0]
        self.logger.debug("end_station %s include_sci %s" % (txsc.end_station, txsc.include_sci))
        self.configure_multivalues(txsc, ixn_staticmacsec, Macsec._TXSC)
        if not self.is_dynamic_key:
            self.configure_multivalues(txsc.static_key, ixn_staticmacsec, Macsec._TXSC_STATIC_KEY)
            tx_saks = txsc.static_key.saks
            ixn_staticmacsec["txSakPoolSize"] = len(tx_saks)
            saks = []
            sscis = []
            salts = []
            for tx_sak in tx_saks:
                saks.append(tx_sak.sak)
                sscis.append(tx_sak.ssci)
                salts.append(tx_sak.salt)
            ixn_tx_sak_pool = self.create_node_elemet(
                    ixn_staticmacsec, "txSakPool", name=None
                )
            static_key = secy.get("static_key")
            cipher_suite = static_key.cipher_suite
            if cipher_suite == "gcm_aes_128" or cipher_suite == "gcm_aes_xpn_128":
                ixn_tx_sak_pool["txSak128"] = self.multivalue(saks)
            elif cipher_suite == "gcm_aes_256" or cipher_suite == "gcm_aes_xpn_256":
                ixn_tx_sak_pool["txSak256"] = self.multivalue(saks)
            if cipher_suite == "gcm_aes_xpn_128" or cipher_suite == "gcm_aes_xpn_256":
                ixn_tx_sak_pool["txSsci"] = self.multivalue(sscis)
                ixn_tx_sak_pool["txSalt"] = self.multivalue(salts)

    def _config_rxsc(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring RxSC")
        rx = secy.get("rx")
        rx_sk = rx.static_key
        rxscs = rx_sk.get("scs")
        rxsc = rxscs[0]
        self.configure_multivalues(rxsc, ixn_staticmacsec, Macsec._RXSC_STATIC_KEY)
        rx_saks = rxsc.saks
        ixn_staticmacsec["rxSakPoolSize"] = len(rx_saks)
        saks = []
        sscis = []
        salts = []
        for rx_sak in rx_saks:
            saks.append(rx_sak.sak)
            sscis.append(rx_sak.ssci)
            salts.append(rx_sak.salt)
        ixn_rx_sak_pool = self.create_node_elemet(
                ixn_staticmacsec, "rxSakPool", name=None
            )
        static_key = secy.get("static_key")
        cipher_suite = static_key.cipher_suite
        if cipher_suite == "gcm_aes_128" or cipher_suite == "gcm_aes_xpn_128":
            ixn_rx_sak_pool["rxSak128"] = self.multivalue(saks)
        elif cipher_suite == "gcm_aes_256" or cipher_suite == "gcm_aes_xpn_256":
            ixn_rx_sak_pool["rxSak256"] = self.multivalue(saks)
        if cipher_suite == "gcm_aes_xpn_128" or cipher_suite == "gcm_aes_xpn_256":
            ixn_rx_sak_pool["rxSsci"] = self.multivalue(sscis)
            ixn_rx_sak_pool["rxSalt"] = self.multivalue(salts)

    def _config_rekey_mode(self, rekey_mode, ixn_staticmacsec):
        self.logger.debug("Configuring rekey settings")
        if rekey_mode.choice == "dont_rekey":
            #ixn_staticmacsec["rekeyMode"] = "timerBased"
            ixn_staticmacsec["rekeyBehaviour"] = "dontRekey"
        elif rekey_mode.choice == "timer_based":
            timer_based = rekey_mode.timer_based
            #ixn_staticmacsec["rekeyMode"] = "timerBased"
            if timer_based.choice == "fixed_count":
                ixn_staticmacsec["rekeyBehaviour"] = "rekeyFixedCount"
                ixn_staticmacsec["periodicRekeyAttempts"] = timer_based.fixed_count
                ixn_staticmacsec["periodicRekeyInterval"] = timer_based.interval
            elif timer_based.choice == "continuous":
                ixn_staticmacsec["rekeyBehaviour"] = "rekeyContinuous"
                ixn_staticmacsec["periodicRekeyInterval"] = timer_based.interval
        #elif rekey_mode.choice == "pn_based":
        #    ixn_staticmacsec["rekeyMode"] = "pnBased"
        #    ixn_staticmacsec["rekeyBehaviour"] = "rekeyContinuous"

    def _config_secy_engine_encryption_only(self, device, ethernet_interface, ixn_staticmacsec):
        secy = ethernet_interface.get("secy")
        self._config_secy_engine_encryption_only_tx_pn(secy, ixn_staticmacsec)
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
        engine_tx_pn = secy.crypto_engine.stateless_encryption_only.tx_pn
        if engine_tx_pn is None:
            return
        self.logger.debug("Configuring Tx PN of stateless encryption only engine secy %s" % secy.get("name"))
        if engine_tx_pn.choice == "fixed_pn":
            ixn_staticmacsec["incrementingPn"] = False
            engine_tx_pn_fixed = engine_tx_pn.fixed
            ixn_staticmacsec["fixedPn"] = engine_tx_pn_fixed.pn
            ixn_staticmacsec["mvFixedXpn"] = self.multivalue(engine_tx_pn_fixed.xpn)
        elif engine_tx_pn.choice == "incrementing_pn":
            ixn_staticmacsec["incrementingPn"] = True
            engine_tx_pn_incr = engine_tx_pn.incrementing
            ixn_staticmacsec["packetCountPn"] = engine_tx_pn_incr.count
            ixn_staticmacsec["firstPn"] = engine_tx_pn_incr.first_pn
            ixn_staticmacsec["mvFirstXpn"] = self.multivalue(engine_tx_pn_incr.first_xpn)
