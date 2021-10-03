from collections import defaultdict


class AttDict(defaultdict):
    def __init__(self):
        super(AttDict, self).__init__(list)

    def __setitem__(self, key, value):
        super(AttDict, self).__setitem__(key, value)

class MultiValue(object):
    def __init__(self):
        self.value = None

    def set_value(self, value):
        self.value = value
        return self

    def get_value(self):
        return self.value

class Base(object):
    def __init__(self):
        pass

    def create_node(self, ixn_obj, name):
        """It will check/ create a node with name"""
        if name in ixn_obj:
            return ixn_obj.get(name)
        else:
            ixn_obj[name] = list()
            return ixn_obj[name]

    def add_element(self, ixn_obj, name=None):
        ixn_obj.append(self.att_dict())
        new_element = ixn_obj[-1]
        new_element["xpath"] = ""
        if name is not None:
            new_element["name"] = self.multivalue(name)
        return new_element

    def create_node_elemet(self, ixn_obj, node_name, name=None):
        """Expectation  of this method:
        - check/ create a node with "node_name"
        - We are setting name as multivalue for farther processing
        - It will return that newly created dict
        """
        node = self.create_node(ixn_obj, node_name)
        return self.add_element(node, name)

    def create_property(self, ixn_obj, name):
        ixn_obj[name] = self.att_dict()
        ixn_property = ixn_obj[name]
        ixn_property["xpath"] = ""
        return ixn_property

    def att_dict(self):
        return AttDict()

    def multivalue(self, value, enum=None):
        if value is not None and enum is not None:
            value = enum[value]
        return MultiValue().set_value(value)

    def configure_multivalues(self, snappi_obj, ixn_obj, attr_map):
        """attr_map contains snappi_key : ixn_key/ ixn_info in dict format"""
        for snappi_attr, ixn_map in attr_map.items():
            if isinstance(ixn_map, dict):
                ixn_attr = ixn_map.get("ixn_attr")
                if ixn_attr is None:
                    raise NameError("ixn_attr is missing within ", ixn_map)
                enum_map = ixn_map.get("enum_map")
                value = snappi_obj.get(snappi_attr)
                if enum_map is not None and value is not None:
                    value = enum_map[value]
            else:
                ixn_attr = ixn_map
                value = snappi_obj.get(snappi_attr)
            ixn_obj[ixn_attr] = self.multivalue(value)
