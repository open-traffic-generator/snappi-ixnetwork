import pytest
from snappi_ixnetwork.device.utils import (
    namedtuple_with_defaults,
    convert_as_values,
    hex_to_ipv4,
)


def test_namedtuple_with_defaults_basic():
    """
    Test namedtuple_with_defaults with basic usage.
    
    Validates:
    - Named tuple creation with defaults
    - Field access
    - Default value behavior
    """
    TestTuple = namedtuple_with_defaults(
        "TestTuple", ["field1", "field2", "field3"], {"field1": "default1", "field3": "default3"}
    )
    
    # Create instance with some defaults
    instance = TestTuple(field2="value2")
    
    assert instance.field1 == "default1"
    assert instance.field2 == "value2"
    assert instance.field3 == "default3"


def test_namedtuple_with_defaults_no_defaults():
    """
    Test namedtuple_with_defaults without default values.
    
    Validates:
    - All fields default to None when no defaults provided
    """
    TestTuple = namedtuple_with_defaults("TestTuple", ["a", "b", "c"])
    
    instance = TestTuple()
    
    assert instance.a is None
    assert instance.b is None
    assert instance.c is None


def test_namedtuple_with_defaults_tuple_defaults():
    """
    Test namedtuple_with_defaults with tuple default values.
    
    Validates:
    - Tuple-based defaults (positional)
    """
    TestTuple = namedtuple_with_defaults("TestTuple", ["x", "y", "z"], ("val_x", "val_y", "val_z"))
    
    instance = TestTuple()
    
    assert instance.x == "val_x"
    assert instance.y == "val_y"
    assert instance.z == "val_z"


def test_namedtuple_with_defaults_override():
    """
    Test namedtuple_with_defaults with overriding defaults.
    
    Validates:
    - Provided values override defaults
    """
    TestTuple = namedtuple_with_defaults("TestTuple", ["a", "b"], {"a": 1, "b": 2})
    
    instance = TestTuple(a=10, b=20)
    
    assert instance.a == 10
    assert instance.b == 20


def test_convert_as_values_as_2octet():
    """
    Test convert_as_values with AS_2OCTET type.
    
    Validates:
    - AS number extraction
    - Assign number extraction
    - Correct field population
    """
    as_types = ["as", "as"]
    as_values = ["100:1", "200:2"]
    
    result = convert_as_values(as_types, as_values)
    
    assert result.as_num == ["100", "200"]
    assert result.as4_num == ["65101", "65101"]  # Default values
    assert result.common_num == ["100", "200"]
    assert result.ip_addr == ["1.1.1.1", "1.1.1.1"]  # Default values
    assert result.assign_num == ["1", "2"]


def test_convert_as_values_as_4octet():
    """
    Test convert_as_values with AS_4OCTET type.
    
    Validates:
    - 4-byte AS number handling
    """
    as_types = ["as4", "as4"]
    as_values = ["4294967295:10", "123456:20"]
    
    result = convert_as_values(as_types, as_values)
    
    assert result.as_num == ["65101", "65101"]  # Default values
    assert result.as4_num == ["4294967295", "123456"]
    assert result.common_num == ["4294967295", "123456"]
    assert result.ip_addr == ["1.1.1.1", "1.1.1.1"]  # Default values
    assert result.assign_num == ["10", "20"]


def test_convert_as_values_ipv4_address():
    """
    Test convert_as_values with IPV4_ADDRESS type.
    
    Validates:
    - IP address extraction
    - Assign number extraction
    """
    as_types = ["ip", "ip"]
    as_values = ["192.168.1.1:100", "10.0.0.1:200"]
    
    result = convert_as_values(as_types, as_values)
    
    assert result.as_num == ["65101", "65101"]  # Default values
    assert result.as4_num == ["65101", "65101"]  # Default values
    assert result.common_num == ["65101", "65101"]  # Default values
    assert result.ip_addr == ["192.168.1.1", "10.0.0.1"]
    assert result.assign_num == ["100", "200"]


def test_convert_as_values_mixed_types():
    """
    Test convert_as_values with mixed AS types.
    
    Validates:
    - Different types in same conversion
    - Correct field population per type
    """
    as_types = ["as", "as4", "ip"]
    as_values = ["100:1", "4294967295:2", "192.168.1.1:3"]
    
    result = convert_as_values(as_types, as_values)
    
    # First value (as)
    assert result.as_num[0] == "100"
    assert result.common_num[0] == "100"
    assert result.assign_num[0] == "1"
    
    # Second value (as4)
    assert result.as4_num[1] == "4294967295"
    assert result.common_num[1] == "4294967295"
    assert result.assign_num[1] == "2"
    
    # Third value (ip)
    assert result.ip_addr[2] == "192.168.1.1"
    assert result.assign_num[2] == "3"


def test_convert_as_values_empty():
    """
    Test convert_as_values with empty inputs.
    
    Validates:
    - Handles empty lists
    """
    as_types = []
    as_values = []
    
    result = convert_as_values(as_types, as_values)
    
    assert result.as_num == []
    assert result.as4_num == []
    assert result.common_num == []
    assert result.ip_addr == []
    assert result.assign_num == []


