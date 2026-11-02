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
        IxNetwork (Globals.Topology.Macsec), applied with the per port
        options, so it is only reported here."""
        rx = encapsulation.get("rx")
        if rx is None:
            return
        if rx.get("replay_window") is not None:
            self.configure_multivalues(rx, ixn_macsec, MacsecHw._REPLAY)
        if rx.get("replay_protection"):
            self.logger.warning(
                "Secure entity %s: replay_protection is a per port setting "
                "that is not applied yet; only replay_window is configured."
                % secy.get("name")
            )

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
