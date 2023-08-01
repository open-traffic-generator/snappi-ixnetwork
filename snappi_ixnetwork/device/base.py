from snappi_ixnetwork.logger import get_ixnet_logger

__all__ = ["Base", "MultiValue", "PostCalculated"]


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
        self.logger = get_ixnet_logger(__name__)

    @property
    def value(self):
        value = None
        if self._key == "connectedTo":
            value = self._ref_obj.get("xpath")
        self.logger.debug("Post Calculated %s - %s" % (self._key, value))
        return value


class Base(object):
    def __init__(self):
        self.logger = get_ixnet_logger(__name__)

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
        self.logger.debug("Creating node for %s" % node_name)
        node = self.create_node(ixn_obj, node_name)
        return self.add_element(node, name)

    def create_property(self, ixn_obj, name):
        ixn_property = ixn_obj[name] = dict()
        ixn_property["xpath"] = ""
        return ixn_property

    def att_dict(self):
        return dict()

    def multivalue(self, value, enum=None):
        if value is not None and enum is not None:
            value = enum[value]
        return MultiValue(value)

    def as_multivalue(self, snappi_obj, name, enum=None):
        return self.multivalue(snappi_obj.get(name), enum)

    def post_calculated(self, key, ref_ixnobj=None, ixnobj=None):
        return PostCalculated(key, ref_ixnobj, ixnobj)

    def get_name(self, object):
        name = object.get("name")
        if isinstance(name, MultiValue):
            name = name.value
        if isinstance(name, list):
            name = name[0]
        return name

    def configure_multivalues(self, snappi_obj, ixn_obj, attr_map):
        """attr_map contains snappi_key : ixn_key/ ixn_info in dict format"""
        self.logger.debug("configuring multivalues:")
        for snappi_attr, ixn_map in attr_map.items():
            if isinstance(ixn_map, dict):
                ixn_attr = ixn_map.get("ixn_attr")
                if ixn_attr is None:
                    raise NameError("ixn_attr is missing within ", ixn_map)
                enum_map = ixn_map.get("enum_map")
                value = snappi_obj.get(snappi_attr)
                if value is None:
                    # We need to specify product default if model not specify
                    default_value = ixn_map.get("default_value")
                    if default_value is None:
                        raise NameError(
                            "Please specify default_value for ", snappi_attr
                        )
                    value = default_value
                if enum_map is not None and value is not None:
                    value = enum_map[value]
                self.logger.debug(
                    "ixn_attr %s with enum value %s" % (ixn_attr, value)
                )
            else:
                ixn_attr = ixn_map
                value = snappi_obj.get(snappi_attr)
                self.logger.debug(
                    "ixn_attr %s with value %s" % (ixn_attr, value)
                )
            ixn_obj[ixn_attr] = self.multivalue(value)

    def configure_multivalues_with_choice(self, snappi_obj, ixn_obj, attr_map):
        """attr_map contains snappi_key : ixn_key/ ixn_info in dict format"""
        self.logger.debug("configuring multivalues:")
        for snappi_attr, ixn_map in attr_map.items():
            ixn_attr = ixn_map
            value = snappi_obj.get(snappi_attr).get("value")
            if snappi_attr == "gateway_mac":
                ixn_obj["resolveGateway"] = self.multivalue(False)
            self.logger.debug("ixn_attr %s with value %s" % (ixn_attr, value))
            ixn_obj[ixn_attr] = self.multivalue(value)

    def get_symmetric_nodes(self, parent_list, node_name):
        nodes_list = []
        max_len = 0
        for parent in parent_list:
            nodes = getattr(parent, node_name)
            node_len = len(nodes)
            if node_len > max_len:
                max_len = node_len
            nodes_list.append(nodes)
        symmetric_nodes = []
        active_list = []
        for nodes in nodes_list:
            if len(nodes) == max_len:
                active_list.extend([True] * max_len)
                symmetric_nodes.extend(nodes)
            else:
                for index in range(0, max_len):
                    node = nodes[0]
                    if index < len(nodes):
                        node = nodes[index]
                        active_list.append(node.active)
                        symmetric_nodes.append(node)
                    else:
                        active_list.append(False)
                        symmetric_nodes.append(node)
        return NodesInfo(max_len, active_list, symmetric_nodes)


