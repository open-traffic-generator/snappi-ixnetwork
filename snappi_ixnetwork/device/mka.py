from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.device.utils import items
from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.logger import get_ixnet_logger


class Mka(Base):
    _BASIC = {
        "key_derivation_function": {
            "ixn_attr": "keyDerivationFunction",
            "enum_map": {
                "aes_cmac_128": "aescmac128",
                "aes_cmac_256": "aescmac256",
            },
        },
        "macsec_capability": {
            "ixn_attr": "macsecCapability",
            "enum_map": {
                "macsec_not_implemented": "macsecnotimplemented",
                "macsec_integrity_without_confidentiality": "macsecintegritywithoutconfidentiality",
                "macsec_integrity_with_no_confidentiality_offset": "macsecintegritywithnoconfidentialityoffset",
                "macsec_integrity_with_confidentiality_offset": "macsecintegritywithconfidentialityoffset",
            },
        },
        "actor_priority": "keyServerPriority",
        "macsec_desired": "macsecDesired",
        "mka_version": "mkaVersion",
        "mka_hello_time": "mkaHelloTime",
        "send_icv_indicatior_in_mkpdu": "sendICVIndicator",
        "delay_protect": "delayProtect",
    }

    _KEY_SERVER = {
        "confidentialty_offset": {
            "ixn_attr": "confidentialityOffset",
            "enum_map": {
                "no_confidentiality": "noconfidentiality",
                "no_confidentiality_offset": "noconfidentialityoffset",
                "confidentiality_offset_30_octets": "confidentialityoffset30octets",
                "confidentiality_offset_50_octets": "confidentialityoffset50octets",
            },
        },
        "cipher_suite": {
            "ixn_attr": "cipherSuite",
            "enum_map": {
                "gcm_aes_128": "aes128",
                "gcm_aes_256": "aes256",
                "gcm_aes_xpn_128": "aesxpn128",
                "gcm_aes_xpn_256": "aesxpn256",
            },
        },
        "starting_key_number": "startingKeyNumber",
        "starting_distributed_an": "startingDistributedAN",
        "rekey_threshold_pn": "rekeyThresholdPN",
        "rekey_threshold_xpn": "rekeyThresholdXPN",
    }

    _TXSC = {
        "system_id": "systemId",
        "port_id": "portId",
        "starting_message_number": "startingMessageNumber",
    }

    def __init__(self, ngpf):
        super(Mka, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)

    def config(self, device):
        self.logger.debug("Configuring MKA protocol")
        macsec = device.get("macsec")
        if macsec is None:
            return
        self._config_ethernet_interfaces(device)

    # Per port settings, IxNetwork Globals.Topology.Mka ---------------------
    _DEFAULT_ETHER_TYPE = "888e"

    @staticmethod
    def _instances(config):
        """(port name, kay) of every MKA instance, in configuration order"""
        instances = []
        for device in items(config.devices):
            macsec = device.get("macsec")
            if macsec is None:
                continue
            ethernets = {
                ethernet.get("name"): ethernet
                for ethernet in items(device.get("ethernets"))
            }
            for iface in items(macsec.get("ethernet_interfaces")):
                secy = iface.get("secure_entity")
                if secy is None:
                    continue
                protocol = secy.get("key_generation_protocol")
                if protocol is None or protocol.choice != "mka":
                    continue
                kay = protocol.get("mka")
                if kay is None:
                    continue
                ethernet = ethernets.get(iface.get("eth_name"))
                connection = (
                    ethernet.get("connection") if ethernet is not None else None
                )
                port_name = (
                    connection.get("port_name")
                    if connection is not None
                    else None
                )
                instances.append((port_name, kay))
        return instances

    @staticmethod
    def _utc(kay):
        basic = kay.get("basic")
        if basic is None:
            return None
        start = basic.psk_chain_start_time
        if start.choice == "utc" and start.utc.day is not None:
            utc = start.utc
            return (
                utc.day,
                utc.month,
                utc.year,
                utc.hour,
                utc.minute,
                utc.second,
            )
        return None

    @staticmethod
    def first_test_start_time(config):
        """(kay name, utc tuple) of the first MKA instance with a user
        defined psk_chain_start_time, or None."""
        for _, kay in Mka._instances(config):
            utc = Mka._utc(kay)
            if utc is not None:
                return (kay.get("name"), utc)
        return None

    @staticmethod
    def port_settings(config):
        """Settings for Globals.Topology.Mka as {IxNetwork attribute: value}.
        IxNetwork keeps them per port and shared by all MKA instances on it,
        so the first instance on a port wins and a later one that differs is
        reported with a warning. The global is one multivalue for all ports,
        so values that differ between ports are rejected. Needs no IxNetwork
        connection."""
        logger = get_ixnet_logger(__name__)
        per_port = {}
        for port_name, kay in Mka._instances(config):
            basic = kay.get("basic")
            if basic is None:
                continue
            value = str(basic.eapol_ethernet_type).lower()
            if value.startswith("0x"):
                value = value[2:]
            if port_name not in per_port:
                per_port[port_name] = (kay.get("name"), value)
            elif per_port[port_name][1] != value:
                logger.warning(
                    "MKA %s: eapol_ethernet_type %s differs from %s of %s on "
                    "port %s. The first instance wins, it is a per port "
                    "setting" % (
                        kay.get("name"),
                        value,
                        per_port[port_name][1],
                        per_port[port_name][0],
                        port_name,
                    )
                )
        values = {v for _, v in per_port.values()}
        if len(values) > 1:
            raise SnappiIxnException(
                400,
                "MKA eapol_ethernet_type differs between ports (%s). IxNetwork "
                "holds it in one global, so it must be the same on every port"
                % ", ".join(
                    "%s: %s" % (p, v) for p, (_, v) in sorted(per_port.items(), key=lambda i: str(i[0]))
                ),
            )
        first = Mka.first_test_start_time(config)
        if first is not None:
            for _, kay in Mka._instances(config):
                utc = Mka._utc(kay)
                if utc is not None and utc != first[1]:
                    logger.warning(
                        "MKA %s: psk_chain_start_time differs from %s. It is "
                        "a per port setting, the first instance wins"
                        % (kay.get("name"), first[0])
                    )
        attrs = {}
        if len(values) == 1 and values != {Mka._DEFAULT_ETHER_TYPE}:
            attrs["EtherType"] = values.pop()
        return attrs

    @staticmethod
    def apply_port_settings(ixnetwork, config):
        """Write the per port settings, after the configuration is pushed."""
        attrs = Mka.port_settings(config)
        if len(attrs) == 0:
            return
        glob = ixnetwork.Globals.Topology.find().Mka.find()
        for name, value in sorted(attrs.items()):
            getattr(glob, name).Single(str(value))

    def _is_valid(self, ethernet_name, kay):
        is_valid = True
        if kay is None:
            is_valid = False
        else:
            self.logger.debug(
                "Validating KaY of ethernert interface %s" % (ethernet_name)
            )
            # Validate basic properties
            basic = kay.get("basic")
            key_src = basic.key_source
            if key_src.choice == "psk":
                psks = key_src.psks
                if len(psks) == 0:
                    self._ngpf.api.add_error(
                        "No PSK added on ethernet %s" % ethernet_name
                    )
                    is_valid = False
            else:
                raise SnappiIxnException(
                    400,
                    "Ethernet %s: MKA key_source %s is not supported, only "
                    "psk is" % (ethernet_name, key_src.choice),
                )
            # Validate TxSC properties
            tx = kay.get("tx")
            txscs = tx.get("secure_channels")
            if len(txscs) == 0:
                self._ngpf.api.add_error(
                    "No TxSC added on ethernet %s" % ethernet_name
                )
                is_valid = False
            elif len(txscs) > 1:
                self._ngpf.api.add_error(
                    "More than one TxSC added on ethernet %s" % ethernet_name
                )
                is_valid = False
        if is_valid == True:
            self.logger.debug("MKA validation success")
        else:
            self.logger.debug("MKA validation failure")
        return is_valid

    def _config_ethernet_interfaces(self, device):
        self.logger.debug("Configuring MKA interfaces")
        macsec = device.get("macsec")
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return
        for ethernet_interface in ethernet_interfaces:
            ethernet_name = ethernet_interface.get("eth_name")
            secy = ethernet_interface.get("secure_entity")
            if secy is None:
                continue
            key_generation_protocol = secy.get("key_generation_protocol")
            if key_generation_protocol is None:
                continue
            protocol = key_generation_protocol.choice
            if protocol != "mka":
                continue
            kay = key_generation_protocol.get("mka")
            if kay is None:
                continue
            if not self._is_valid(ethernet_name, kay):
                continue
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            self._config_kay(ethernet_interface, kay)

    def _config_kay(self, ethernet_interface, kay):
        self.logger.debug("Configuring KaY")
        ethernet_name = ethernet_interface.get("eth_name")
        ixn_ethernet = self._ngpf.api.ixn_objects.get_object(ethernet_name)
        ixn_mka = self.create_node_elemet(ixn_ethernet, "mka", kay.get("name"))
        self._ngpf.set_device_info(kay, ixn_mka)
        self._config_basic(kay, ixn_mka)
        self._config_txsc(kay, ixn_mka)
        self._config_keyserver(kay, ixn_mka)

    def _config_basic(self, kay, ixn_mka):
        self.logger.debug("Configuring basic properties")
        basic = kay.get("basic")
        self.configure_multivalues(basic, ixn_mka, Mka._BASIC)
        ixn_mka["mkaLifeTime"] = basic.mka_life_time
        ixn_mka["keyType"] = basic.key_source.choice
        self._config_key_source(basic, ixn_mka)
        self._config_rekey_mode(basic, ixn_mka)
        self._config_supported_cipher_suites(basic, ixn_mka)
        self._config_test_start_time(basic, ixn_mka, kay.get("name"))

    def _is_test_start_time_user_defined(self, macsec):
        self.logger.debug("Checking if MKA is configured")
        ethernet_interfaces = macsec.get("ethernet_interfaces")
        for ethernet_interface in ethernet_interfaces:
            secy = ethernet_interface.get("secure_entity")
            key_generation_protocol = secy.get("key_generation_protocol")
            protocol = key_generation_protocol.choice
            if protocol == "mka":
                kay = key_generation_protocol.get("mka")
                if kay:
                    basic = kay.get("basic")
                    psk_chain_start_time = basic.psk_chain_start_time
                    if (
                        psk_chain_start_time.choice == "utc"
                        and psk_chain_start_time.utc.day is not None
                    ):
                        return True
        return False

    def _clear_overlays_in_globals(self, macsec):
        if self._is_test_start_time_user_defined(macsec):
            ixn_mka_globals_port_settings = (
                self._ngpf._ixnetwork.Globals.Topology.find().Mka.find()
            )
            ixn_mka_globals_port_settings.TestStartTime.ClearOverlays()

    def _config_test_start_time(self, basic, ixn_mka, kay_name=None):
        self.logger.debug("Configuring test start time")
        # It is a per port IxNetwork global shared by every MKA instance, so
        # the first instance decides (Mka.port_settings warns on conflicts)
        first = Mka.first_test_start_time(self._ngpf.api.snappi_config)
        if first is not None and first[0] != kay_name:
            return
        psk_chain_start_time = basic.psk_chain_start_time
        if (
            psk_chain_start_time.choice == "utc"
            and psk_chain_start_time.utc.day is not None
        ):
            utc_day = str(psk_chain_start_time.utc.day)
            utc_month = str(psk_chain_start_time.utc.month)
            utc_year = str(psk_chain_start_time.utc.year)
            utc_hour = str(psk_chain_start_time.utc.hour)
            utc_minute = str(psk_chain_start_time.utc.minute)
            utc_second = str(psk_chain_start_time.utc.second)

            utc_time = (
                utc_day
                + "-"
                + utc_month
                + "-"
                + utc_year
                + " "
                + utc_hour
                + ":"
                + utc_minute
                + ":"
                + utc_second
            )

            ixn_topology = self._ngpf.api._ixnetwork.Globals.Topology.refresh()
            ixn_mka_global_port_settings = ixn_topology.find().Mka.find()
            ixn_mka_global_test_start_time = (
                ixn_mka_global_port_settings.TestStartTime
            )
            ixn_mka_global_test_start_time.ValueList(
                [utc_time] * ixn_mka_global_test_start_time.Count
            )
            self.logger.debug(
                "MKA global per port test start time set to %s"
                % ixn_mka_global_test_start_time
            )

    def _config_supported_cipher_suites(self, basic, ixn_mka):
        self.logger.debug(
            "Configuring basic properties: supported cipher suites"
        )
        supported_cipher_suites = "selectciphers"
        if basic.supported_cipher_suites.gcm_aes_128:
            supported_cipher_suites += " gcm_aes_128"
        if basic.supported_cipher_suites.gcm_aes_256:
            supported_cipher_suites += " gcm_aes_256"
        if basic.supported_cipher_suites.gcm_aes_xpn_128:
            supported_cipher_suites += " gcm_aes_xpn_128"
        if basic.supported_cipher_suites.gcm_aes_xpn_256:
            supported_cipher_suites += " gcm_aes_xpn_256"
        ixn_mka["supportedCipherSuites"] = supported_cipher_suites

    def _config_key_source(self, basic, ixn_mka):
        self.logger.debug("Configuring key source settings")
        key_src = basic.key_source
        if key_src.choice == "psk":
            psks = key_src.psks
            ixn_mka["cakCount"] = len(psks)
            cak_names = []
            cak_values = []
            cak_start_offset_times = []
            cak_lifetime_validities = []
            cak_durations = []
            overlapping_keys = False
            prev_end_offset_time_mm = 0
            for psk in psks:
                cak_names.append(psk.cak_name)
                cak_values.append(psk.cak_value)

                start_offset_time_hh = psk.start_offset_time.hh
                start_offset_time_mm = psk.start_offset_time.mm
                start_offset_time = (
                    str(start_offset_time_hh) + ":" + str(start_offset_time_mm)
                )
                cak_start_offset_times.append(start_offset_time)
                start_offset_time_mm = (
                    start_offset_time_hh * 60 + start_offset_time_mm
                )

                end_offset_time_hh = psk.end_offset_time.hh
                end_offset_time_mm = psk.end_offset_time.mm
                end_offset_time_mm = (
                    end_offset_time_hh * 60 + end_offset_time_mm
                )

                if not overlapping_keys:
                    if start_offset_time_mm < prev_end_offset_time_mm:
                        overlapping_keys = True
                    else:
                        prev_end_offset_time_mm = end_offset_time_mm
                duration_mm = 0
                if end_offset_time_mm == 0:
                    cak_lifetime_validities.append(True)
                else:
                    cak_lifetime_validities.append(False)
                    if end_offset_time_mm > start_offset_time_mm:
                        duration_mm = end_offset_time_mm - start_offset_time_mm
                duration_hh = int(duration_mm / 60)
                duration_mm = duration_mm % 60
                cak_duration = str(duration_hh) + ":" + str(duration_mm)
                cak_durations.append(cak_duration)

            ixn_psk = self.create_node_elemet(ixn_mka, "cakCache", name=None)
            key_derivation_function = basic.key_derivation_function
            ixn_psk["cakName"] = self.multivalue(cak_names)
            if key_derivation_function == "aes_cmac_128":
                ixn_psk["cakValue128"] = self.multivalue(cak_values)
            elif key_derivation_function == "aes_cmac_256":
                ixn_psk["cakValue256"] = self.multivalue(cak_values)
            ixn_psk["keyStartTime"] = self.multivalue(cak_start_offset_times)
            ixn_psk["lifetimeValidity"] = self.multivalue(
                cak_lifetime_validities
            )
            ixn_psk["overlappingKeys"] = overlapping_keys
            ixn_psk["keyDuration"] = self.multivalue(cak_durations)

    def _config_rekey_mode(self, basic, ixn_mka):
        self.logger.debug("Configuring rekey settings")
        rekey_mode = basic.rekey_mode
        if rekey_mode.choice == "dont_rekey":
            ixn_mka["rekeyMode"] = "timerBased"
            ixn_mka["rekeyBehaviour"] = "dontRekey"
        elif rekey_mode.choice == "timer_based":
            timer_based = rekey_mode.timer_based
            ixn_mka["rekeyMode"] = "timerBased"
            if timer_based.choice == "fixed_count":
                ixn_mka["rekeyBehaviour"] = "rekeyFixedCount"
                ixn_mka["periodicRekeyAttempts"] = timer_based.fixed_count
                ixn_mka["periodicRekeyInterval"] = timer_based.interval
            elif timer_based.choice == "continuous":
                ixn_mka["rekeyBehaviour"] = "rekeyContinuous"
                ixn_mka["periodicRekeyInterval"] = timer_based.interval
        elif rekey_mode.choice == "pn_based":
            ixn_mka["rekeyMode"] = "pNBased"
            ixn_mka["rekeyBehaviour"] = "rekeyContinuous"

    def _config_txsc(self, kay, ixn_mka):
        self.logger.debug("Configuring TxSC")
        tx = kay.get("tx")
        txscs = tx.get("secure_channels")
        txsc = txscs[0]
        ixn_txsc = self.create_node_elemet(
            ixn_mka, "txChannels", txsc.get("name")
        )
        self.logger.debug("ixn_txsc %s" % ixn_txsc)
        self.configure_multivalues(txsc, ixn_txsc, Mka._TXSC)

    def _config_keyserver(self, kay, ixn_mka):
        self.logger.debug("Configuring key server")
        key_server = kay.get("key_server")
        if key_server is None:
            return
        self.configure_multivalues(key_server, ixn_mka, Mka._KEY_SERVER)
