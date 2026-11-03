"""Hardware (inline crypto) MACsec engine.

Only what differs from the software engine lives here. Everything else
(cipher, secure channels, SAK pools, Tx PN, data plane Tx, MKA hookup, name
registration) is shared with the software engine in macsec.py and driven by
the engine descriptor below.

The hardware engine is the NGPF ``macsec`` node, selected by
``crypto_engine.encrypt_decrypt`` with
``hardware_acceleration.choice = inline_crypto``.
"""

from snappi_ixnetwork.device.base import Base
from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.logger import get_ixnet_logger

# Engine descriptor, see Macsec._ENGINES
ENGINE_KEY = "encrypt_decrypt_inline_crypto"
ENGINE = {
    "node": "macsec",
    "traffic_type": None,
    "ip_restricted": False,
    "tx_pn": "single",
    "pn_based": True,
    "replay": True,
    # IPv4/IPv6 must sit on the macsec node, or flows bypass the SecY
    "ip_under_node": True,
}


class MacsecHw(Base):
    _REPLAY = {
        "replay_window": "replayWindowSize",
    }

    def __init__(self):
        super(MacsecHw, self).__init__()
        self.logger = get_ixnet_logger(__name__)

    def config_replay(self, secy, encapsulation, ixn_macsec):
        """Rx replay window. replay_protection is a per port setting in
        IxNetwork (Globals.Topology.Macsec), see port_settings()."""
        rx = encapsulation.get("rx")
        if rx is None:
            return
        if rx.get("replay_window") is not None:
            self.configure_multivalues(rx, ixn_macsec, MacsecHw._REPLAY)

    def config_rekey_mode(self, rekey_mode, ixn_macsec):
        """Tx rekey. Unlike the software node, the hardware node has a
        rekeyMode (timerBased or pnBased)."""
        self.logger.debug("Configuring Tx rekey for hardware MACsec")
        if rekey_mode.choice == "dont_rekey":
            ixn_macsec["rekeyMode"] = "timerBased"
            ixn_macsec["rekeyBehaviour"] = "dontRekey"
        elif rekey_mode.choice == "timer_based":
            timer_based = rekey_mode.timer_based
            ixn_macsec["rekeyMode"] = "timerBased"
            ixn_macsec["periodicRekeyInterval"] = timer_based.interval
            if timer_based.choice == "fixed_count":
                ixn_macsec["rekeyBehaviour"] = "rekeyFixedCount"
                ixn_macsec["periodicRekeyAttempts"] = timer_based.fixed_count
            elif timer_based.choice == "continuous":
                ixn_macsec["rekeyBehaviour"] = "rekeyContinuous"
        elif rekey_mode.choice == "pn_based":
            ixn_macsec["rekeyMode"] = "pnBased"
            ixn_macsec["rekeyBehaviour"] = "rekeyContinuous"

    # Per port settings, IxNetwork Globals.Topology.Macsec ------------------
    _RX_SC_IDENTIFYING_FIELD = {
        "source_mac": "rxscidentifyingfieldsrcmac",
        "sci_system_id": "rxscidentifyingfieldscisystemid",
        "sci_port_id": "rxscidentifyingfieldsciportid",
    }
    _MAX_CA_COUNT = {
        "one": "macsecmaxcaone",
        "two": "macsecmaxcatwo",
        "four": "macsecmaxcafour",
        "eight": "macsecmaxcaeight",
        "sixteen": "macsecmaxcasixteen",
        "thirty_two": "macsecmaxcathirtytwo",
        "sixty_four": "macsecmaxcasixtyfour",
        "one_twenty_eight": "macsecmaxcaonehundredtwentyeight",
        "two_fifty_six": "macsecmaxcatwohundredfiftysix",
    }
    _CA_COUNT = {
        "one": 1,
        "two": 2,
        "four": 4,
        "eight": 8,
        "sixteen": 16,
        "thirty_two": 32,
        "sixty_four": 64,
        "one_twenty_eight": 128,
        "two_fifty_six": 256,
    }
    _TYPE_OF_CA = {
        "pairwise_ca": "pairwiseca",
        "single_dut_tx_sc": "groupwithsingledut",
        "multiple_dut_tx_sc": "groupwithmultidut",
    }

    @staticmethod
    def is_inline_crypto(secy):
        data_plane = secy.get("data_plane")
        if data_plane is None or data_plane.choice != "encapsulation":
            return False
        crypto_engine = data_plane.encapsulation.crypto_engine
        if crypto_engine.choice != "encrypt_decrypt":
            return False
        acceleration = crypto_engine.encrypt_decrypt.hardware_acceleration
        return acceleration.choice == "inline_crypto"

    @staticmethod
    def _secys_per_port(config):
        """port name -> list of inline crypto secure entities on the port"""
        ports = {}
        for device in config.devices:
            macsec = device.get("macsec")
            if macsec is None:
                continue
            ethernets = {
                ethernet.get("name"): ethernet
                for ethernet in device.get("ethernets") or []
            }
            for iface in macsec.get("ethernet_interfaces") or []:
                secy = iface.get("secure_entity")
                if secy is None or not MacsecHw.is_inline_crypto(secy):
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
                if port_name is not None:
                    ports.setdefault(port_name, []).append(secy)
        return ports

    @staticmethod
    def _per_port_options(config):
        """port name -> MacsecPerPortSettings of per_port_options"""
        options = config.get("options")
        result = {}
        if options is None:
            return result
        for per_port in options.per_port_options:
            for protocol in per_port.protocols:
                # iterating yields the object of the choice, as for flow
                # headers
                if protocol.parent.choice == "macsec":
                    result[per_port.port_name] = protocol
        return result

    @staticmethod
    def port_settings(config):
        """Settings for Globals.Topology.Macsec, as {IxNetwork attribute:
        value}. KeyGenerationMode is not among them: IxNetwork derives it
        (read only) from the configuration. They are the same for every hardware port because the
        IxNetwork global is one multivalue for all ports: differing values
        are rejected. Returns {} when no hardware secure entity exists.
        Raises SnappiIxnException(400) for what cannot be realised. Needs no
        IxNetwork connection."""
        logger = get_ixnet_logger(__name__)
        secys_per_port = MacsecHw._secys_per_port(config)
        per_port = MacsecHw._per_port_options(config)
        for port_name in per_port:
            if port_name not in secys_per_port:
                logger.warning(
                    "Port %s has MACsec per port options but no inline crypto "
                    "secure entity, the options are ignored" % port_name
                )
        by_port = {}
        for port_name, secys in secys_per_port.items():
            attrs = MacsecHw._port_attrs(
                port_name, secys, per_port.get(port_name)
            )
            by_port[port_name] = attrs
        first = None
        for port_name, attrs in by_port.items():
            if first is None:
                first = (port_name, attrs)
            elif attrs != first[1]:
                raise SnappiIxnException(
                    400,
                    "Inline crypto MACsec per port settings differ between "
                    "ports %s and %s (%s vs %s). IxNetwork holds them in one "
                    "global, so they must be the same on every port"
                    % (
                        first[0],
                        port_name,
                        sorted(first[1].items()),
                        sorted(attrs.items()),
                    ),
                )
        return {} if first is None else dict(first[1])

    @staticmethod
    def _port_attrs(port_name, secys, options):
        attrs = {}
        replay = set()
        for secy in secys:
            encapsulation = secy.data_plane.encapsulation
            rx = encapsulation.get("rx")
            if rx is not None and rx.get("replay_protection") is not None:
                replay.add(bool(rx.get("replay_protection")))
        if len(replay) > 1:
            raise SnappiIxnException(
                400,
                "Port %s: replay_protection differs between secure entities. "
                "It is a per port setting" % port_name,
            )
        if len(replay) == 1:
            attrs["ReplayProtection"] = replay.pop()
        if options is None:
            return attrs
        validate_frames = options.get("validate_frames")
        if validate_frames is not None and validate_frames.choice == "strict":
            raise SnappiIxnException(
                400,
                "Port %s: validate_frames strict is not supported, IxNetwork "
                "only offers check" % port_name,
            )
        if validate_frames is not None and validate_frames.choice == "check":
            attrs["MacsecValidation"] = "check"
        acceleration = options.get("hardware_acceleration")
        if acceleration is None or acceleration.choice != "inline_crypto":
            return attrs
        inline = acceleration.inline_crypto
        attrs["RxSecTagOffset"] = inline.rx_sectag_offset
        attrs["RxScIdentifyingField"] = MacsecHw._RX_SC_IDENTIFYING_FIELD[
            inline.rx_sc_identifying_field
        ]
        max_ca = inline.max_ca_count
        if len(secys) > MacsecHw._CA_COUNT[max_ca]:
            raise SnappiIxnException(
                400,
                "Port %s has %d inline crypto secure entities but "
                "max_ca_count is %s" % (port_name, len(secys), max_ca),
            )
        attrs["MaxCaCount"] = MacsecHw._MAX_CA_COUNT[max_ca]
        type_of_ca = inline.type_of_ca
        if type_of_ca.choice == "group_ca":
            group = type_of_ca.group_ca
            attrs["TypeOfCa"] = MacsecHw._TYPE_OF_CA[group.choice]
            if group.choice == "multiple_dut_tx_sc":
                attrs["MaxDutTxScPerCa"] = (
                    group.multiple_dut_tx_sc.max_dut_tx_sc_per_ca
                )
        else:
            attrs["TypeOfCa"] = MacsecHw._TYPE_OF_CA[
                type_of_ca.choice or "pairwise_ca"
            ]
        return attrs

    @staticmethod
    def apply_port_settings(ixnetwork, config):
        """Write the port settings to Globals.Topology.Macsec. Needs the
        topology to exist, so it runs after the configuration is pushed and
        before the protocols start."""
        attrs = MacsecHw.port_settings(config)
        if len(attrs) == 0:
            return
        logger = get_ixnet_logger(__name__)
        glob = ixnetwork.Globals.Topology.find().Macsec.find()
        for name, value in sorted(attrs.items()):
            logger.debug("MACsec per port %s = %s" % (name, value))
            if isinstance(value, bool):
                value = "true" if value else "false"
            getattr(glob, name).Single(str(value))
