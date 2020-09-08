class CustomField(object):
    """
    Implemented All custom field which specify within TrafficItem class
    Best Practice :
        - Please use self._configure_pattern to setting Pattern
        - Otherwise please handle group_by accordingly
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
            if phb_pattern is not None:
                if phb_pattern.choice == 'fixed':
                    value = phb_pattern.fixed
                elif phb_pattern.choice == 'list':
                    value = phb_pattern.list[0]
                elif phb_pattern.choice == 'counter':
                    value = phb_pattern.counter.start
                else:
                    value = phb_pattern.random.min
                
                if isinstance(value, int) is True:
                    value = str(value)
                if value not in CustomField._IPv4_DSCP_PHB:
                    field_type_id = CustomField._IPv4_DSCP_PHB['0']
                else:
                    field_type_id = CustomField._IPv4_DSCP_PHB[value]
                    
                ixn_dscp_phb = ixn_field.find(FieldTypeId=field_type_id)
                ixn_dscp_phb.update(Auto=False, ActiveFieldChoice=True)
                self._configure_pattern(ixn_field, field_type_id, phb_pattern)
            
            # Use defaultPHB.defaultPHB to configure ECN
            ecn_pattern = pattern.dscp.ecn
            if ecn_pattern is not None:
                field_type_id = CustomField._IPv4_DSCP_PHB['0']
                ixn_dscp_ecn= ixn_field.find(FieldTypeId=field_type_id)
                ixn_dscp_ecn.update(Auto=False, ActiveFieldChoice=True)
                self._configure_pattern(ixn_field, field_type_id, ecn_pattern)