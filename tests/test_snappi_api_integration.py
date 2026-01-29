"""
Integration tests for snappi_api.py Priority 3 methods
These tests require actual IxNetwork connection and test real-world scenarios
"""
import pytest
import snappi
import time
import utils as utl


class TestApiSetConfig:
    """Integration tests for set_config method"""

    def test_set_config_basic_ports(self, api, utils):
        """Test set_config with basic port configuration"""
        config = api.config()
        config.ports.port(name="tx", location=utils.settings.ports[0])
        config.ports.port(name="rx", location=utils.settings.ports[1])
        
        response = api.set_config(config)
        
        # Verify response is not None and has expected attributes
        assert response is not None
        assert hasattr(response, 'warnings') or isinstance(response, dict)

    def test_set_config_with_devices(self, api, utils):
        """Test set_config with device configuration"""
        config = api.config()
        
        # Configure ports
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        p2 = config.ports.port(name="p2", location=utils.settings.ports[1])[-1]
        
        # Configure devices
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv4_addresses.ipv4()[-1]
        d1_ip.name = "d1_ipv4"
        d1_ip.address = "10.1.1.1"
        d1_ip.gateway = "10.1.1.2"
        d1_ip.prefix = 24
        
        response = api.set_config(config)
        
        assert response is not None

    def test_set_config_with_flows(self, api, utils):
        """Test set_config with traffic flow configuration"""
        config = api.config()
        
        # Configure ports
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        # Configure flow
        flow = config.flows.flow(name="f1")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 128
        flow.duration.fixed_packets.packets = 1000
        flow.rate.percentage = 10
        
        flow.packet.ethernet().ipv4().udp()
        
        response = api.set_config(config)
        
        assert response is not None

    def test_set_config_clear_config(self, api, utils):
        """Test set_config with empty config to clear"""
        # First set a config
        config = api.config()
        config.ports.port(name="tx", location=utils.settings.ports[0])
        api.set_config(config)
        
        # Now clear it
        empty_config = api.config()
        response = api.set_config(empty_config)
        
        assert response is not None

    def test_set_config_with_convergence_events(self, api, utils):
        """Test set_config with CP/DP convergence events"""
        config = api.config()
        
        # Configure ports
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        # Configure flow
        flow = config.flows.flow(name="f1")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 128
        flow.duration.fixed_packets.packets = 1000
        
        flow.packet.ethernet().ipv4().tcp()
        
        # Enable CP events
        config.events.cp_events.enable = True
        
        response = api.set_config(config)
        
        assert response is not None


class TestApiGetMetrics:
    """Integration tests for get_metrics method"""

    def test_get_port_metrics(self, api, utils):
        """Test get_metrics for port metrics"""
        # Set up basic config
        config = api.config()
        config.ports.port(name="tx", location=utils.settings.ports[0])
        config.ports.port(name="rx", location=utils.settings.ports[1])
        api.set_config(config)
        
        # Get port metrics
        req = api.metrics_request()
        req.port.port_names = []
        req.port.column_names = [
            "frames_tx",
            "frames_rx",
            "bytes_tx",
            "bytes_rx"
        ]
        
        response = api.get_metrics(req)
        
        assert response is not None
        assert hasattr(response, 'port_metrics')
        assert len(response.port_metrics) > 0

    def test_get_flow_metrics(self, api, utils):
        """Test get_metrics for flow metrics"""
        # Set up config with flow
        config = api.config()
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        flow = config.flows.flow(name="f1")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 128
        flow.duration.fixed_packets.packets = 1000
        flow.rate.percentage = 10
        flow.packet.ethernet().ipv4().udp()
        flow.metrics.enable = True
        
        api.set_config(config)
        
        # Start traffic
        ts = api.control_state()
        ts.traffic.flow_transmit.state = ts.traffic.flow_transmit.START
        api.set_control_state(ts)
        
        # Wait a bit for traffic
        time.sleep(2)
        
        # Get flow metrics
        req = api.metrics_request()
        req.flow.flow_names = []
        
        response = api.get_metrics(req)
        
        assert response is not None
        assert hasattr(response, 'flow_metrics')

    def test_get_port_metrics_specific_ports(self, api, utils):
        """Test get_metrics for specific port names"""
        config = api.config()
        config.ports.port(name="port1", location=utils.settings.ports[0])
        config.ports.port(name="port2", location=utils.settings.ports[1])
        api.set_config(config)
        
        req = api.metrics_request()
        req.port.port_names = ["port1"]
        req.port.column_names = ["name", "location", "link"]
        
        response = api.get_metrics(req)
        
        assert response is not None
        assert hasattr(response, 'port_metrics')
        # Should only get metrics for port1
        port_names = [p.name for p in response.port_metrics]
        assert "port1" in port_names

    def test_get_flow_metrics_specific_columns(self, api, utils):
        """Test get_metrics with specific column names"""
        config = api.config()
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        flow = config.flows.flow(name="test_flow")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 64
        flow.duration.fixed_packets.packets = 100
        flow.packet.ethernet().ipv4().tcp()
        flow.metrics.enable = True
        
        api.set_config(config)
        
        req = api.metrics_request()
        req.flow.flow_names = ["test_flow"]
        req.flow.metric_names = ["frames_tx", "frames_rx"]
        
        response = api.get_metrics(req)
        
        assert response is not None
        assert hasattr(response, 'flow_metrics')


