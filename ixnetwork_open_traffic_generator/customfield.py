class CustomField(object):
    """
    Implemented All custom field which specify within TrafficItem class
    Best Practice :
        - Please use self._configure_pattern to setting Pattern
    """
    _IPv4_DSCP_PHB = {
        '0': 'ipv4.header.priority.ds.phb.defaultPHB.defaultPHB',
        '8': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '16': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '24': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '32': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '40': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '48': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '56': 'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB',
        '10': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '12': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '14': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '18': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '20': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '22': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '26': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '28': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '30': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '24': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '36': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '38': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB',
        '46': 'ipv4.header.priority.ds.phb.expeditedForwardingPHB.expeditedForwardingPHB'
    }
    _IPv4_DSCP_ECN = {
        'ipv4.header.priority.ds.phb.defaultPHB.defaultPHB': 'ipv4.header.priority.ds.phb.defaultPHB.unused',
        'ipv4.header.priority.ds.phb.classSelectorPHB.classSelectorPHB': 'ipv4.header.priority.ds.phb.classSelectorPHB.unused',
        'ipv4.header.priority.ds.phb.assuredForwardingPHB.assuredForwardingPHB': 'ipv4.header.priority.ds.phb.assuredForwardingPHB.unused',
        'ipv4.header.priority.ds.phb.expeditedForwardingPHB.expeditedForwardingPHB': 'ipv4.header.priority.ds.phb.expeditedForwardingPHB.unused'
    }

    _ETHERNETPAUSE = {
        'dst': 'ethernet.header.destinationAddress',
        'src': 'ethernet.header.sourceAddress',
        'ether_type': 'ethernet.header.etherType',
        'control_op_code': 'custom.header.length',
        'time': 'custom.header.data',
    }

    def _ipv4_priority(self, ixn_field, priority):
        if priority.choice == 'dscp':
            field_type_id = None
            if priority.dscp.phb.choice == 'fixed':
                field_type_id = CustomField._IPv4_DSCP_PHB[priority.dscp.phb.fixed]
            elif priority.dscp.phb.choice == 'list':
                field_type_id = CustomField._IPv4_DSCP_PHB[priority.dscp.phb.list[0]]
            elif priority.dscp.phb.choice == 'counter':
                field_type_id = CustomField._IPv4_DSCP_PHB[priority.dscp.phb.counter.start]
            elif priority.dscp.phb.choice == 'counter':
                field_type_id = CustomField._IPv4_DSCP_PHB[priority.dscp.phb.random.min]
            if field_type_id is not None:
                self._configure_pattern(ixn_field, field_type_id, priority.dscp.phb, field_choice=True)
                field_type_id = CustomField._IPv4_DSCP_ECN[field_type_id]
                self._configure_pattern(ixn_field, field_type_id, priority.dscp.ecn, field_choice=True)

    def _ethernet_pause(self, ixn_field, ethernet_pause):
        pass
    