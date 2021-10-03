from snappi_ixnetwork.device.base import *


class Compactor(object):
    def __init__(self):
        self._unsupported_nodes = []

    @staticmethod
    def ignore_keys():
        return [
            "xpath", "name"
        ]

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
            similar_objs.compact(roots)

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
        src_node_keys = list(set(src_node_keys) - set(Compactor.ignore_keys()))
        dst_node_keys.sort()
        dst_node_keys = list(set(dst_node_keys) - set(Compactor.ignore_keys()))
        if src_node_keys != dst_node_keys:
            return False
        for key in src_node_keys:
            if key in self._unsupported_nodes:
                return False
            src_value = src.get(key)
            if isinstance(src_value, AttDict):
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


class SimilarObjects(Base):
    def __init__(self, primary_obj):
        super(SimilarObjects, self).__init__()
        self._primary_obj = primary_obj
        self._objects = []

    @property
    def primary_obj(self):
        return self._primary_obj

    def append(self, object):
        self._objects.append(object)

    def compact(self, roots):
        multiplier = len(self._objects) + 1
        for object in self._objects:
            self._value_compactor(
                self._primary_obj, object
            )
            roots.remove(object)
        self._primary_obj["multiplier"] = multiplier

    def _value_compactor(self, src, dst):
        for key, value in src.items():
            if key in Compactor.ignore_keys():
                continue
            src_value = src.get(key)
            dst_value = dst.get(key)
            # todo: fill with product default value for
            # if dst_value is None:
            #     dst_value = obj.get(key, with_default=True)
            if isinstance(dst_value, list):
                for index, dst_dict in enumerate(dst_value):
                    self._value_compactor(
                        src_value[index], dst_dict
                    )
            elif isinstance(dst_value, AttDict):
                self._value_compactor(src_value, dst_value)
            elif isinstance(src_value, MultiValue):
                src_value = src_value.get_value()
                dst_value = dst_value.get_value()
                if not isinstance(dst_value, list):
                    dst_value = [dst_value]
                if isinstance(src_value, list):
                    src_value.extend(dst_value)
                else:
                    src_value = [src_value] + dst_value
                src[key] = self.multivalue(src_value)