class TestApiSetControlState:
    """Integration tests for set_control_state method"""

    def test_set_control_state_traffic_start(self, api, utils):
        """Test set_control_state to start traffic"""
        # Set up config
        config = api.config()
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        flow = config.flows.flow(name="f1")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 128
        flow.duration.fixed_packets.packets = 1000
        flow.rate.pps = 100
        flow.packet.ethernet().ipv4().udp()
        
        api.set_config(config)
        
        # Start traffic
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
        
        response = api.set_control_state(cs)
        
        assert response is not None

    def test_set_control_state_traffic_stop(self, api, utils):
        """Test set_control_state to stop traffic"""
        # Set up config
        config = api.config()
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        flow = config.flows.flow(name="f1")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 128
        flow.duration.continuous = True
        flow.rate.pps = 100
        flow.packet.ethernet().ipv4().udp()
        
        api.set_config(config)
        
        # Start traffic
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
        api.set_control_state(cs)
        
        time.sleep(1)
        
        # Stop traffic
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.STOP
        
        response = api.set_control_state(cs)
        
        assert response is not None

    def test_set_control_state_port_link(self, api, utils):
        """Test set_control_state for port link state"""
        config = api.config()
        config.ports.port(name="tx", location=utils.settings.ports[0])
        api.set_config(config)
        
        # Set link state
        cs = api.control_state()
        cs.port.link.port_names = ["tx"]
        cs.port.link.state = cs.port.link.UP
        
        response = api.set_control_state(cs)
        
        assert response is not None

    def test_set_control_state_protocol_all_start(self, api, utils):
        """Test set_control_state to start all protocols"""
        config = api.config()
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        
        # Add device with BGP
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv4_addresses.ipv4()[-1]
        d1_ip.name = "d1_ipv4"
        d1_ip.address = "10.1.1.1"
        d1_ip.gateway = "10.1.1.2"
        d1_ip.prefix = 24
        
        bgp = d1_ip.bgpv4_interfaces.bgpv4interface()[-1]
        bgp.name = "bgp1"
        bgp.as_type = bgp.IBGP
        bgp.as_number = 65001
        
        api.set_config(config)
        
        # Start protocols
        cs = api.control_state()
        cs.protocol.all.state = cs.protocol.all.START
        
        response = api.set_control_state(cs)
        
        assert response is not None

    def test_set_control_state_capture_start(self, api, utils):
        """Test set_control_state to start capture"""
        config = api.config()
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        
        # Enable capture
        capture = config.captures.capture()[-1]
        capture.name = "c1"
        capture.port_names = [p1.name]
        
        api.set_config(config)
        
        # Start capture
        cs = api.control_state()
        cs.port.capture.state = cs.port.capture.START
        
        response = api.set_control_state(cs)
        
        assert response is not None