class NodesInfo(object):
    def __init__(self, max_len, active_list, symmetric_nodes):
        self._base = Base()
        self._max_len = max_len
        self._active_list = active_list
        self._symmetric_nodes = symmetric_nodes

    @property
    def max_len(self):
        return self._max_len

    @property
    def active_list(self):
        return self._active_list

    @property
    def symmetric_nodes(self):
        return self._symmetric_nodes

    @property
    def is_all_null(self):
        for node in self._symmetric_nodes:
            if node is not None:
                return False
        return True

    def get_values(self, attr_name, enum_map=None, default=None):
        """This will extract values from NodesInfo object.
        It will set default value if value is None and have some default
        Otherwise raise error"""
        values = []
        for node in self._symmetric_nodes:
            value = node.get(attr_name)
            if value is None:
                if default is None:
                    raise NameError(
                        "Please specify default_value for ", attr_name
                    )
                value = default
            if enum_map is not None:
                value = enum_map[value]
            values.append(value)
        return values

    def get_multivalues(self, attr_name, enum_map=None, default=None):
        return self._base.multivalue(
            self.get_values(attr_name, enum_map=enum_map, default=default)
        )

    def config_values(self, ixn_obj, attr_map):
        for snappi_attr, ixn_map in attr_map.items():
            if isinstance(ixn_map, dict):
                ixn_attr = ixn_map.get("ixn_attr")
                if ixn_attr is None:
                    raise NameError("ixn_attr is missing within ", ixn_map)
                enum_map = ixn_map.get("enum_map")
                values = self.get_multivalues(
                    snappi_attr,
                    enum_map=enum_map,
                    default=ixn_map.get("default_value"),
                )
            else:
                ixn_attr = ixn_map
                values = self.get_multivalues(snappi_attr)
            ixn_obj[ixn_attr] = values

    def get_tab(self, tab_name):
        dummy_value = None
        tab_nodes = []
        for node in self._symmetric_nodes:
            tab_node = node.get(tab_name)
            if tab_node is not None:
                dummy_value = tab_node
            tab_nodes.append(tab_node)

        for idx, tab_node in enumerate(tab_nodes):
            if tab_node is None and dummy_value is not None:
                tab_nodes[idx] = dummy_value

        return NodesInfo(self._max_len, self._active_list, tab_nodes)

    def get_symmetric_nodes(self, node_name):
        return self._base.get_symmetric_nodes(self._symmetric_nodes, node_name)

    def get_group_nodes(self, tab_name):
        """We will pass a attribute names which is array in type
        Fill with other nodes and active_list as False
        It will raise error if all elements are not same length
        Finally return list of NodesInfo
        It will use some IxNetwork tab which do not have enable/disable features
        """
        dummy_tab = None
        for node in self._symmetric_nodes:
            dummy_tab = node.get(tab_name)
            if dummy_tab is not None:
                break
        tab_lengths = []
        group_nodes = []
        active_list = []
        for node in self._symmetric_nodes:
            tab = node.get(tab_name)
            if tab is None:
                active_list.append(False)
                if dummy_tab is None:
                    tab_lengths.append(0)
                else:
                    tab_lengths.append(len(dummy_tab))
                    tab = dummy_tab
            else:
                tab_lengths.append(len(tab))
                active_list.append(True)
            if len(set(tab_lengths)) > 1:
                raise Exception(
                    "All the attributes %s should have same lengths" % tab_name
                )
            for idx in range(tab_lengths[-1]):
                if len(group_nodes) <= idx:
                    group_nodes.append([tab[idx]])
                else:
                    group_nodes[idx].append(tab[idx])

        return active_list, [
            NodesInfo(1, self._active_list, group_node)  # use dummy one
            for group_node in group_nodes
        ]

    def get_active_group_nodes(self, tab_name):
        """It will cover get_group_nodes
        At the same time it will raise error if None node
        because IxNetwork do not have active field for those"""
        active_list, node_info_list = self.get_group_nodes(tab_name)
        if len(set(active_list)) > 1:
            raise Exception(
                "All the attributes %s should configure with equal length"
                % tab_name
            )
        return node_info_list
