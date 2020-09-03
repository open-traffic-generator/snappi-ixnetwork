class CustomField(object):
    """
    Implemented All custom field which specify within TrafficItem class
    """
    
    ##########################      IPv4 stack      ##########################
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
    
    def _ipv4_priority(self, ixn_field, pattern):
        if pattern.choice == 'dscp':
            phb_pattern = pattern.dscp.phb
            value = str()
            if phb_pattern.choice == 'fixed':
                value = phb_pattern.fixed
            elif phb_pattern.choice == 'list':
                value = phb_pattern.list[0]
            elif phb_pattern.choice == 'counter':
                value = phb_pattern.counter.start
            else:
                value = phb_pattern.random.min
            
            field_type_id = CustomField._IPv4_DSCP_PHB[value]
            ixn_field = ixn_field.find(FieldTypeId=field_type_id)
            ixn_field.update(Auto=False, ActiveFieldChoice=True)
            self._configure_pattern(ixn_field, field_type_id, phb_pattern)