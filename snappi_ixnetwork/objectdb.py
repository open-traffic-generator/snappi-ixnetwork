#
# class DeviceObjects(Base):
#     def __init__(self):
#         super(DeviceObjects, self).__init__()
#         self._dev_map = {}
#
#     def set(self, object):
#         object_id = id(object)
#         name = self.get_name(object)
#         if object_id in self._dev_map:
#             self._dev_map[object_id].append(name)
#         else:
#             self._dev_map[object_id] = [name]
#
#     def get(self, object):
#         object_id = id(object)
#         if object_id not in self._dev_map:
#             raise NameError(
#                 "Somehow this object not stored"
#             )
#         return self._dev_map[object_id]
#
#     def pop(self, object_id):
#         if object_id in self._dev_map:
#             self._dev_map.pop(object_id)


class IxNetObjects(object):
    def __init__(self):
        self._ixn_objects = {}

    # get_ixn_href
    def get_href(self, name):
        """Returns an href given a unique configuration name"""
        obj = self.get(name)
        return obj.href

    def get_xpath(self, name):
        """Returns an xpath given a unique configuration name"""
        obj = self.get(name)
        return obj.xpath

    def get_object(self, name):
        """Returns an internal ixnobject given a unique configuration name"""
        obj = self.get(name)
        return obj.ixnobject

    def get_names(self, name):
        """Returns names ob objects got compacted to given a unique configuration name"""
        obj = self.get(name)
        return obj.names

    def get(self, name):
        try:
            return self._ixn_objects[name]
        except KeyError:
            raise NameError(
                "snappi object named {0} not found in internal db".format(
                    name
                )
            )

    def set(self, name, ixnobject):
        self._ixn_objects[name] = IxNetInfo(ixnobject)

    def set_scalable(self, ixnobject):
        names = ixnobject.get("name")
        set_names = []
        for index, name in enumerate(names):
            if name not in self._ixn_objects:
                continue
            if name is None or name in set_names:
                continue
            # Same name may present within different object structure
            old_keys = sorted(self._ixn_objects[name].ixnobject)
            keys = sorted(ixnobject)
            if old_keys != keys:
                continue
            set_names.append(name)
            self._ixn_objects[name] = IxNetInfo(
                ixnobject=ixnobject,
                index=index,
                multiplier=names.count(name),
                names=names
            )


class IxNetInfo(object):
    # index start with 0 and use multiplier for count
    def __init__(self, ixnobject, index=0, multiplier=1, names=None):
        self.ixnobject = ixnobject
        self.index = int(index)
        self.multiplier = int(multiplier)
        self.names = [] if names is None else names

    @property
    def xpath(self):
        return self.ixnobject.get("xpath")

    @property
    def href(self):
        return self.ixnobject.get("href")
