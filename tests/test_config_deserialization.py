import pytest
import json
from abstract_open_traffic_generator.config import Config


def test_json_config(serializer, api):
    config = """{
        "device_groups": [
            {
                "name": "Tx Device Group",
                "devices": [
                    {
                        "ethernets": [
                            {
                                "name": "Tx Ethernet",
                                "mtu": null,
                                "mac": null,
                                "ipv4": {
                                    "prefix": {
                                        "fixed": "24",
                                        "choice": "fixed"
                                    },
                                    "bgpv4": null,
                                    "gateway": {
                                        "fixed": "192.168.1.1",
                                        "choice": "fixed"
                                    },
                                    "name": "Tx Ipv4",
                                    "address": {
                                        "fixed": "192.168.1.3",
                                        "choice": "fixed"
                                    }
                                },
                                "ipv6": null,
                                "vlans": null
                            }
                        ],
                        "devices_per_port": 1,
                        "networks": null,
                        "devices": null,
                        "name": "Tx Device"
                    }
                ],
                "port_names": [
                    "Tx"
                ]
            },
            {
                "name": "Rx Device Group",
                "devices": [
                    {
                        "ethernets": [
                            {
                                "name": "Rx Ethernet",
                                "mtu": null,
                                "mac": null,
                                "ipv4": {
                                    "prefix": {
                                        "fixed": "24",
                                        "choice": "fixed"
                                    },
                                    "bgpv4": null,
                                    "gateway": {
                                        "fixed": "192.168.1.1",
                                        "choice": "fixed"
                                    },
                                    "name": "Rx Ipv4",
                                    "address": {
                                        "fixed": "192.168.1.2",
                                        "choice": "fixed"
                                    }
                                },
                                "ipv6": null,
                                "vlans": null
                            }
                        ],
                        "devices_per_port": 1,
                        "networks": null,
                        "devices": null,
                        "name": "Rx Device"
                    }
                ],
                "port_names": [
                    "Rx"
                ]
            }
        ],
        "captures": null,
        "ports": [
            {
                "name": "Tx"
            },
            {
                "name": "Rx"
            }
        ],
        "flows": null
    }"""
    api.set_config(None)
    api.set_config(config)

def test_dict_config(serializer, api):
    config = {
        "device_groups": [
            {
                "name": "Tx Device Group",
                "devices": [
                    {
                        "ethernets": [
                            {
                                "name": "Tx Ethernet",
                                "mtu": None,
                                "mac": None,
                                "ipv4": {
                                    "prefix": {
                                        "fixed": "24",
                                        "choice": "fixed"
                                    },
                                    "bgpv4": None,
                                    "gateway": {
                                        "fixed": "192.168.1.1",
                                        "choice": "fixed"
                                    },
                                    "name": "Tx Ipv4",
                                    "address": {
                                        "fixed": "192.168.1.3",
                                        "choice": "fixed"
                                    }
                                },
                                "ipv6": None,
                                "vlans": None
                            }
                        ],
                        "devices_per_port": 1,
                        "networks": None,
                        "devices": None,
                        "name": "Tx Device"
                    }
                ],
                "port_names": [
                    "Tx"
                ]
            },
            {
                "name": "Rx Device Group",
                "devices": [
                    {
                        "ethernets": [
                            {
                                "name": "Rx Ethernet",
                                "mtu": None,
                                "mac": None,
                                "ipv4": {
                                    "prefix": {
                                        "fixed": "24",
                                        "choice": "fixed"
                                    },
                                    "bgpv4": None,
                                    "gateway": {
                                        "fixed": "192.168.1.1",
                                        "choice": "fixed"
                                    },
                                    "name": "Rx Ipv4",
                                    "address": {
                                        "fixed": "192.168.1.2",
                                        "choice": "fixed"
                                    }
                                },
                                "ipv6": None,
                                "vlans": None
                            }
                        ],
                        "devices_per_port": 1,
                        "networks": None,
                        "devices": None,
                        "name": "Rx Device"
                    }
                ],
                "port_names": [
                    "Rx"
                ]
            }
        ],
        "captures": None,
        "ports": [
            {
                "name": "Tx"
            },
            {
                "name": "Rx"
            }
        ],
        "flows": None
    }
    api.set_config(None)
    api.set_config(config)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
