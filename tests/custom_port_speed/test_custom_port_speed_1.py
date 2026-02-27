import pytest

@pytest.mark.skip("these port speeds might not be available on all load modules in ci")
def test_custom_port_speed_1(api, utils):
    config = api.config()
    # port location is chassis-ip;card-id;port-id
    tx, rx = (
        config.ports.port(
            name="Port 1", location=utils.settings.ports[0]
        ).port(name="Port 2", location=utils.settings.ports[1])
    )
    # configure layer 1 properties
    layer, = config.layer1.layer1(name='layer')
    layer.port_names = [tx.name, rx.name]
    layer.speed = layer.CUSTOM_SPEED
    layer.custom_speed = "novusTwoByFiftyGigNonFanOutHighStream"
    layer.media = layer.FIBER
    # configure flow properties
    flw, = config.flows.flow(name='flw')
    # flow endpoints
    flw.tx_rx.port.tx_name = tx.name
    flw.tx_rx.port.rx_name = rx.name
    # enable flow metrics
    flw.metrics.enable = True
    # configure rate, size, frame count
    flw.size.fixed = 128
    flw.rate.pps = 1000
    flw.duration.fixed_packets.packets = 10000
    # configure protocol headers with defaults fields
    flw.packet.ethernet().vlan().ipv4().tcp()
    # push configuration
    api.set_config(config)
    
    # Verify that the port speed mode has been changed correctly
    # Parse the port location to get card information
    tx_location = utils.settings.ports[0]
    location_info = api.parse_location_info(tx_location)
    card_id = int(location_info.card_info)
    
    # Fetch current chassis configuration
    chassis = api._ixnetwork.AvailableHardware.Chassis.find()
    
    # Find the card with the specified card_id
    cards = chassis.Card.find()
    target_card = None
    for card in cards:
        if card.CardId == card_id:
            target_card = card
            break
    
    if target_card is None:
        raise Exception(f"Card {card_id} not found in chassis")
    
    # Get the current aggregation mode
    aggregation = target_card.Aggregation.find()
    current_mode = aggregation.Mode
    
    # Verify the mode matches the custom_speed configured
    expected_mode = layer.custom_speed
    assert expected_mode.lower() in current_mode.lower(), \
        f"Expected mode to contain '{expected_mode}' but got '{current_mode}'"
    
    print(f"Port speed mode successfully changed to: {current_mode}")
    