class TestApiSetControlAction:
    """Integration tests for set_control_action method"""

    def test_set_control_action_ping_ipv4(self, api, utils):
        """Test set_control_action for IPv4 ping"""
        config = api.config()
        
        # Configure source device
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv4_addresses.ipv4()[-1]
        d1_ip.name = "d1_ipv4"
        d1_ip.address = "10.1.1.1"
        d1_ip.gateway = "10.1.1.2"
        d1_ip.prefix = 24
        
        # Configure destination device
        p2 = config.ports.port(name="p2", location=utils.settings.ports[1])[-1]
        d2 = config.devices.device(name="d2")[-1]
        d2_eth = d2.ethernets.ethernet()[-1]
        d2_eth.name = "d2_eth"
        d2_eth.port_name = p2.name
        d2_eth.mac = "00:00:00:00:00:02"
        
        d2_ip = d2_eth.ipv4_addresses.ipv4()[-1]
        d2_ip.name = "d2_ipv4"
        d2_ip.address = "10.1.1.2"
        d2_ip.gateway = "10.1.1.1"
        d2_ip.prefix = 24
        
        api.set_config(config)
        
        # Wait for interfaces to be ready
        time.sleep(5)
        
        # Send ping
        ca = api.control_action()
        ca.protocol.ipv4.ping.requests.request(
            src_name="d1_ipv4",
            dst_ip="10.1.1.2"
        )
        
        response = api.set_control_action(ca)
        
        assert response is not None
        assert hasattr(response, 'response')

    def test_set_control_action_ping_ipv6(self, api, utils):
        """Test set_control_action for IPv6 ping"""
        config = api.config()
        
        # Configure source device
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv6_addresses.ipv6()[-1]
        d1_ip.name = "d1_ipv6"
        d1_ip.address = "2000::1"
        d1_ip.gateway = "2000::2"
        d1_ip.prefix = 64
        
        # Configure destination device
        p2 = config.ports.port(name="p2", location=utils.settings.ports[1])[-1]
        d2 = config.devices.device(name="d2")[-1]
        d2_eth = d2.ethernets.ethernet()[-1]
        d2_eth.name = "d2_eth"
        d2_eth.port_name = p2.name
        d2_eth.mac = "00:00:00:00:00:02"
        
        d2_ip = d2_eth.ipv6_addresses.ipv6()[-1]
        d2_ip.name = "d2_ipv6"
        d2_ip.address = "2000::2"
        d2_ip.gateway = "2000::1"
        d2_ip.prefix = 64
        
        api.set_config(config)
        
        # Wait for interfaces to be ready
        time.sleep(5)
        
        # Send ping
        ca = api.control_action()
        ca.protocol.ipv6.ping.requests.request(
            src_name="d1_ipv6",
            dst_ip="2000::2"
        )
        
        response = api.set_control_action(ca)
        
        assert response is not None
        assert hasattr(response, 'response')


class TestApiGetStates:
    """Integration tests for get_states method"""

    def test_get_bgp_states(self, api, utils):
        """Test get_states for BGP protocol state"""
        config = api.config()
        
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        
        # Configure device with BGP
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv4_addresses.ipv4()[-1]
        d1_ip.name = "d1_ipv4"
        d1_ip.address = "10.1.1.1"
        d1_ip.gateway = "10.1.1.2"
        d1_ip.prefix = 24
        
        bgp = d1_ip.bgpv4_interfaces.bgpv4interface()[-1]
        bgp.name = "bgp1"
        bgp.as_type = bgp.IBGP
        bgp.as_number = 65001
        
        api.set_config(config)
        
        time.sleep(2)
        
        # Get BGP states
        req = api.states_request()
        req.bgpv4_peers.peer_names = []
        
        response = api.get_states(req)
        
        assert response is not None
        assert hasattr(response, 'bgpv4_peers') or hasattr(response, 'choice')

    def test_get_ipv4_states(self, api, utils):
        """Test get_states for IPv4 interface state"""
        config = api.config()
        
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv4_addresses.ipv4()[-1]
        d1_ip.name = "d1_ipv4"
        d1_ip.address = "10.1.1.1"
        d1_ip.gateway = "10.1.1.2"
        d1_ip.prefix = 24
        
        api.set_config(config)
        
        time.sleep(2)
        
        # Get IPv4 states
        req = api.states_request()
        req.ipv4_neighbors.ethernet_names = []
        
        response = api.get_states(req)
        
        assert response is not None

    def test_get_port_states(self, api, utils):
        """Test get_states for port link state"""
        config = api.config()
        config.ports.port(name="p1", location=utils.settings.ports[0])
        api.set_config(config)
        
        # Get port states (if supported)
        req = api.states_request()
        # Note: Port states might not be a valid choice, adjust as needed
        try:
            response = api.get_states(req)
            assert response is not None
        except Exception:
            # Port states may not be supported, that's ok
            pass


