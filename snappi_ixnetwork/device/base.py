__all__ = ['Base', 'MultiValue', 'PostCalculated']



class MultiValue(object):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class PostCalculated(object):
    def __init__(self, key, ref_ixnobj=None, ixnobj=None):
        self._key = key
        self._ref_obj = ref_ixnobj
        self._parent_obj = ixnobj

    @property
    def value(self):
        if self._key == "connectedTo":
            return self._ref_obj.get("xpath")


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
        ixn_obj.append(dict())
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
        ixn_obj[name] = dict()
        ixn_property = ixn_obj[name]
        ixn_property["xpath"] = ""
        return ixn_property

    def att_dict(self):
        return dict()

    def multivalue(self, value, enum=None):
        if value is not None and enum is not None:
            value = enum[value]
        return MultiValue(value)

    def post_calculated(self, key, ref_ixnobj=None, ixnobj=None):
        return PostCalculated(
            key, ref_ixnobj, ixnobj
        )

    def get_name(self, object):
        name = object.get("name")
        if isinstance(name, MultiValue):
            name = name.value
        if isinstance(name, list):
            name = name[0]
        return name

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