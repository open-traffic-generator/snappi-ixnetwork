import json
import time
import re
from snappi_ixnetwork.timer import Timer
from snappi_ixnetwork.logger import get_ixnet_logger
import snappi


class IxNetworkConfig(object):
    """
    Represents the IxNetwork configuration, managing chassis chains.
    ixnconfig = api.ixnet_specific_config
    chassis_chain1 = ixnconfig.chassis_chains.add()
    chassis_chain1.primary = "10.36.78.236"
    chassis_chain1.topology = chassis_chain1.STAR
    secondary1 = chassis_chain1.secondary.add()
    secondary1.location = "10.36.78.141"
    secondary1.sequence_id = "2"
    secondary1.cable_length = "6"
    """

    _TYPE = {"chassis_chains": {"type": "ChassisChainIter"}}

    def __init__(self, ixnetworkapi):
        """
        Initializes the IxNetworkConfig object.

        :param ixnetworkapi: API object for interacting with IxNetwork.
        :param chassis_chains: Object to add new chassis chain objects
        """
        print(f"End {object.__class__}")
        self._api = ixnetworkapi
        self._chassis_chains = None

    @property
    def chassis_chains(self):
        """
        Retrieves the chassis chains configuration.

        :return: ChassisChainIter object.
        """
        if self._chassis_chains is None:
            self._chassis_chains = ChassisChainIter()

        return self._chassis_chains

    def config(self):
        """
        Logs configuration settings for IxNetwork.
        """
        self.logger.info("Configuring IxNConfig")


class ChassisChain(object):
    """
    Represents a chassis chain configuration in the network.
    """

    _TYPES = {
        "primary": {"type": str},
        "topology": {"type": str},
        "enum": [
            "daisy",
            "star",
        ],
        "secondary": {"type": "SecondaryIter"},
    }

    _REQUIRED = ("primary",)

    DAISY = "daisy"
    STAR = "star"

    def __init__(self, primary=None, topology=None):
        """
        Initializes a ChassisChain object.

        :param primary: Primary chassis.
        :param topology: Network topology (daisy or star).
        """
        super(ChassisChain, self).__init__()
        self._primary = primary
        self._topology = topology
        self._secondary = None

    def set(self, primary=None, topology=None):
        """
        Sets the primary chassis and topology.

        :param primary: Primary chassis.
        :param topology: Network topology (daisy or star).
        """
        self._topology = topology
        self._primary = primary

    @property
    def primary(self):
        """
        Gets the primary chassis.
        """
        return self._primary

    @primary.setter
    def primary(self, value):
        """
        Sets the primary chassis.

        :param value: Primary chassis value.
        :raises TypeError: If value is None.
        """
        if value is None:
            raise TypeError("Cannot set required property primary as None")
        self._primary = value

    @property
    def topology(self):
        """
        Gets the topology type.
        """
        return self._topology

    @topology.setter
    def topology(self, value):
        """
        Sets the topology type.

        :param value: Topology type (daisy or star).
        :raises TypeError: If value is None.
        """
        if value is None:
            raise TypeError("Cannot set required property topology as None")
        self._topology = value

    @property
    def secondary(self):
        """
        Retrieves the secondary chassis configuration.
        """
        if self._secondary is None:
            self._secondary = SecondaryIter()

        return self._secondary


class ChassisChainIter(snappi.snappi.OpenApiIter):
    """
    Iterator class for managing multiple ChassisChain objects.
    """

    def __init__(self):
        super(ChassisChainIter, self).__init__()

    def __getitem__(self, key):
        return self._getitem(key)

    def __iter__(self):
        return self._iter()

    def __next__(self):
        return self._next()

    def next(self):
        return self._next()

    def _instanceOf(self, item):
        """
        Ensures that the item is an instance of ChassisChain.
        """
        if not isinstance(item, ChassisChain):
            raise Exception("Item is not an instance of ChassisChain")

    def chassisChain(self, primary=None, topology=None):
        """
        Adds a new ChassisChain object to the iterator.
        """
        item = ChassisChain(primary=primary, topology=topology)
        self._add(item)
        return self

    def add(self, primary=None, topology=None):
        """
        Adds a new ChassisChain instance to the list.
        """
        item = ChassisChain(primary=primary)
        self._add(item)
        return item


class Secondary(object):
    """
    Initializes a Secondary chassis object.

    :param location: Secondary chassis.
    :param sequence_id: Sequence ID of the secondary chassis.
    :param cable_length: Cable Length of the secondary chassis.
    """

    """
    Represents a secondary chassis configuration.
    """
    _TYPES = {
        "location": {"type": str},
        "sequence_id": {"type": int},
        "cable_length": {"type": int},
    }

    _REQUIRED = ("location",)

    def __init__(self, location=None, sequence_id=None, cable_length=None):
        super(Secondary, self).__init__()
        self._location = location
        self._sequence_id = sequence_id
        self._cable_length = cable_length

    def set(self, location=None, sequence_id=None, cable_length=None):
        self._location = location
        self._sequence_id = sequence_id
        self._cable_length = cable_length

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        if value is None:
            raise TypeError("Cannot set required property location as None")
        self._location = value

    @property
    def sequence_id(self):
        return self._sequence_id

    @sequence_id.setter
    def sequence_id(self, value):
        if value is None:
            raise TypeError("Cannot set required property sequence_id as None")
        self._sequence_id = value

    @property
    def cable_length(self):
        return self._cable_length

    @cable_length.setter
    def cable_length(self, value):
        if value is None:
            raise TypeError(
                "Cannot set required property cable_length as None"
            )
        self._cable_length = value


class SecondaryIter(snappi.snappi.OpenApiIter):
    """
    Iterator class for managing multiple Secondary objects.
    """

    def __init__(self):
        super(SecondaryIter, self).__init__()

    def __getitem__(self, key):
        return self._getitem(key)

    def __iter__(self):
        return self._iter()

    def __next__(self):
        return self._next()

    def next(self):
        return self._next()

    def _instanceOf(self, item):
        if not isinstance(item, Secondary):
            raise Exception("Item is not an instance of Port")

    def secondary(self, location=None, sequence_id=None, cable_length=None):
        item = Secondary(
            location=location,
            sequence_id=sequence_id,
            cable_length=cable_length,
        )
        self._add(item)
        return self

    def add(self, location=None, sequence_id=None, cable_length=None):
        item = Secondary(
            location=location,
            sequence_id=sequence_id,
            cable_length=cable_length,
        )
        self._add(item)
        return item
