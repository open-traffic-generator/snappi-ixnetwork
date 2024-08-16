from snappi_ixnetwork.device.base import *
from snappi_ixnetwork.logger import get_ixnet_logger


class Compactor(object):
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        self._unsupported_nodes = []
        self._ignore_keys = ["xpath", "name"]
        self.logger = get_ixnet_logger(__name__)

    def compact(self, roots):
        if roots is None or len(roots) == 0:
            return
        similar_objs_list = []
        for root in roots:
            is_match = False
            for similar_objs in similar_objs_list:
                if self._comparator(similar_objs.primary_obj, root) is True:
                    similar_objs.append(root)
                    is_match = True
                    break
            if len(similar_objs_list) == 0 or is_match is False:
                similar_objs = SimilarObjects(root)
                similar_objs_list.append(similar_objs)

        for similar_objs in similar_objs_list:
            if len(similar_objs.objects) > 0:
                similar_objs.compact(roots)
                self.set_scalable(similar_objs.primary_obj)

    def _comparator(self, src, dst):
        if type(src) != type(dst):
            raise Exception("comparision issue")
        src_node_keys = [
            k for k, v in src.items() if not isinstance(v, MultiValue)
        ]
        dst_node_keys = [
            k for k, v in dst.items() if not isinstance(v, MultiValue)
        ]
        src_node_keys.sort()
        src_node_keys = list(set(src_node_keys) - set(self._ignore_keys))
        dst_node_keys.sort()
        dst_node_keys = list(set(dst_node_keys) - set(self._ignore_keys))
        if src_node_keys != dst_node_keys:
            return False
        for key in src_node_keys:
            if key in self._unsupported_nodes:
                return False
            src_value = src.get(key)
            dst_value = dst[key]
            if isinstance(src_value, dict):
                if self._comparator(src_value, dst_value) is False:
                    return False
            # todo: we need to restructure if same element in different position
            elif isinstance(src_value, list):
                if len(src_value) != len(dst_value):
                    return False
                for index, src_dict in enumerate(src_value):
                    if not isinstance(src_dict, dict):
                        continue
                    if self._comparator(src_dict, dst_value[index]) is False:
                        return False
            # Scalar comparison
            elif isinstance(src_value, PostCalculated):
                if src_value.value != dst_value.value:
                    return False
            elif src_value != dst_value:
                return False
        return True

    def _get_names(self, ixnobject):
        name = ixnobject.get("name")
        if isinstance(name, MultiValue):
            name = name.value
        if not isinstance(name, list):
            name = [name]
        return name

    def set_scalable(self, parent):
        for key, value in parent.items():
            if key == "name":
                parent[key] = self._get_names(parent)
                self._api.ixn_objects.set_scalable(parent)
                self._api.ixn_routes.set_scalable(parent)
                continue
            if isinstance(value, list):
                for val in value:
                    if isinstance(val, dict):
                        self.set_scalable(val)
            elif isinstance(value, dict):
                self.set_scalable(value)


class SimilarObjects(Base):
    def __init__(self, primary_obj):
        super(SimilarObjects, self).__init__()
        self._primary_obj = primary_obj
        self._objects = []
        self._ignore_keys = ["xpath"]

    @property
    def primary_obj(self):
        return self._primary_obj

    @property
    def objects(self):
        return self._objects

    def append(self, object):
        self._objects.append(object)

    def compact(self, roots):
        multiplier = len(self._objects) + 1
        for object in self._objects:
            self._value_compactor(self._primary_obj, object)
            roots.remove(object)
        self._primary_obj["multiplier"] = multiplier

    def _value_compactor(self, src, dst):
        for key, value in src.items():
            if key in self._ignore_keys:
                continue
            src_value = src.get(key)
            dst_value = dst.get(key)
            if key == "name":
                src_value = (
                    src_value
                    if isinstance(src_value, MultiValue)
                    else self.multivalue(src_value)
                )
                dst_value = (
                    dst_value
                    if isinstance(dst_value, MultiValue)
                    else self.multivalue(dst_value)
                )
            # todo: fill with product default value for
            # if dst_value is None:
            #     dst_value = obj.get(key, with_default=True)
            if isinstance(dst_value, list):
                for index, dst_dict in enumerate(dst_value):
                    if not isinstance(dst_dict, dict):
                        continue
                    self._value_compactor(src_value[index], dst_dict)
            elif isinstance(dst_value, dict):
                self._value_compactor(src_value, dst_value)
            elif isinstance(src_value, MultiValue):
                src_value = src_value.value
                dst_value = dst_value.value
                if not isinstance(dst_value, list):
                    dst_value = [dst_value]
                if isinstance(src_value, list):
                    src_value.extend(dst_value)
                else:
                    src_value = [src_value] + dst_value
                src[key] = self.multivalue(src_value)
