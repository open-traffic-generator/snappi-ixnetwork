from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.logger import get_ixnet_logger


class Mka(Base):
    _BASIC = {
        "key_derivation_function": {
            "ixn_attr": "keyDerivationFunction",
            "enum_map": {"aes_cmac_128": "aescmac128", "aes_cmac_256": "aescmac256"},
        },
        "macsec_capability": {
            "ixn_attr": "macsecCapability",
            "enum_map": {"macsec_not_implemented": "macsecnotimplemented",
                         "macsec_integrity_without_confidentiality": "macsecintegritywithoutconfidentiality",
                         "macsec_integrity_with_no_confidentiality_offset": "acsecintegritywithnoconfidentialityoffset",
                         "macsec_integrity_with_confidentiality_offset": "macsecintegritywithconfidentialityoffset"},
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
            "enum_map": {"no_confidentiality": "noconfidentiality",
                         "no_confidentiality_offset": "noconfidentialityoffset",
                         "confidentiality_offset_30_octets": "confidentialityoffset30octets",
                         "confidentiality_offset_50_octets": "confidentialityoffset50octets"},
        },
        "cipher_suite": {
            "ixn_attr": "cipherSuite",
            "enum_map": {"gcm_aes_128": "aes128",
                         "gcm_aes_256": "aes256",
                         "gcm_aes_xpn_128":"aesxpn128",
                         "gcm_aes_xpn_256":"aesxpn256"},
        },
        "starting_key_number": "startingKeyNumber",
        "starting_distributed_an": "startingDistributedAN",
        "rekey_threshold_pn": "rekeyThresholdPN",
        "rekey_threshold_xpn":"rekeyThresholdXPN",
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
        self.logger.debug("Configuring MKA")
        mka = device.get("mka")
        if mka is None:
            return
        self._config_ethernet_interfaces(device)

    def _is_valid(self, ethernet_name, kay):
        is_valid = True
        if kay is None:
            is_valid = False
        else:
            self.logger.debug("Validating KaY of etherner interface %s" % (ethernet_name))
            txscs = kay.get("txscs")
            if len(txscs) > 1:
                self._ngpf.api.add_error(
                    "More than one TxSC added when key generation is static".format(
                        name=ethernet_name
                    )
                )
                is_valid = False
        if is_valid == True:
            self.logger.debug("MKA validation success")
        else:
            self.logger.debug("MKA validation failure")
        return is_valid

    def _config_ethernet_interfaces(self, device):
        self.logger.debug("Configuring MKA interfaces")
        mka = device.get("mka")
        ethernet_interfaces = mka.get("ethernet_interfaces")
        if ethernet_interfaces is None:
            return
        for ethernet_interface in ethernet_interfaces:
            ethernet_name = ethernet_interface.get("eth_name")
            self._ngpf.working_dg = self._ngpf.api.ixn_objects.get_working_dg(
                ethernet_name
            )
            if not self._is_valid(ethernet_name, ethernet_interface.get("kay")):
                continue
            self._config_kay(device, ethernet_interface)

    def _config_kay(self, device, ethernet_interface):
        self.logger.debug("Configuring KaY")
        kay = ethernet_interface.get("kay")
        if kay is None:
            return
        ethernet_name = ethernet_interface.get("eth_name")
        ixn_ethernet = self._ngpf.api.ixn_objects.get_object(ethernet_name)
        ixn_mka = self.create_node_elemet(
            ixn_ethernet, "mka", kay.get("name")
        )
        self._ngpf.set_device_info(kay, ixn_mka)
        self._config_basic(kay, ixn_mka)
        self._config_txsc(kay, ixn_mka)
        self._config_keyserver(kay, ixn_mka)

    def _config_basic(self, kay, ixn_mka):
        self.logger.debug("Configuring basic properties")
        basic = kay.get("basic")
        self.configure_multivalues(basic, ixn_mka, Mka._BASIC)
        ixn_mka["mkaLifeTime"] = basic.mka_life_time
        ixn_mka["keyType"] =  basic.key_source.choice
        #TODO:supported_cipher_suites
        self._config_rekey_mode(basic, ixn_mka)

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
        txscs = kay.get("txscs")
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
