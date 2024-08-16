from snappi_ixnetwork.device.base import *
from snappi_ixnetwork.logger import get_ixnet_logger


class CreateIxnConfig(Base):
    def __init__(self, ngpf):
        super(CreateIxnConfig, self).__init__()
        self._ngpf = ngpf
        self.logger = get_ixnet_logger(__name__)
        self._post_calculated_info = list()

    def create(self, node, node_name, parent_xpath=""):
        if not isinstance(node, list):
            raise TypeError("Expecting list to loop through it")
        for idx, element in enumerate(node, start=1):
            if not isinstance(element, dict):
                raise TypeError("Expecting dict")
            xpath = """{parent_xpath}/{node_name}[{index}]""".format(
                parent_xpath=parent_xpath, node_name=node_name, index=idx
            )
            element["xpath"] = xpath
            self._process_element(element, xpath)

    def post_calculate(self):
        for element, key, value in self._post_calculated_info:
            element[key] = value.value

    def _process_element(self, element, parent_xpath, child_name=None):
        if child_name is not None and "xpath" in element:
            child_xpath = """{parent_xpath}/{child_name}""".format(
                parent_xpath=parent_xpath, child_name=child_name
            )
            element["xpath"] = child_xpath
        key_to_remove = []
        for key, value in element.items():
            if key == "name":
                element["name"] = self.get_name(element)
            elif isinstance(value, MultiValue):
                value = self._get_ixn_multivalue(value, key, element["xpath"])
                if value is None:
                    key_to_remove.append(key)
                else:
                    element[key] = value
            elif isinstance(value, PostCalculated):
                self._post_calculated_info.append([element, key, value])
            elif isinstance(value, dict):
                self._process_element(value, parent_xpath, key)
            elif (
                isinstance(value, list)
                and len(value) > 0
                and isinstance(value[0], dict)
            ):
                if child_name is not None:
                    self.create(value, key, element["xpath"])
                else:
                    self.create(value, key, parent_xpath)

        for key in key_to_remove:
            element.pop(key)

    def _get_ixn_multivalue(self, value, att_name, xpath):
        value = value.value
        ixn_value = {
            "xpath": "/multivalue[@source = '{xpath} {att_name}']".format(
                xpath=xpath, att_name=att_name
            )
        }
        if not isinstance(value, list):
            value = [value]
        if len(set(value)) == 1:
            if value[0] is None:
                return None
            else:
                ixn_value["singleValue"] = {
                    "xpath": "/multivalue[@source = '{xpath} {att_name}']/singleValue".format(
                        xpath=xpath, att_name=att_name
                    ),
                    "value": value[0],
                }
                return ixn_value
        else:
            ixn_value["valueList"] = {
                "xpath": "/multivalue[@source = '{xpath} {att_name}']/valueList".format(
                    xpath=xpath, att_name=att_name
                ),
                "values": value,
            }
            return ixn_value
