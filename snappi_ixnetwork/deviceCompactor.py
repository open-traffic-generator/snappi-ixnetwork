import json
from copy import deepcopy


class DeviceCompactor(object):
    def __init__(self, devices):
        self._device_count = 0
        self._devices = devices
        self._unsupported_nodes = ["sr_te_policies"]

    def compact(self):
        same_dev_list = []
        for device in self._devices:
            is_match = False
            for same_devs in same_dev_list:
                dev_dict = json.loads(device.serialize("json"))
                if self._comparator(same_devs.dev_schema, dev_dict) is True:
                    same_devs.append(device, dev_dict)
                    is_match = True
                    break
            if len(same_dev_list) == 0 or is_match is False:
                same_dev = SimilarDevices()
                same_dev.append(device)
                same_dev_list.append(same_dev)
        return same_dev_list

    def _comparator(self, src, dst):
        if type(src) != type(dst):
            raise Exception("comparision issue")
        src_node_keys = [
            k for k, v in src.items() if isinstance(v, (dict, list))
        ]
        dst_node_keys = [
            k for k, v in dst.items() if isinstance(v, (dict, list))
        ]
        src_node_keys.sort()
        dst_node_keys.sort()
        if src_node_keys != dst_node_keys:
            return False
        for key in src_node_keys:
            if key in self._unsupported_nodes:
                return False
            src_value = src.get(key)
            if isinstance(src_value, dict):
                dst_value = dst[key]
                if self._comparator(src_value, dst_value) is False:
                    return False
            # todo: we need to restructure if same element in different position
            if isinstance(src_value, list):
                dst_value = dst[key]
                if len(src_value) != len(dst_value):
                    return False
                for index, src_dict in enumerate(src_value):
                    if self._comparator(src_dict, dst_value[index]) is False:
                        return False
        return True


class SimilarDevices(object):
    def __init__(self):
        self._index = -1
        self._dev_compact = None
        self._dev_schema = None
        self._dev_obj = None
        self._ignore_keys = ["container_name", "name_list"]

    @property
    def dev_schema(self):
        if self._dev_schema is None:
            dev_dict = json.loads(self._dev_obj.serialize("json"))
            self._dev_schema = deepcopy(dev_dict)
            self._dev_compact = dev_dict
        return self._dev_schema

    @property
    def len(self):
        return self._index + 1

    @property
    def compact_dev(self):
        if self._index == 0:
            return self._dev_obj
        return self._dev_compact

    def append(self, dev_obj, dev_dict=None):
        self._index += 1
        if self._index == 0:
            self._dev_obj = dev_obj
            # self._fill_comp_dev(self._dev_compact, self._dev_obj)
        else:
            self._value_compactor(self._dev_compact, dev_dict, self._dev_obj)

    # def _fill_comp_dev(self, parent_dict, parent_obj):
    #     for key, obj_value in parent_obj._properties.items():
    #         if key in self._ignore_keys:
    #             continue
    #         if key == "name":
    #             parent_dict["name_list"] = [parent_dict.get(key)]
    #             continue
    #         dict_value = parent_dict.get(key)
    #         if isinstance(dict_value, list):
    #             for index, dst_dict in enumerate(dict_value):
    #                 self._fill_comp_dev(dst_dict, obj_value[index])
    #         elif isinstance(dict_value, dict):
    #             self._fill_comp_dev(dict_value, obj_value)
    #         elif dict_value is None:
    #             parent_dict[key] = [obj_value.get(key, with_default=True)]
    #         else:
    #             parent_dict[key] = [dict_value]

    def _value_compactor(self, src, dst, obj):
        for key, obj_value in obj._properties.items():
            if key in self._ignore_keys:
                continue
            src_value = src.get(key)
            dst_value = dst.get(key)
            if key == "name":
                if self._index == 1:
                    src["name_list"] = [src_value]
                src["name_list"].append(dst_value)
                continue
            if dst_value is None:
                dst_value = obj.get(key, with_default=True)
            if isinstance(dst_value, list):
                for index, dst_dict in enumerate(dst_value):
                    self._value_compactor(
                        src_value[index], dst_dict, obj_value[index]
                    )
            elif isinstance(dst_value, dict):
                self._value_compactor(src_value, dst_value, obj_value)
            else:
                if self._index == 1:
                    src_value = [src_value]
                src_value.append(dst_value)
                src[key] = src_value
