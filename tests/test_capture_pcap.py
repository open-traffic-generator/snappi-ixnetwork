import pytest


@pytest.mark.skip(
    reason="Fix - intermittent failure as rx ports are not set in capture mode"
)
def test_capture_pcap(serializer, api, tx_port, rx_port, options):
    """Demonstrates how to start capture and get capture results"""
    config = Config(ports=[tx_port, rx_port], options=options)

    # configure capture
    filter = MacAddressFilter(mac="source", filter="000000000000")
    config.captures.append(
        Capture(
            name="rx_capture",
            port_names=[rx_port.name],
            choice=[BasicFilter(filter)],
            enable=True,
        )
    )

    # configure flow
    port_tx_rx = PortTxRx(tx_port_name=tx_port.name, rx_port_name=rx_port.name)
    config.flows.append(
        Flow(
            name="capture",
            tx_rx=TxRx(port_tx_rx),
            packet=[],
            size=Size(128),
            rate=Rate(unit="pps", value=100),
            duration=Duration(FixedPackets(packets=100)),
        )
    )
    api.set_state(State(ConfigState(config=config, state="set")))

    # start capture
    api.set_state(
        State(PortCaptureState(port_names=[rx_port.name], state="start"))
    )

    # start transmit
    api.set_state(State(FlowTransmitState(state="start")))
    time.sleep(5)

    # stop the capture and receive the capture as a stream of bytes
    pcap_bytes = api.get_capture_results(
        CaptureRequest(port_name=rx_port.name)
    )

    # write the pcap bytes to a local file
    with open("%s.pcap" % rx_port.name, "wb") as fid:
        fid.write(pcap_bytes)

    # do stuff using scapy and the pcap file
    from scapy.all import PcapReader

    reader = PcapReader("%s.pcap" % rx_port.name)
    for item in reader:
        print(item.time)
        item.show()


if __name__ == "__main__":
    pytest.main(["-s", __file__])