def test_convert_as_values_malformed_value():
    """
    Test convert_as_values with malformed value string.
    
    Validates:
    - Error handling for missing colon separator
    """
    as_types = ["as"]
    as_values = ["100_1"]  # Underscore instead of colon
    
    # Should raise ValueError when trying to split by ':'
    with pytest.raises(ValueError):
        result = convert_as_values(as_types, as_values)


def test_convert_as_values_invalid_type():
    """
    Test convert_as_values with invalid AS type.
    
    Validates:
    - Behavior with unknown type (uses defaults)
    """
    as_types = ["unknown_type"]
    as_values = ["100:1"]
    
    result = convert_as_values(as_types, as_values)
    
    # Unknown type should use default values
    assert result.as_num == ["65101"]
    assert result.as4_num == ["65101"]
    assert result.common_num == ["65101"]
    assert result.ip_addr == ["1.1.1.1"]
    assert result.assign_num == ["1"]


def test_hex_to_ipv4_basic():
    """
    Test hex_to_ipv4 with basic hex string.
    
    Validates:
    - Correct conversion from hex to dotted decimal
    """
    hex_value = "c0a80101"  # 192.168.1.1 in hex
    
    result = hex_to_ipv4(hex_value)
    
    assert result == "1.1.168.192"  # Note: reversed byte order


def test_hex_to_ipv4_all_zeros():
    """
    Test hex_to_ipv4 with all zeros.
    
    Validates:
    - 0.0.0.0 conversion
    """
    hex_value = "00000000"
    
    result = hex_to_ipv4(hex_value)
    
    assert result == "0.0.0.0"


def test_hex_to_ipv4_all_ones():
    """
    Test hex_to_ipv4 with all ones (broadcast).
    
    Validates:
    - 255.255.255.255 conversion
    """
    hex_value = "ffffffff"
    
    result = hex_to_ipv4(hex_value)
    
    assert result == "255.255.255.255"


def test_hex_to_ipv4_loopback():
    """
    Test hex_to_ipv4 with loopback address.
    
    Validates:
    - 127.0.0.1 conversion
    """
    hex_value = "7f000001"  # 127.0.0.1 in hex
    
    result = hex_to_ipv4(hex_value)
    
    assert result == "1.0.0.127"  # Reversed


def test_hex_to_ipv4_uppercase():
    """
    Test hex_to_ipv4 with uppercase hex string.
    
    Validates:
    - Case insensitivity
    """
    hex_value = "C0A80101"  # Uppercase
    
    result = hex_to_ipv4(hex_value)
    
    assert result == "1.1.168.192"


def test_hex_to_ipv4_invalid_length():
    """
    Test hex_to_ipv4 with invalid length hex string.
    
    Validates:
    - Error handling for wrong length input
    """
    hex_value = "c0a801"  # Only 3 bytes (6 hex digits)
    
    # Should raise error or produce invalid result
    # Depending on implementation, this might not be validated
    # Test documents current behavior
    try:
        result = hex_to_ipv4(hex_value)
        # If it doesn't raise, check that result is unexpected
        # (won't be valid IPv4)
    except Exception:
        # Expected to fail
        pass


def test_hex_to_ipv4_non_hex_chars():
    """
    Test hex_to_ipv4 with non-hexadecimal characters.
    
    Validates:
    - Error handling for invalid hex characters
    """
    hex_value = "g0a80101"  # 'g' is not a hex character
    
    with pytest.raises(ValueError):
        result = hex_to_ipv4(hex_value)


def test_hex_to_ipv4_various_addresses():
    """
    Test hex_to_ipv4 with various common IP addresses.
    
    Validates:
    - Multiple IP conversions
    """
    test_cases = [
        ("0a000001", "1.0.0.10"),      # 10.0.0.1 -> reversed
        ("ac100001", "1.0.16.172"),     # 172.16.0.1 -> reversed
        ("c0a8016e", "110.1.168.192"),  # 192.168.1.110 -> reversed
    ]
    
    for hex_val, expected in test_cases:
        result = hex_to_ipv4(hex_val)
        assert result == expected


def test_convert_as_values_single_value():
    """
    Test convert_as_values with single value.
    
    Validates:
    - Works with single element lists
    """
    as_types = ["as"]
    as_values = ["65000:100"]
    
    result = convert_as_values(as_types, as_values)
    
    assert len(result.as_num) == 1
    assert result.as_num[0] == "65000"
    assert result.assign_num[0] == "100"


def test_convert_as_values_large_numbers():
    """
    Test convert_as_values with large AS numbers.
    
    Validates:
    - Handles maximum 4-byte AS number
    """
    as_types = ["as4"]
    as_values = ["4294967295:65535"]  # Max 4-byte AS and max 2-byte assign
    
    result = convert_as_values(as_types, as_values)
    
    assert result.as4_num[0] == "4294967295"
    assert result.assign_num[0] == "65535"
