from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.device.mka import Mka
from snappi_ixnetwork.logger import get_ixnet_logger


class Macsec(Base):
    _CIPHER = {
        "cipher_suite": {
            "ixn_attr": "cipherSuite",
            "enum_map": {
                "gcm_aes_128": "aes128",
                "gcm_aes_256": "aes256",
                "gcm_aes_xpn_128": "aesxpn128",
                "gcm_aes_xpn_256": "aesxpn256",
            },
        },
        "confidentiality": "enableConfidentiality",
        "confidentiality_offset": {
            "ixn_attr": "confidentialityOffset",
            "enum_map": {"zero": 0, "thirty": 30, "fifty": 50},
        },
    }

    _DATA_PLANE_TX = {
        "end_station": "endStation",
        "include_sci": "includeSci",
    }

    _STATIC_KEY_TXSC = {
        "system_id": "systemId",
        "port_id": "portId",
    }

    _STATIC_KEY_RXSC = {
        "dut_sci_system_id": "dutSciMac",
        "dut_sci_port_id": "dutSciPortId",
        "dut_msb_xpn": "dutMsbOfXpn",
    }

    def __init__(self, ngpf):
        super(Macsec, self).__init__()
        self._ngpf = ngpf
        self._mka = Mka(ngpf)
        self.is_dynamic_key = False
        self.logger = get_ixnet_logger(__name__)

    def config(self, device):
        self.logger.debug("Configuring MACsec")
        macsec = device.get("macsec")
        if macsec is None:
            return
        self.is_dynamic_key = self._is_dynamic_key(macsec)
        if self.is_dynamic_key == True:
            self._mka.config(device)
        self.is_data_plane = self._is_data_plane(macsec)
        self._config_ethernet_interfaces(device)

    def _is_valid(self, ethernet_name, secy):
        is_valid = True
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
            secy = ethernet_interface.get("secure_entity")
            if secy is None:
                continue
            data_plane = secy.get("data_plane")
            if data_plane is None:
                continue
            encapsulation = data_plane.get("encapsulation")
            if encapsulation is None:
                continue
            crypto_engine = encapsulation.get("crypto_engine")
            if crypto_engine is None:
                continue
            if crypto_engine.choice == "encrypt_only":
                is_allowed = False
                break
        if is_allowed == True:
            self.logger.debug("IPv4/ v6 is allowed")
        else:
            self.logger.debug(
                "IPv4/ v6 is not allowed on configured crypto_engine in MACsec"
            )
        return is_allowed

    def _is_dynamic_key(self, macsec):
        self.logger.debug("Checking if MKA is configured")
        is_mka = False
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        for ethernet_interface in ethernet_interfaces:
            secy = ethernet_interface.get("secure_entity")
            key_generation_protocol = secy.get("key_generation_protocol")
            protocol = key_generation_protocol.choice
            if protocol == "mka":
                is_mka = True
                break
        if is_mka == True:
            self.logger.info("MKA is configured in test")
        return is_mka

    def _is_data_plane(self, macsec):
        self.logger.debug("Checking if MACsec data plane is configured")
        is_data_plane = False
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        for ethernet_interface in ethernet_interfaces:
            ethernet_interface = ethernet_interfaces[0]
            secy = ethernet_interface.get("secure_entity")
            data_plane = secy.get("data_plane")
            if data_plane is None:
                continue
            if data_plane.choice == "encapsulation":
                is_data_plane = True
                break
        return is_data_plane

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
            if not self._is_valid(
                ethernet_name, ethernet_interface.get("secure_entity")
            ):
                continue
            self._config_secy(device, ethernet_interface)

    def _config_secy(self, device, ethernet_interface):
        self.logger.debug("Configuring SecY")
        secy = ethernet_interface.get("secure_entity")
        if secy is None:
            return
        ethernet_name = ethernet_interface.get("eth_name")
        ixn_ethernet = self._ngpf.api.ixn_objects.get_object(ethernet_name)
        # if self.is_dynamic_key:
        # config MKA
        if self.is_data_plane:
            if (
                secy.data_plane.encapsulation.crypto_engine.choice
                == "encrypt_only"
            ):
                self.logger.debug("Configuring SecY: encrypt_only")
                ixn_staticmacsec = self.create_node_elemet(
                    ixn_ethernet, "staticMacsec", secy.get("name")
                )
                self._ngpf.set_device_info(secy, ixn_staticmacsec)
                if not self.is_dynamic_key:
                    self._config_static_key(secy, ixn_staticmacsec)
                self._config_data_plane(
                    device, ethernet_interface, ixn_staticmacsec
                )

    def _config_static_key(self, secy, ixn_staticmacsec):
        self.logger.debug("Configuring static key")
        key_generation_protocol = secy.get("key_generation_protocol")
        static_key = key_generation_protocol.get("static_key")
        if static_key is None:
            return
        self._config_static_key_cipher(static_key, ixn_staticmacsec)
        self._config_static_key_tx(static_key, ixn_staticmacsec)
        self._config_static_key_rx(static_key, ixn_staticmacsec)

    def _config_static_key_cipher(self, static_key, ixn_staticmacsec):
        self.logger.debug("Configuring cipher for static key")
        self.configure_multivalues(
            static_key, ixn_staticmacsec, Macsec._CIPHER
        )

    def _config_data_plane(self, device, ethernet_interface, ixn_staticmacsec):
        self.logger.debug("Configuring data plane properties")
        secy = ethernet_interface.get("secure_entity")
        data_plane = secy.get("data_plane")
        encapsulation = data_plane.get("encapsulation")
        if encapsulation is None:
            return
        self._config_data_plane_tx(encapsulation, ixn_staticmacsec)
        self._config_data_plane_rx(encapsulation, ixn_staticmacsec)
        self._config_crypto_engine(
            device, ethernet_interface, ixn_staticmacsec
        )

    def _config_data_plane_tx(self, encapsulation, ixn_staticmacsec):
        self.logger.debug("Configuring data plane Tx properties")
        tx = encapsulation.get("tx")
        if tx is None:
            return
        self.logger.debug(
            "end_station %s include_sci %s" % (tx.end_station, tx.include_sci)
        )
        self.configure_multivalues(tx, ixn_staticmacsec, Macsec._DATA_PLANE_TX)

    def _config_data_plane_rx(self, encapsulation, ixn_staticmacsec):
        self.logger.debug("Configuring data plane Rx properties")
        rx = encapsulation.get("rx")
        if rx is None:
            return
        # TODO: replay protection, replay window.
        # self.logger.debug("replay_protection %s replay_window %s" % (rx.replay_protection, rx.replay_window))

    def _config_crypto_engine(
        self, device, ethernet_interface, ixn_staticmacsec
    ):
        self.logger.debug("Configuring crypto engine properties")
        secy = ethernet_interface.get("secure_entity")
        data_plane = secy.get("data_plane")
        encapsulation = data_plane.get("encapsulation")
        crypto_engine = encapsulation.get("crypto_engine")
        if crypto_engine is None:
            return
        if crypto_engine.choice == "encrypt_only":
            self._config_crypto_engine_encrypt_only(
                device, ethernet_interface, ixn_staticmacsec
            )

    def _config_static_key_tx(self, static_key, ixn_staticmacsec):
        self.logger.debug("Configuring Tx properties for static key")
        tx = static_key.get("tx")
        if tx is None:
            return
        self._config_static_key_txsc(static_key, ixn_staticmacsec)
        self._config_rekey_mode(static_key.tx.rekey_mode, ixn_staticmacsec)

    def _config_static_key_rx(self, static_key, ixn_staticmacsec):
        self.logger.debug("Configuring Rx properties for static key")
        rx = static_key.get("rx")
        if rx is None:
            return
        self._config_static_key_rxsc(static_key, ixn_staticmacsec)

    def _config_static_key_txsc(self, static_key, ixn_staticmacsec):
        self.logger.debug("Configuring Tx secure channels for static key")
        tx = static_key.get("tx")
        txscs = tx.get("secure_channels")
        txsc = txscs[0]
        self.configure_multivalues(
            txsc, ixn_staticmacsec, Macsec._STATIC_KEY_TXSC
        )
        tx_saks = txsc.saks
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
        cipher_suite = static_key.cipher_suite
        if cipher_suite == "gcm_aes_128" or cipher_suite == "gcm_aes_xpn_128":
            ixn_tx_sak_pool["txSak128"] = self.multivalue(saks)
        elif (
            cipher_suite == "gcm_aes_256" or cipher_suite == "gcm_aes_xpn_256"
        ):
            ixn_tx_sak_pool["txSak256"] = self.multivalue(saks)
        if (
            cipher_suite == "gcm_aes_xpn_128"
            or cipher_suite == "gcm_aes_xpn_256"
        ):
            ixn_tx_sak_pool["txSsci"] = self.multivalue(sscis)
            ixn_tx_sak_pool["txSalt"] = self.multivalue(salts)

    def _config_static_key_rxsc(self, static_key, ixn_staticmacsec):
        self.logger.debug("Configuring Rx secure channels for static key")
        rx = static_key.get("rx")
        rxscs = rx.get("secure_channels")
        rxsc = rxscs[0]
        self.configure_multivalues(
            rxsc, ixn_staticmacsec, Macsec._STATIC_KEY_RXSC
        )
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
        elif (
            cipher_suite == "gcm_aes_256" or cipher_suite == "gcm_aes_xpn_256"
        ):
            ixn_rx_sak_pool["rxSak256"] = self.multivalue(saks)
        if (
            cipher_suite == "gcm_aes_xpn_128"
            or cipher_suite == "gcm_aes_xpn_256"
        ):
            ixn_rx_sak_pool["rxSsci"] = self.multivalue(sscis)
            ixn_rx_sak_pool["rxSalt"] = self.multivalue(salts)

    def _config_rekey_mode(self, rekey_mode, ixn_staticmacsec):
        self.logger.debug("Configuring Tx rekey for static key")
        if rekey_mode.choice == "dont_rekey":
            # ixn_staticmacsec["rekeyMode"] = "timerBased"
            ixn_staticmacsec["rekeyBehaviour"] = "dontRekey"
        elif rekey_mode.choice == "timer_based":
            timer_based = rekey_mode.timer_based
            # ixn_staticmacsec["rekeyMode"] = "timerBased"
            if timer_based.choice == "fixed_count":
                ixn_staticmacsec["rekeyBehaviour"] = "rekeyFixedCount"
                ixn_staticmacsec["periodicRekeyAttempts"] = (
                    timer_based.fixed_count
                )
                ixn_staticmacsec["periodicRekeyInterval"] = (
                    timer_based.interval
                )
            elif timer_based.choice == "continuous":
                ixn_staticmacsec["rekeyBehaviour"] = "rekeyContinuous"
                ixn_staticmacsec["periodicRekeyInterval"] = (
                    timer_based.interval
                )
        # elif rekey_mode.choice == "pn_based":
        #    ixn_staticmacsec["rekeyMode"] = "pnBased"
        #    ixn_staticmacsec["rekeyBehaviour"] = "rekeyContinuous"

    def _config_crypto_engine_encrypt_only(
        self, device, ethernet_interface, ixn_staticmacsec
    ):
        secy = ethernet_interface.get("secure_entity")
        self._config_crypto_engine_encrypt_only_tx_pn(secy, ixn_staticmacsec)
        self._config_crypto_engine_encrypt_only_traffic(
            device, ethernet_interface, ixn_staticmacsec
        )

    def _config_crypto_engine_encrypt_only_traffic(
        self, device, ethernet_interface, ixn_staticmacsec
    ):
        ethernet_name = ethernet_interface.get("eth_name")
        secy = ethernet_interface.get("secure_entity")
        self.logger.debug(
            "Configuring stateless encryption traffic from ethernet %s secy %s"
            % (ethernet_name, secy.get("name"))
        )
        ethernets = device.get("ethernets")
        for ethernet in ethernets:
            if ethernet.get("name") == ethernet_name:
                self._ngpf.api.set_device_traffic_endpoint(
                    ethernet_name, secy.get("name")
                )
                ipv4_addresses = ethernet.get("ipv4_addresses")
                if ipv4_addresses is None:
                    # raise Exception("IPv4 not configured on ethernet %s" % ethernet_name)
                    self.logger.info(
                        "IPv4 not configured on ethernet %s" % ethernet_name
                    )
                    break
                elif len(ipv4_addresses) > 1:
                    raise Exception(
                        "More than one IPv4 address configured on ethernet %s"
                        % ethernet_name
                    )
                ipv4_address = ipv4_addresses[0].address
                ipv4_gateway_mac = ipv4_addresses[0].gateway_mac
                if ipv4_gateway_mac is None:
                    raise Exception(
                        "IPv4 gateway mac not configured for IPv4 address %s on ethernet %s"
                        % (ethernet_name, ipv4_address)
                    )
                elif (
                    not ipv4_gateway_mac.choice == "value"
                    or ipv4_gateway_mac.value is None
                ):
                    raise Exception(
                        "IPv4 gateway static mac not configured for IPv4 address %s on ethernet %s"
                        % (ethernet_name, ipv4_address)
                    )
                ipv4_gateway_static_mac = ipv4_addresses[0].gateway_mac.value
                ixn_staticmacsec["sourceIp"] = self.multivalue(ipv4_address)
                ixn_staticmacsec["dutMac"] = self.multivalue(
                    ipv4_gateway_static_mac
                )
                self._ngpf.api.set_device_traffic_endpoint(
                    ipv4_addresses[0].name, secy.get("name")
                )
                break

    def _config_crypto_engine_encrypt_only_tx_pn(self, secy, ixn_staticmacsec):
        crypto_engine = secy.data_plane.encapsulation.crypto_engine
        crypto_engine_encrypt_only = crypto_engine.encrypt_only
        if crypto_engine_encrypt_only is None:
            return
        txscs = crypto_engine_encrypt_only.secure_channels
        if len(txscs) > 0:
            txsc = txscs[0]
        else:
            return
        if txsc is None:
            return
        engine_tx_pn = txsc.get("tx_pn")
        if engine_tx_pn is None:
            return
        self.logger.debug(
            "Configuring Tx PN of stateless encryption only engine secy %s"
            % secy.get("name")
        )
        if engine_tx_pn.choice == "fixed_pn":
            ixn_staticmacsec["incrementingPn"] = False
            engine_tx_pn_fixed = engine_tx_pn.fixed
            ixn_staticmacsec["fixedPn"] = engine_tx_pn_fixed.pn
            ixn_staticmacsec["mvFixedXpn"] = self.multivalue(
                engine_tx_pn_fixed.xpn
            )
        elif engine_tx_pn.choice == "incrementing_pn":
            ixn_staticmacsec["incrementingPn"] = True
            engine_tx_pn_incr = engine_tx_pn.incrementing
            ixn_staticmacsec["packetCountPn"] = engine_tx_pn_incr.count
            ixn_staticmacsec["firstPn"] = engine_tx_pn_incr.starting_pn
            ixn_staticmacsec["mvFirstXpn"] = self.multivalue(
                engine_tx_pn_incr.starting_xpn
            )