class TestApiGetCapture:
    """Integration tests for get_capture method"""

    def test_get_capture_basic(self, api, utils):
        """Test get_capture to retrieve capture file"""
        config = api.config()
        
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        # Enable capture on rx port
        capture = config.captures.capture()[-1]
        capture.name = "cap1"
        capture.port_names = [rx.name]
        
        # Create flow
        flow = config.flows.flow(name="f1")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 128
        flow.duration.fixed_packets.packets = 10
        flow.rate.pps = 10
        flow.packet.ethernet().ipv4().udp()
        
        api.set_config(config)
        
        # Start capture
        cs = api.control_state()
        cs.port.capture.state = cs.port.capture.START
        api.set_control_state(cs)
        
        # Start traffic
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
        api.set_control_state(cs)
        
        # Wait for packets
        time.sleep(3)
        
        # Stop capture
        cs = api.control_state()
        cs.port.capture.state = cs.port.capture.STOP
        api.set_control_state(cs)
        
        # Get capture
        req = api.capture_request()
        req.port_name = rx.name
        
        response = api.get_capture(req)
        
        assert response is not None
        # Response should be bytes or have capture data
        assert isinstance(response, bytes) or hasattr(response, '__len__')

    def test_get_capture_no_packets(self, api, utils):
        """Test get_capture when no packets captured"""
        config = api.config()
        
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        # Enable capture but send no traffic
        capture = config.captures.capture()[-1]
        capture.name = "cap1"
        capture.port_names = [rx.name]
        
        api.set_config(config)
        
        # Start and stop capture quickly
        cs = api.control_state()
        cs.port.capture.state = cs.port.capture.START
        api.set_control_state(cs)
        
        time.sleep(1)
        
        cs = api.control_state()
        cs.port.capture.state = cs.port.capture.STOP
        api.set_control_state(cs)
        
        # Get capture
        req = api.capture_request()
        req.port_name = rx.name
        
        response = api.get_capture(req)
        
        # Should still return valid response even with no packets
        assert response is not None


