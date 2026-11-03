from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.device import macsec_hw
from snappi_ixnetwork.device.macsec_hw import MacsecHw
from snappi_ixnetwork.device.mka import Mka
from snappi_ixnetwork.exceptions import SnappiIxnException
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

    _ENCRYPT_DECRYPT_TX_PN = {
        "starting_pn": "startingPn",
        "starting_xpn": "startingXpn",
    }

    # Engine descriptors: one entry per way an OTG secure entity can be
    # realised in IxNetwork. The shared build logic below is driven by these,
    # so a new engine (e.g. inline crypto hardware) only adds an entry here
    # and the maps it needs, not a copy of the build code.
    #   node           NGPF node created under the Ethernet
    #   traffic_type   staticMacsec encryptedTrafficType (None if not applicable)
    #   ip_restricted  encrypt only engine cannot carry IP stacks
    #   tx_pn          "per_secure_channel" (encrypt_only array) or "single"
    #   pn_based       pn_based rekey supported
    #   replay         replay_protection / replay_window supported
    _ENGINES = {
        "encrypt_only": {
            "node": "staticMacsec",
            "traffic_type": "statelessL23",
            "ip_restricted": True,
            "tx_pn": "per_secure_channel",
            "pn_based": False,
            "replay": False,
        },
        "encrypt_decrypt_none": {
            "node": "staticMacsec",
            "traffic_type": "statefulL47",
            "ip_restricted": False,
            "tx_pn": "single",
            "pn_based": False,
            "replay": False,
            # stateful engine: only IP stacked on the node is protected
            "ip_under_node": True,
        },
        macsec_hw.ENGINE_KEY: macsec_hw.ENGINE,
    }

    _SAK_HEX_LENGTH = {
        "gcm_aes_128": 32,
        "gcm_aes_xpn_128": 32,
        "gcm_aes_256": 64,
        "gcm_aes_xpn_256": 64,
    }

    def __init__(self, ngpf):
        super(Macsec, self).__init__()
        self._ngpf = ngpf
        self._mka = Mka(ngpf)
        self._hw = MacsecHw()
        self.logger = get_ixnet_logger(__name__)

    @staticmethod
    def validate_config(config):
        """Checks that need no IxNetwork connection. Called before any REST
        call is made."""
        for lag in config.lags:
            for lag_port in lag.get("ports") or []:
                if lag_port.get("macsec") is not None:
                    raise SnappiIxnException(
                        400,
                        "MACsec on LAG ports (lag %s, port %s) is not "
                        "supported" % (lag.get("name"), lag_port.port_name),
                    )
        MacsecHw.port_settings(config)
        Mka.port_settings(config)
        port_protocols = {}
        for device in config.devices:
            macsec = device.get("macsec")
            if macsec is None:
                continue
            ethernets = {
                ethernet.get("name"): ethernet
                for ethernet in device.get("ethernets") or []
            }
            device_engines = {}
            for iface in macsec.get("ethernet_interfaces") or []:
                secy = iface.get("secure_entity")
                if secy is None:
                    continue
                engine = Macsec._engine_for(secy)
                if engine is not None:
                    descriptor = Macsec._ENGINES[engine]
                    device_engines[secy.get("name")] = (
                        descriptor["node"],
                        descriptor["traffic_type"],
                    )
                protocol = secy.get("key_generation_protocol")
                ethernet = ethernets.get(iface.get("eth_name"))
                connection = (
                    ethernet.get("connection")
                    if ethernet is not None
                    else None
                )
                port_name = (
                    connection.get("port_name")
                    if connection is not None
                    else None
                )
                if protocol is not None and port_name is not None:
                    port_protocols.setdefault(port_name, {})[
                        secy.get("name")
                    ] = protocol.choice
            if len(set(device_engines.values())) > 1:
                raise SnappiIxnException(
                    400,
                    "Device %s mixes MACsec engines (%s). Different engines "
                    "need separate devices"
                    % (device.get("name"), ", ".join(sorted(device_engines))),
                )
        for port_name, secys in port_protocols.items():
            if len(set(secys.values())) > 1:
                raise SnappiIxnException(
                    400,
                    "Port %s mixes key_generation_protocol choices %s. "
                    "The key generation mode is a per port setting"
                    % (port_name, sorted(secys.items())),
                )

    def config(self, device):
        self.logger.debug("Configuring MACsec")
        macsec = device.get("macsec")
        if macsec is None:
            return
        if self._is_dynamic_key(macsec):
            self._mka.config(device)
        self._config_ethernet_interfaces(device)

    @staticmethod
    def engines_on_port(config, port_name):
        """Engine keys of the secure entities on a port."""
        engines = set()
        for device in config.devices:
            macsec = device.get("macsec")
            if macsec is None:
                continue
            ethernets = {
                ethernet.get("name"): ethernet
                for ethernet in device.get("ethernets") or []
            }
            for iface in macsec.get("ethernet_interfaces") or []:
                ethernet = ethernets.get(iface.get("eth_name"))
                connection = (
                    ethernet.get("connection") if ethernet is not None else None
                )
                if connection is None or connection.get("port_name") != port_name:
                    continue
                secy = iface.get("secure_entity")
                engine = Macsec._engine_for(secy) if secy is not None else None
                if engine is not None:
                    engines.add(engine)
        return engines

    @staticmethod
    def _engine_for(secy):
        """Return the engine descriptor key for a secure entity, None when the
        secure entity has no MACsec data plane (MKA only)."""
        name = secy.get("name")
        data_plane = secy.get("data_plane")
        if data_plane is None or data_plane.choice is None:
            return None
        if data_plane.choice == "no_encapsulation":
            return None
        if data_plane.choice != "encapsulation":
            raise SnappiIxnException(
                400,
                "Secure entity %s: unknown data_plane choice %s"
                % (name, data_plane.choice),
            )
        crypto_engine = data_plane.encapsulation.crypto_engine
        if crypto_engine.choice == "encrypt_only":
            return "encrypt_only"
        if crypto_engine.choice == "encrypt_decrypt":
            acceleration = crypto_engine.encrypt_decrypt.hardware_acceleration
            if acceleration.choice == "none":
                return "encrypt_decrypt_none"
            if acceleration.choice == "inline_crypto":
                return macsec_hw.ENGINE_KEY
            raise SnappiIxnException(
                400,
                "Secure entity %s: unknown hardware_acceleration choice %s"
                % (name, acceleration.choice),
            )
        raise SnappiIxnException(
            400,
            "Secure entity %s: unknown crypto_engine choice %s"
            % (name, crypto_engine.choice),
        )

    def _is_valid(self, ethernet_name, secy, engine):
        """Raise SnappiIxnException(400) for a config that cannot be
        realised. Runs before any node is created."""
        name = secy.get("name")
        self.logger.debug("Validating MACsec secure entity %s" % name)
        data_plane = secy.get("data_plane")
        key_generation_protocol = secy.get("key_generation_protocol")
        protocol = (
            key_generation_protocol.choice
            if key_generation_protocol is not None
            else None
        )
        if engine is None:
            if (
                data_plane is not None
                and data_plane.choice == "no_encapsulation"
                and protocol == "static_key"
            ):
                raise SnappiIxnException(
                    400,
                    "Secure entity %s on ethernet %s: no_encapsulation needs "
                    "mka as key_generation_protocol, static_key has nothing "
                    "to configure" % (name, ethernet_name),
                )
            return True
        if protocol == "static_key":
            static_key = key_generation_protocol.get("static_key")
            if static_key is not None:
                self._validate_static_key(name, static_key)
        encapsulation = data_plane.encapsulation
        self._validate_rekey(name, engine, key_generation_protocol)
        rx = encapsulation.get("rx")
        if rx is not None and not self._ENGINES[engine]["replay"]:
            if rx.get("replay_protection"):
                self.logger.warning(
                    "Secure entity %s: replay_protection is set but is not "
                    "supported by this engine; the value will be ignored."
                    % name
                )
            if rx.get("replay_window") is not None:
                self.logger.warning(
                    "Secure entity %s: replay_window is set but is not "
                    "supported by this engine; the value will be ignored."
                    % name
                )
        self.logger.debug("MACsec validation success")
        return True

    def _validate_rekey(self, name, engine, key_generation_protocol):
        if self._ENGINES[engine]["pn_based"]:
            return
        if key_generation_protocol.choice != "static_key":
            return
        static_key = key_generation_protocol.get("static_key")
        tx = static_key.get("tx") if static_key is not None else None
        if tx is None:
            return
        rekey_mode = tx.get("rekey_mode")
        if rekey_mode is not None and rekey_mode.choice == "pn_based":
            raise SnappiIxnException(
                400,
                "Secure entity %s: rekey_mode pn_based is not supported by "
                "the software MACsec engine" % name,
            )

    def _validate_static_key(self, name, static_key):
        cipher_suite = static_key.cipher_suite
        for direction in ("tx", "rx"):
            side = static_key.get(direction)
            if side is None:
                continue
            secure_channels = side.get("secure_channels")
            if secure_channels is None or len(secure_channels) == 0:
                raise SnappiIxnException(
                    400,
                    "Secure entity %s: static_key.%s.secure_channels is empty,"
                    " exactly one secure channel is needed"
                    % (name, direction),
                )
            if len(secure_channels) > 1:
                self.logger.warning(
                    "Secure entity %s: only the first of %d static_key.%s "
                    "secure channels is configured"
                    % (name, len(secure_channels), direction)
                )
            saks = secure_channels[0].get("saks")
            if saks is None or len(saks) == 0:
                raise SnappiIxnException(
                    400,
                    "Secure entity %s: static_key.%s.secure_channels[0] has "
                    "no saks" % (name, direction),
                )
            expected = Macsec._SAK_HEX_LENGTH[cipher_suite]
            for index, sak in enumerate(saks):
                length = Macsec._hex_length(sak.get("sak"))
                if length != expected:
                    raise SnappiIxnException(
                        400,
                        "Secure entity %s: static_key.%s sak %d has %s hex "
                        "digits but cipher_suite %s needs %d"
                        % (
                            name,
                            direction,
                            index,
                            length,
                            cipher_suite,
                            expected,
                        ),
                    )

    @staticmethod
    def _hex_length(value):
        if value is None:
            return None
        value = str(value)
        if value[:2] in ("0x", "0X"):
            value = value[2:]
        return len(value)

    def set_ip_restriction(self, device):
        self.logger.debug("Checking if IPv4/ v6 is restricted")
        macsec = device.get("macsec")
        if macsec is None:
            return
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return
        for ethernet_interface in ethernet_interfaces:
            secy = ethernet_interface.get("secure_entity")
            if secy is None:
                continue
            engine = self._engine_for(secy)
            if engine is None or not self._ENGINES[engine]["ip_restricted"]:
                continue
            self.logger.debug(
                "IPv4/ v6 is restricted on ethernet %s as %s MACsec engine is configured"
                % (ethernet_interface.get("eth_name"), engine)
            )
            self._ngpf.set_ip_restricted(ethernet_interface.get("eth_name"))

    def _is_dynamic_key(self, macsec):
        self.logger.debug("Checking if MKA is configured")
        is_mka = False
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return False
        for ethernet_interface in ethernet_interfaces:
            if self._secy_is_dynamic_key(ethernet_interface):
                is_mka = True
                break
        if is_mka == True:
            self.logger.info("MKA is configured in test")
        return is_mka

    def _secy_is_dynamic_key(self, ethernet_interface):
        secy = ethernet_interface.get("secure_entity")
        if secy is None:
            return False
        key_generation_protocol = secy.get("key_generation_protocol")
        if key_generation_protocol is None:
            return False
        return key_generation_protocol.choice == "mka"

    def _config_ethernet_interfaces(self, device):
        self.logger.debug("Configuring MACsec interfaces")
        macsec = device.get("macsec")
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return
        for ethernet_interface in ethernet_interfaces:
            ethernet_name = ethernet_interface.get("eth_name")
            secy = ethernet_interface.get("secure_entity")
            if secy is None:
                continue
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            engine = self._engine_for(secy)
            if not self._is_valid(ethernet_name, secy, engine):
                continue
            if engine is None:
                continue
            self._config_secy(device, ethernet_interface, engine)

    def _config_secy(self, device, ethernet_interface, engine):
        self.logger.debug("Configuring SecY: %s" % engine)
        descriptor = Macsec._ENGINES[engine]
        secy = ethernet_interface.get("secure_entity")
        ethernet_name = ethernet_interface.get("eth_name")
        ixn_ethernet = self._ngpf.api.ixn_objects.get_object(ethernet_name)
        ixn_node = self.create_node_elemet(
            ixn_ethernet, descriptor["node"], secy.get("name")
        )
        if descriptor["traffic_type"] is not None:
            ixn_node["encryptedTrafficType"] = descriptor["traffic_type"]
        self._ngpf.set_device_info(secy, ixn_node)
        if descriptor.get("ip_under_node"):
            self._move_ip_under_node(ixn_ethernet, ixn_node)
        if not self._secy_is_dynamic_key(ethernet_interface):
            self._config_static_key(secy, ixn_node, descriptor)
        self._config_data_plane(device, ethernet_interface, ixn_node, engine)

    def _move_ip_under_node(self, ixn_ethernet, ixn_node):
        """The hardware engine only protects traffic of the IP interfaces
        stacked on its node, so move the Ethernet's IPv4/IPv6 there. The
        elements keep their identity, so registered names and anything built
        on top of them (BGP, ...) follow."""
        for ip_node in ("ipv4", "ipv6"):
            elements = ixn_ethernet.pop(ip_node, None)
            if elements is not None:
                ixn_node.setdefault(ip_node, []).extend(elements)

    def _config_static_key(self, secy, ixn_node, descriptor):
        self.logger.debug("Configuring static key")
        key_generation_protocol = secy.get("key_generation_protocol")
        static_key = key_generation_protocol.get("static_key")
        if static_key is None:
            return
        self._config_static_key_cipher(static_key, ixn_node)
        self._config_static_key_tx(static_key, ixn_node, descriptor)
        self._config_static_key_rx(static_key, ixn_node)

    def _config_static_key_cipher(self, static_key, ixn_node):
        self.logger.debug("Configuring cipher for static key")
        self.configure_multivalues(static_key, ixn_node, Macsec._CIPHER)

    def _config_data_plane(self, device, ethernet_interface, ixn_node, engine):
        self.logger.debug("Configuring data plane properties")
        secy = ethernet_interface.get("secure_entity")
        encapsulation = secy.get("data_plane").get("encapsulation")
        if encapsulation is None:
            return
        self._config_data_plane_tx(encapsulation, ixn_node)
        self._config_vlan_options(encapsulation, ixn_node)
        if Macsec._ENGINES[engine]["replay"]:
            self._hw.config_replay(secy, encapsulation, ixn_node)
        self._config_crypto_engine(
            device, ethernet_interface, ixn_node, engine
        )

    def _config_vlan_options(self, encapsulation, ixn_node):
        """encrypt_interface_vlans false sends the Ethernet VLANs as clear
        text before the SecTAG. IxNetwork's enableClearTextVlans is a plain
        bool whose default (false) means encrypted VLANs."""
        vlan_options = encapsulation.get("vlan_options")
        if vlan_options is None:
            return
        encrypt = vlan_options.get("encrypt_interface_vlans")
        if encrypt is not None:
            ixn_node["enableClearTextVlans"] = not encrypt

    def _config_data_plane_tx(self, encapsulation, ixn_node):
        self.logger.debug("Configuring data plane Tx properties")
        tx = encapsulation.get("tx")
        if tx is None:
            return
        self.logger.debug(
            "end_station %s include_sci %s" % (tx.end_station, tx.include_sci)
        )
        self.configure_multivalues(tx, ixn_node, Macsec._DATA_PLANE_TX)

    def _config_crypto_engine(
        self, device, ethernet_interface, ixn_node, engine
    ):
        self.logger.debug("Configuring crypto engine properties")
        secy = ethernet_interface.get("secure_entity")
        crypto_engine = secy.data_plane.encapsulation.crypto_engine
        if engine == "encrypt_only":
            self._config_crypto_engine_encrypt_only(
                device, ethernet_interface, ixn_node
            )
        elif Macsec._ENGINES[engine]["tx_pn"] == "single":
            self._config_crypto_engine_encrypt_decrypt(
                crypto_engine.encrypt_decrypt, ixn_node
            )

    def _config_crypto_engine_encrypt_decrypt(self, encrypt_decrypt, ixn_node):
        tx_pn = encrypt_decrypt.get("tx_pn")
        if tx_pn is None:
            return
        self.configure_multivalues(
            tx_pn, ixn_node, Macsec._ENCRYPT_DECRYPT_TX_PN
        )

    def _config_static_key_tx(self, static_key, ixn_node, descriptor):
        self.logger.debug("Configuring Tx properties for static key")
        tx = static_key.get("tx")
        if tx is None:
            return
        self._config_static_key_txsc(static_key, ixn_node)
        if descriptor["pn_based"]:
            self._hw.config_rekey_mode(tx.rekey_mode, ixn_node)
        else:
            self._config_rekey_mode(tx.rekey_mode, ixn_node)

    def _config_static_key_rx(self, static_key, ixn_node):
        self.logger.debug("Configuring Rx properties for static key")
        rx = static_key.get("rx")
        if rx is None:
            return
        self._config_static_key_rxsc(static_key, ixn_node)

    def _config_sak_pool(
        self, direction, static_key, secure_channel, ixn_node
    ):
        """Create the Tx or Rx SAK pool. direction is "tx" or "rx"."""
        saks = secure_channel.saks
        ixn_node["%sSakPoolSize" % direction] = len(saks)
        ixn_pool = self.create_node_elemet(
            ixn_node, "%sSakPool" % direction, name=None
        )
        values = [sak.sak for sak in saks]
        cipher_suite = static_key.cipher_suite
        if cipher_suite in ("gcm_aes_128", "gcm_aes_xpn_128"):
            ixn_pool["%sSak128" % direction] = self.multivalue(values)
        elif cipher_suite in ("gcm_aes_256", "gcm_aes_xpn_256"):
            ixn_pool["%sSak256" % direction] = self.multivalue(values)
        if cipher_suite in ("gcm_aes_xpn_128", "gcm_aes_xpn_256"):
            ixn_pool["%sSsci" % direction] = self.multivalue(
                [sak.ssci for sak in saks]
            )
            ixn_pool["%sSalt" % direction] = self.multivalue(
                [sak.salt for sak in saks]
            )

    def _config_static_key_txsc(self, static_key, ixn_node):
        self.logger.debug("Configuring Tx secure channels for static key")
        txsc = static_key.get("tx").get("secure_channels")[0]
        self.configure_multivalues(txsc, ixn_node, Macsec._STATIC_KEY_TXSC)
        self._config_sak_pool("tx", static_key, txsc, ixn_node)

    def _config_static_key_rxsc(self, static_key, ixn_node):
        self.logger.debug("Configuring Rx secure channels for static key")
        rxsc = static_key.get("rx").get("secure_channels")[0]
        self.configure_multivalues(rxsc, ixn_node, Macsec._STATIC_KEY_RXSC)
        self._config_sak_pool("rx", static_key, rxsc, ixn_node)

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
        traffic_options = (
            secy.data_plane.encapsulation.crypto_engine.encrypt_only.get(
                "traffic_options"
            )
        )
        if traffic_options is not None:
            send_gratuitous_arp = traffic_options.get("send_gratuitous_arp")
            if send_gratuitous_arp is not None:
                ixn_staticmacsec["sendGratArp"] = send_gratuitous_arp
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
