"""
Shared constants for device configuration mappings.

This module contains common configuration dictionaries used across
multiple device types (BGP, BGP-EVPN, ISIS, MACsec, MKA) to eliminate
code duplication and improve maintainability.
"""

# AS Path configuration (used by BGP and BGP-EVPN)
AS_SET_MODE = {
    "do_not_include_local_as": "dontincludelocalas",
    "include_as_seq": "includelocalasasasseq",
    "include_as_set": "includelocalasasasset",
    "include_as_confed_seq": "includelocalasasasseqconfederation",
    "include_as_confed_set": "includelocalasasassetconfederation",
    "prepend_to_first_segment": "prependlocalastofirstsegment",
}

SEGMENT_TYPE = {
    "as_seq": "asseq",
    "as_set": "asset",
    "as_confed_seq": "asseqconfederation",
    "as_confed_set": "assetconfederation",
}

# IP Pool configuration (used by BGP, BGP-EVPN, ISIS)
IP_POOL_MAPPING = {
    "address": "networkAddress",
    "prefix": "prefixLength",
    "count": "numberOfAddressesAsy",
    "step": "prefixAddrStep",
}

# Cipher Suite configuration (used by MACsec and MKA)
CIPHER_SUITE_MAPPING = {
    "gcm_aes_128": "aes128",
    "gcm_aes_256": "aes256",
    "gcm_aes_xpn_128": "aesxpn128",
    "gcm_aes_xpn_256": "aesxpn256",
}

# Community configuration (used by BGP and BGP-EVPN)
COMMUNITY_TYPE_MAPPING = {
    "manual_as_number": "manual",
    "no_export": "noexport",
    "no_advertised": "noadvertised",
    "no_export_subconfed": "noexport_subconfed",
    "llgr_stale": "llgr_stale",
    "no_llgr": "no_llgr",
}