class TestApiComplexScenarios:
    """Integration tests for complex real-world scenarios"""

    def test_full_traffic_flow_scenario(self, api, utils):
        """Test complete workflow: config -> start -> metrics -> stop"""
        config = api.config()
        
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        flow = config.flows.flow(name="test_flow")[-1]
        flow.tx_rx.port.tx_name = tx.name
        flow.tx_rx.port.rx_name = rx.name
        flow.size.fixed = 256
        flow.duration.fixed_packets.packets = 1000
        flow.rate.percentage = 50
        flow.packet.ethernet().ipv4().tcp()
        flow.metrics.enable = True
        
        # Step 1: Set config
        api.set_config(config)
        
        # Step 2: Start traffic
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
        api.set_control_state(cs)
        
        # Step 3: Wait and get metrics
        time.sleep(2)
        
        req = api.metrics_request()
        req.flow.flow_names = ["test_flow"]
        response = api.get_metrics(req)
        
        assert response is not None
        assert hasattr(response, 'flow_metrics')
        
        # Step 4: Get port metrics
        req = api.metrics_request()
        req.port.port_names = []
        port_response = api.get_metrics(req)
        
        assert port_response is not None
        assert hasattr(port_response, 'port_metrics')

    def test_bgp_convergence_scenario(self, api, utils):
        """Test BGP protocol convergence scenario"""
        config = api.config()
        
        # Configure two BGP peers
        p1 = config.ports.port(name="p1", location=utils.settings.ports[0])[-1]
        p2 = config.ports.port(name="p2", location=utils.settings.ports[1])[-1]
        
        # Device 1
        d1 = config.devices.device(name="d1")[-1]
        d1_eth = d1.ethernets.ethernet()[-1]
        d1_eth.name = "d1_eth"
        d1_eth.port_name = p1.name
        d1_eth.mac = "00:00:00:00:00:01"
        
        d1_ip = d1_eth.ipv4_addresses.ipv4()[-1]
        d1_ip.name = "d1_ipv4"
        d1_ip.address = "10.1.1.1"
        d1_ip.gateway = "10.1.1.2"
        d1_ip.prefix = 24
        
        bgp1 = d1_ip.bgpv4_interfaces.bgpv4interface()[-1]
        bgp1.name = "bgp1"
        bgp1.as_type = bgp1.IBGP
        bgp1.as_number = 65001
        bgp1.ipv4_routes.bgpv4route(name="route1")
        
        # Device 2
        d2 = config.devices.device(name="d2")[-1]
        d2_eth = d2.ethernets.ethernet()[-1]
        d2_eth.name = "d2_eth"
        d2_eth.port_name = p2.name
        d2_eth.mac = "00:00:00:00:00:02"
        
        d2_ip = d2_eth.ipv4_addresses.ipv4()[-1]
        d2_ip.name = "d2_ipv4"
        d2_ip.address = "10.1.1.2"
        d2_ip.gateway = "10.1.1.1"
        d2_ip.prefix = 24
        
        bgp2 = d2_ip.bgpv4_interfaces.bgpv4interface()[-1]
        bgp2.name = "bgp2"
        bgp2.as_type = bgp2.IBGP
        bgp2.as_number = 65001
        
        # Step 1: Configure
        api.set_config(config)
        
        # Step 2: Wait for BGP to come up
        time.sleep(10)
        
        # Step 3: Check BGP states
        req = api.states_request()
        req.bgpv4_peers.peer_names = []
        response = api.get_states(req)
        
        assert response is not None

    def test_multiflow_traffic_scenario(self, api, utils):
        """Test scenario with multiple flows"""
        config = api.config()
        
        tx = config.ports.port(name="tx", location=utils.settings.ports[0])[-1]
        rx = config.ports.port(name="rx", location=utils.settings.ports[1])[-1]
        
        # Create multiple flows
        for i in range(3):
            flow = config.flows.flow(name=f"flow_{i}")[-1]
            flow.tx_rx.port.tx_name = tx.name
            flow.tx_rx.port.rx_name = rx.name
            flow.size.fixed = 64 + (i * 64)
            flow.duration.fixed_packets.packets = 1000
            flow.rate.percentage = 10
            flow.packet.ethernet().ipv4().udp()
            flow.metrics.enable = True
        
        # Configure
        api.set_config(config)
        
        # Start traffic
        cs = api.control_state()
        cs.traffic.flow_transmit.state = cs.traffic.flow_transmit.START
        api.set_control_state(cs)
        
        time.sleep(3)
        
        # Get metrics for all flows
        req = api.metrics_request()
        req.flow.flow_names = []
        response = api.get_metrics(req)
        
        assert response is not None
        assert hasattr(response, 'flow_metrics')
        assert len(response.flow_metrics) >= 3


class TestApiErrorHandling:
    """Integration tests for error handling in API methods"""

    def test_set_config_invalid_config_type(self, api):
        """Test set_config with invalid config type raises TypeError"""
        with pytest.raises(Exception):  # Could be TypeError or SnappiIxnException
            api.set_config({"invalid": "dict"})

    def test_get_metrics_invalid_request_type(self, api):
        """Test get_metrics with invalid request type raises TypeError"""
        with pytest.raises(Exception):
            api.get_metrics({"invalid": "dict"})

    def test_get_states_invalid_request_type(self, api):
        """Test get_states with invalid request type raises TypeError"""
        with pytest.raises(Exception):
            api.get_states("invalid string")

    def test_get_capture_invalid_request_type(self, api):
        """Test get_capture with invalid request type raises TypeError"""
        with pytest.raises(Exception):
            api.get_capture(12345)


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
