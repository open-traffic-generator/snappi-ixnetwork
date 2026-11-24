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
from snappi_ixnetwork.device.utils import (
    items,
    topology_port_order,
    write_per_port,
)
from snappi_ixnetwork.exceptions import SnappiIxnException
from snappi_ixnetwork.logger import get_ixnet_logger

# Engine descriptor, see Macsec._ENGINES
ENGINE_KEY = "encrypt_decrypt_inline_crypto"
ENGINE = {
    "node": "macsec",
    "traffic_type": None,
    "ip_restricted": False,
    "tx_pn": "single",
    "pn_based_rekey": True,
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

    # IxNetwork defaults of the settings above. They are filled in before
    # ports are compared (a port that spells out a default is the same as one
    # that leaves it unset) and written explicitly, so a value left by an
    # earlier configuration in the same session never survives.
    _PORT_DEFAULTS = {
        "RxSecTagOffset": 12,
        "RxScIdentifyingField": "rxscidentifyingfieldsrcmac",
        "MaxCaCount": "macsecmaxcatwohundredfiftysix",
        "TypeOfCa": "pairwiseca",
    }
    _MAX_RX_SECTAG_OFFSET = 255

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
        for per_port in items(options.per_port_options):
            for protocol in items(per_port.protocols):
                # iterating yields the object of the choice, as for flow
                # headers
                if protocol.parent.choice == "macsec":
                    result[per_port.port_name] = protocol
        return result

    @staticmethod
    def port_settings(config):
        """Settings for Globals.Topology.Macsec as {port name: {IxNetwork
        attribute: value}}, for the ports that have an inline crypto secure
        entity. KeyGenerationMode is not among them: IxNetwork derives it
        (read only) from the configuration. Ports may differ from each
        other, as in ixhw-c. Raises SnappiIxnException(400) for what cannot
        be realised. Needs no IxNetwork connection."""
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
            MacsecHw._validate_uniform(port_name, secys)
            attrs = dict(MacsecHw._PORT_DEFAULTS)
            attrs.update(
                MacsecHw._port_attrs(port_name, secys, per_port.get(port_name))
            )
            by_port[port_name] = attrs
        return by_port

    @staticmethod
    def _rekey_signature(secy):
        """(rekey mode, rekey behaviour) of the static key Tx, None when the
        secure entity has no static key Tx rekey."""
        protocol = secy.get("key_generation_protocol")
        if protocol is None or protocol.choice != "static_key":
            return None
        static_key = protocol.get("static_key")
        tx = static_key.get("tx") if static_key is not None else None
        rekey_mode = tx.get("rekey_mode") if tx is not None else None
        if rekey_mode is None or rekey_mode.choice is None:
            return None
        behaviour = None
        if rekey_mode.choice == "timer_based":
            behaviour = rekey_mode.timer_based.choice
        return (rekey_mode.choice, behaviour)

    @staticmethod
    def _sak_counts(secy):
        """(Tx SAK count, Rx SAK count) of the static key secure channels"""
        protocol = secy.get("key_generation_protocol")
        if protocol is None or protocol.choice != "static_key":
            return None
        static_key = protocol.get("static_key")
        counts = []
        for direction in ("tx", "rx"):
            side = (
                static_key.get(direction) if static_key is not None else None
            )
            channels = side.get("secure_channels") if side is not None else None
            if channels is None or len(channels) == 0:
                counts.append(0)
            else:
                counts.append(len(channels[0].get("saks") or []))
        return tuple(counts)

    @staticmethod
    def _encrypt_interface_vlans(secy):
        encapsulation = secy.data_plane.encapsulation
        vlan_options = encapsulation.get("vlan_options")
        if vlan_options is None:
            return None
        return vlan_options.get("encrypt_interface_vlans")

    @staticmethod
    def _validate_uniform(port_name, secys):
        """The secure entities on one port must agree on these settings, 
        i.e., encrypt_interface_vlans, rekey mode
        and behaviour and the SAK counts."""
        checks = (
            ("encrypt_interface_vlans", MacsecHw._encrypt_interface_vlans),
            ("static_key tx rekey mode and behaviour", MacsecHw._rekey_signature),
            ("static_key Tx and Rx SAK counts", MacsecHw._sak_counts),
        )
        for label, getter in checks:
            values = {}
            for secy in secys:
                values.setdefault(getter(secy), []).append(secy.get("name"))
            if len(values) > 1:
                raise SnappiIxnException(
                    400,
                    "Port %s: inline crypto secure entities differ in %s "
                    "(%s). They must be the same on one port"
                    % (
                        port_name,
                        label,
                        "; ".join(
                            "%s: %s" % (value, ", ".join(names))
                            for value, names in sorted(
                                values.items(), key=lambda i: str(i[0])
                            )
                        ),
                    ),
                )

    @staticmethod
    def _port_attrs(port_name, secys, options):
        attrs = {}
        for secy in secys:
            encapsulation = secy.data_plane.encapsulation
            rx = encapsulation.get("rx")
            if rx is not None and rx.get("replay_protection"):
                raise SnappiIxnException(
                    400,
                    "Secure entity %s on port %s: replay_protection is not "
                    "supported by inline crypto MACsec"
                    % (secy.get("name"), port_name),
                )
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
        offset = inline.rx_sectag_offset
        if offset is not None and not (
            0 <= offset <= MacsecHw._MAX_RX_SECTAG_OFFSET
        ):
            raise SnappiIxnException(
                400,
                "Port %s: rx_sectag_offset %s is out of range, it must be "
                "between 0 and %d"
                % (port_name, offset, MacsecHw._MAX_RX_SECTAG_OFFSET),
            )
        attrs["RxSecTagOffset"] = offset
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
        by_port = MacsecHw.port_settings(config)
        if len(by_port) == 0:
            return
        logger = get_ixnet_logger(__name__)
        glob = ixnetwork.Globals.Topology.find().Macsec.find()
        port_order = topology_port_order(ixnetwork)
        names = set()
        for attrs in by_port.values():
            names.update(attrs)
        for name in sorted(names):
            values = {
                port: attrs[name]
                for port, attrs in by_port.items()
                if name in attrs
            }
            logger.debug("MACsec per port %s = %s" % (name, values))
            default = MacsecHw._PORT_DEFAULTS.get(name)
            if default is None:
                default = sorted(values.values(), key=str)[0]
            write_per_port(
                getattr(glob, name),
                {p: MacsecHw._to_text(v) for p, v in values.items()},
                MacsecHw._to_text(default),
                port_order,
            )

    @staticmethod
    def _to_text(value):
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
