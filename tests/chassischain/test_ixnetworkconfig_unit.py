import pytest

from snappi_ixnetwork.ixnetworkconfig import (
    ChassisChain,
    ChassisChainIter,
    IxNetworkConfig,
    Secondary,
    SecondaryIter,
)


def test_ixnetwork_config_lazily_creates_chassis_chains():
    config = IxNetworkConfig(object())

    chassis_chains = config.chassis_chains

    assert chassis_chains is config.chassis_chains
    assert isinstance(chassis_chains, ChassisChainIter)


def test_chassis_chain_set_and_properties():
    chassis_chain = ChassisChain()

    chassis_chain.set("primary-a", ChassisChain.STAR)

    assert chassis_chain.primary == "primary-a"
    assert chassis_chain.topology == ChassisChain.STAR

    chassis_chain.primary = "primary-b"
    chassis_chain.topology = ChassisChain.DAISY
    assert chassis_chain.primary == "primary-b"
    assert chassis_chain.topology == ChassisChain.DAISY


@pytest.mark.parametrize(
    "property_name",
    ["primary", "topology"],
)
def test_chassis_chain_required_properties_reject_none(property_name):
    chassis_chain = ChassisChain()

    with pytest.raises(TypeError, match="as None"):
        setattr(chassis_chain, property_name, None)


def test_chassis_chain_lazily_creates_secondary():
    chassis_chain = ChassisChain()

    secondary = chassis_chain.secondary

    assert secondary is chassis_chain.secondary
    assert isinstance(secondary, SecondaryIter)


def test_chassis_chain_iter_add_and_chassis_chain():
    iterator = ChassisChainIter()

    item = iterator.add("primary-a", ChassisChain.STAR)
    fluent_result = iterator.chassisChain("primary-b", ChassisChain.DAISY)

    assert isinstance(item, ChassisChain)
    assert item.primary == "primary-a"
    assert len(iterator) == 2
    assert fluent_result is iterator
    assert iterator[1].primary == "primary-b"
    assert iterator[1].topology == ChassisChain.DAISY


def test_chassis_chain_iter_rejects_non_chassis_chain():
    with pytest.raises(Exception, match="not an instance of ChassisChain"):
        ChassisChainIter()._instanceOf(object())


def test_chassis_chain_iter_supports_iteration_protocol():
    iterator = ChassisChainIter()
    iterator.add("primary-a")
    iterator.add("primary-b")

    assert [item.primary for item in iterator] == ["primary-a", "primary-b"]

    iterator = ChassisChainIter()
    iterator.add("primary-a")
    iterator.add("primary-b")
    iter(iterator)
    assert iterator.next().primary == "primary-a"
    assert next(iterator).primary == "primary-b"


def test_secondary_set_and_properties():
    secondary = Secondary()

    secondary.set("secondary-a", 2, 6)

    assert secondary.location == "secondary-a"
    assert secondary.sequence_id == 2
    assert secondary.cable_length == 6

    secondary.location = "secondary-b"
    secondary.sequence_id = 3
    secondary.cable_length = 7
    assert secondary.location == "secondary-b"
    assert secondary.sequence_id == 3
    assert secondary.cable_length == 7


@pytest.mark.parametrize(
    "property_name",
    ["location", "sequence_id", "cable_length"],
)
def test_secondary_required_properties_reject_none(property_name):
    secondary = Secondary()

    with pytest.raises(TypeError, match="as None"):
        setattr(secondary, property_name, None)


def test_secondary_iter_add_and_secondary():
    iterator = SecondaryIter()

    item = iterator.add("secondary-a", 2, 6)
    fluent_result = iterator.secondary("secondary-b", 3, 7)

    assert isinstance(item, Secondary)
    assert item.location == "secondary-a"
    assert len(iterator) == 2
    assert fluent_result is iterator
    assert iterator[1].location == "secondary-b"
    assert iterator[1].sequence_id == 3
    assert iterator[1].cable_length == 7


def test_secondary_iter_rejects_non_secondary():
    with pytest.raises(Exception, match="not an instance of Port"):
        SecondaryIter()._instanceOf(object())


def test_secondary_iter_supports_iteration_protocol():
    iterator = SecondaryIter()
    iterator.add("secondary-a")
    iterator.add("secondary-b")

    assert [item.location for item in iterator] == [
        "secondary-a",
        "secondary-b",
    ]

    iterator = SecondaryIter()
    iterator.add("secondary-a")
    iterator.add("secondary-b")
    iter(iterator)
    assert iterator.next().location == "secondary-a"
    assert next(iterator).location == "secondary-b"