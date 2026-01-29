"""
Unit tests for snappi_api.py core functionality
Tests use the api fixture from conftest which connects to settings.json configuration
"""
import pytest
import snappi
import logging
import utils as utl
from snappi_ixnetwork.exceptions import SnappiIxnException


class TestApiInitialization:
    """Test API initialization and configuration"""

    def test_api_default_initialization(self):
        """Test API initialization with default parameters"""
        api = snappi.api(location=utl.settings.location, ext=utl.settings.ext)
        
        assert api._address is not None
        assert api._port is not None
        assert api._username == "admin"
        assert api._password == "admin"

    def test_api_custom_credentials(self):
        """Test API initialization with custom credentials"""
        api = snappi.api(
            location=utl.settings.location,
            ext=utl.settings.ext,
            username="testuser",
            password="testpass"
        )
        
        assert api._username == "testuser"
        assert api._password == "testpass"

    def test_api_with_loglevel(self):
        """Test API initialization with custom log level"""
        api = snappi.api(
            location=utl.settings.location,
            ext=utl.settings.ext,
            loglevel=logging.DEBUG
        )
        
        assert api.log_level == logging.DEBUG


    def test_api_properties_after_init(self):
        """Test that API properties are properly initialized"""
        api = snappi.api(location=utl.settings.location, ext=utl.settings.ext)
        
        assert hasattr(api, 'vport')
        assert hasattr(api, 'lag')
        assert hasattr(api, 'ngpf')
        assert hasattr(api, 'traffic_item')
        assert hasattr(api, 'capture')
        assert hasattr(api, 'ping')
        assert hasattr(api, 'protocol_metrics')
        assert hasattr(api, 'validation')


class TestApiLocationParsing:
    """Test location parsing utilities"""

    def test_parse_location_semicolon_format(self, api):
        """Test parsing location with semicolon separator"""
        location = "10.36.74.26;2;13"
        result = api.parse_location_info(location)
        
        assert result.chassis_info == "10.36.74.26"
        assert result.card_info == "2"
        assert result.port_info == "13"


    def test_parse_location_localhost(self, api):
        """Test parsing localhost location format"""
        location = "localhost;1;1"
        result = api.parse_location_info(location)
        
        assert result.chassis_info == "localhost"
        assert result.card_info == "1"
        assert result.port_info == "1"

    def test_get_addr_port_https_with_port(self, api):
        """Test address/port extraction from HTTPS URL with port"""
        addr, port = api._get_addr_port("https://192.168.1.100:443")
        
        assert addr == "192.168.1.100"
        assert port == "443"

    def test_get_addr_port_https_default(self, api):
        """Test address/port extraction from HTTPS URL without port"""
        addr, port = api._get_addr_port("https://192.168.1.100")
        
        assert addr == "192.168.1.100"
        assert port == "443"

    def test_get_addr_port_http_with_port(self, api):
        """Test address/port extraction from HTTP URL with port"""
        addr, port = api._get_addr_port("http://192.168.1.100:80")
        
        assert addr == "192.168.1.100"
        assert port == "80"

    def test_get_addr_port_http_default(self, api):
        """Test address/port extraction from HTTP URL without port"""
        addr, port = api._get_addr_port("http://192.168.1.100")
        
        assert addr == "192.168.1.100"
        assert port == "80"


class TestApiSpecialCharHandling:
    """Test special character escaping for regex patterns"""

    def test_special_char_single_string(self, api):
        """Test escaping special characters in a single string"""
        result = api.special_char("flow.test")
        
        assert isinstance(result, str)
        assert result == "flow\\.test"

    def test_special_char_list_of_strings(self, api):
        """Test escaping special characters in list of strings"""
        names = ["flow.1", "flow[2]", "flow(3)", "flow*"]
        result = api.special_char(names)
        
        assert isinstance(result, list)
        assert len(result) == 4
        assert result[0] == "flow\\.1"
        assert result[1] == "flow\\[2\\]"
        assert result[2] == "flow\\(3\\)"
        assert result[3] == "flow\\*"

    def test_special_char_with_none(self, api):
        """Test handling None values in list"""
        names = [None, "test.flow", None]
        result = api.special_char(names)
        
        assert len(result) == 3
        assert result[0] is None
        assert result[1] == "test\\.flow"
        assert result[2] is None

    def test_special_char_all_special_chars(self, api):
        """Test escaping all supported special characters"""
        name = "test.()[]*+?{}"
        result = api.special_char(name)
        
        assert result == "test\\.\\(\\)\\[\\]\\*\\+\\?\\{\\}"


class TestApiConfigurationManagement:
    """Test configuration object management"""

    def test_get_config_returns_config_type(self, api):
        """Test get_config returns proper config object"""
        config = api.get_config()
        
        # Initially should be None or empty
        assert config is None or hasattr(config, '_properties')

    def test_snappi_config_property(self, api):
        """Test snappi_config property accessor"""
        result = api.snappi_config
        
        # Should match get_config
        assert result == api.get_config()

    def test_set_config_object_and_retrieve(self, api):
        """Test storing and retrieving config objects"""
        # This would normally be set during config processing
        test_obj = {"name": "test_flow", "type": "flow"}
        api._config_objects["test_flow"] = test_obj
        
        result = api.get_config_object("test_flow")
        assert result == test_obj

    def test_get_config_object_missing_raises_error(self, api):
        """Test retrieving non-existent config object raises NameError"""
        with pytest.raises(NameError, match="snappi object named .* not found"):
            api.get_config_object("non_existent_object")


class TestApiDeviceManagement:
    """Test device-related management functions"""

    def test_set_and_get_device_encap(self, api):
        """Test setting and getting device encapsulation"""
        api.set_device_encap("device1", "ipv4")
        result = api.get_device_encap("device1")
        
        assert result == "ipv4"

    def test_set_and_get_device_encap_ipv6(self, api):
        """Test setting IPv6 encapsulation"""
        api.set_device_encap("device2", "ipv6")
        result = api.get_device_encap("device2")
        
        assert result == "ipv6"

    def test_get_device_encap_missing_raises_error(self, api):
        """Test getting non-existent device encap raises NameError"""
        with pytest.raises(NameError, match="snappi object named .* not found"):
            api.get_device_encap("non_existent_device")

    def test_set_and_get_device_traffic_endpoint(self, api):
        """Test setting and getting device traffic endpoint"""
        api.set_device_traffic_endpoint("device1", "endpoint1")
        result = api.get_device_traffic_endpoint("device1")
        
        assert result == "endpoint1"

    def test_get_device_traffic_endpoint_missing_returns_none(self, api):
        """Test getting non-existent traffic endpoint returns None"""
        result = api.get_device_traffic_endpoint("non_existent")
        
        assert result is None


class TestApiScalingAndCompaction:
    """Test scaling and compaction features"""

    def test_enable_scaling_default(self, api):
        """Test enable_scaling with default parameter"""
        api.enable_scaling()
        
        assert api.do_compact is False

    def test_enable_scaling_with_compaction(self, api):
        """Test enable_scaling with compaction enabled"""
        api.enable_scaling(do_compact=True)
        
        assert api.do_compact is True

    def test_set_dev_compacted(self, api):
        """Test setting compacted device information"""
        name_list = ["dev1", "dev2", "dev3"]
        api.set_dev_compacted("parent_device", name_list)
        
        compacted = api.dev_compacted
        assert "dev1" in compacted
        assert compacted["dev1"]["dev_name"] == "parent_device"
        assert compacted["dev1"]["index"] == 0
        assert compacted["dev2"]["index"] == 1
        assert compacted["dev3"]["index"] == 2

    def test_dev_compacted_property(self, api):
        """Test dev_compacted property returns dict"""
        result = api.dev_compacted
        
        assert isinstance(result, dict)

    def test_enable_flow_tracking_default(self, api):
        """Test flow tracking disabled by default"""
        api._enable_flow_tracking()
        
        assert api._flow_tracking is False

    def test_enable_flow_tracking_enabled(self, api):
        """Test enabling flow tracking"""
        api._enable_flow_tracking(_flow_tracking=True)
        
        assert api._flow_tracking is True

    def test_enable_port_compaction_default(self, api):
        """Test port compaction disabled by default"""
        api._enable_port_compaction()
        
        assert api._port_compaction is False

    def test_enable_port_compaction_enabled(self, api):
        """Test enabling port compaction"""
        api._enable_port_compaction(_port_compaction=True)
        
        assert api._port_compaction is True


class TestApiErrorHandling:
    """Test error handling and reporting"""

    def test_add_error_string(self, api):
        """Test adding string error"""
        api._errors = []  # Reset errors
        api.add_error("Test error message")
        
        errors = api.get_errors()
        assert "Test error message" in errors

    def test_add_error_non_string(self, api):
        """Test adding non-string error converts to string"""
        api._errors = []
        api.add_error(12345)
        
        errors = api.get_errors()
        assert "<class 'int'> 12345" in errors

    def test_get_errors_returns_list(self, api):
        """Test get_errors returns a list"""
        result = api.get_errors()
        
        assert isinstance(result, list)

    def test_multiple_errors(self, api):
        """Test adding multiple errors"""
        api._errors = []
        api.add_error("Error 1")
        api.add_error("Error 2")
        api.add_error("Error 3")
        
        errors = api.get_errors()
        assert len(errors) >= 3
        assert "Error 1" in errors
        assert "Error 2" in errors
        assert "Error 3" in errors


class TestApiPropertyAccessors:
    """Test property getters and setters"""

    def test_username_getter(self, api):
        """Test username property getter"""
        result = api.username
        
        assert isinstance(result, str)

    def test_username_setter(self, api):
        """Test username property setter"""
        original = api.username
        api.username = "new_username"
        
        assert api.username == "new_username"
        # Restore original
        api.username = original

    def test_password_getter(self, api):
        """Test password property getter"""
        result = api.password
        
        assert isinstance(result, str)

    def test_password_setter(self, api):
        """Test password property setter"""
        original = api.password
        api.password = "new_password"
        
        assert api.password == "new_password"
        # Restore original
        api.password = original

    def test_log_level_property(self, api):
        """Test log_level property"""
        result = api.log_level
        
        assert isinstance(result, int)

    def test_assistant_property(self, api):
        """Test assistant property (may be None before connection)"""
        result = api.assistant
        
        # Can be None if not connected
        assert result is None or hasattr(result, 'Session')


class TestApiHelperMethods:
    """Test helper and utility methods"""

    def test_dict_to_obj_simple_dict(self, api):
        """Test converting simple dict to object"""
        source = {"name": "test", "value": 123}
        result = api._dict_to_obj(source)
        
        assert hasattr(result, "name")
        assert result.name == "test"
        assert hasattr(result, "value")
        assert result.value == 123

    def test_dict_to_obj_nested_dict(self, api):
        """Test converting nested dict to object"""
        source = {
            "outer": "value1",
            "nested": {
                "inner1": "value2",
                "inner2": 456
            }
        }
        result = api._dict_to_obj(source)
        
        assert hasattr(result, "outer")
        assert result.outer == "value1"
        assert hasattr(result, "nested")
        assert hasattr(result.nested, "inner1")
        assert result.nested.inner1 == "value2"
        assert result.nested.inner2 == 456

    def test_dict_to_obj_list_of_dicts(self, api):
        """Test converting list of dicts to list of objects"""
        source = [
            {"name": "item1", "id": 1},
            {"name": "item2", "id": 2}
        ]
        result = api._dict_to_obj(source)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert hasattr(result[0], "name")
        assert result[0].name == "item1"
        assert result[1].id == 2

    def test_dict_to_obj_non_dict_passthrough(self, api):
        """Test that non-dict values pass through unchanged"""
        assert api._dict_to_obj("string") == "string"
        assert api._dict_to_obj(123) == 123
        assert api._dict_to_obj(45.67) == 45.67
        assert api._dict_to_obj(True) is True
        assert api._dict_to_obj(None) is None


class TestApiConvergenceConstants:
    """Test convergence-related constants and configuration"""

    def test_convergence_constants_exist(self, api):
        """Test that convergence constants are defined"""
        assert hasattr(api, "_CONVERGENCE")
        assert hasattr(api, "_DP_CONVERGENCE")
        assert hasattr(api, "_EVENT")

    def test_convergence_constant_format(self, api):
        """Test convergence constant is a set of tuples"""
        assert isinstance(api._CONVERGENCE, set)
        assert len(api._CONVERGENCE) == 2
        
        # Each item should be a tuple
        for item in api._CONVERGENCE:
            assert isinstance(item, tuple)
            assert len(item) == 3

    def test_dp_convergence_constant(self, api):
        """Test DP convergence constant structure"""
        assert isinstance(api._DP_CONVERGENCE, set)
        assert len(api._DP_CONVERGENCE) == 1
        
        item = list(api._DP_CONVERGENCE)[0]
        assert item[0] == "data_plane_convergence_us"
        assert item[1] == "DP/DP Convergence Time (us)"
        assert item[2] == float

    def test_event_constant(self, api):
        """Test event constant structure"""
        assert isinstance(api._EVENT, set)
        assert len(api._EVENT) == 2
        
        # Should contain timestamp fields
        field_names = [item[0] for item in api._EVENT]
        assert "begin_timestamp_ns" in field_names
        assert "end_timestamp_ns" in field_names


class TestApiConfigCreation:
    """Test config object creation"""

    def test_create_empty_config(self, api):
        """Test creating an empty configuration"""
        config = api.config()
        
        assert config is not None
        assert hasattr(config, 'ports')
        assert hasattr(config, 'devices')
        assert hasattr(config, 'flows')

    def test_config_with_ports(self, api):
        """Test creating config with port definitions"""
        config = api.config()
        port = config.ports.port(name="port1", location=utl.settings.ports[0])
        
        assert len(config.ports) == 1
        assert config.ports[0].name == "port1"
        assert config.ports[0].location == utl.settings.ports[0]

    def test_config_with_multiple_ports(self, api):
        """Test creating config with multiple ports"""
        config = api.config()
        config.ports.port(name="port1", location=utl.settings.ports[0])
        config.ports.port(name="port2", location=utl.settings.ports[1])
        
        assert len(config.ports) == 2
        assert config.ports[0].name == "port1"
        assert config.ports[1].name == "port2"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
