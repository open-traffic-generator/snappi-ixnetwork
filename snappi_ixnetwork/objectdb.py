

class IxNetObjects(object):
    def __init__(self, ixnetworkapi):
        self._ixn_objects = {}
        self._api = ixnetworkapi

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

    @property
    def names(self):
        """Returns all names stored as keys"""
        return self._ixn_objects.keys()

    def get(self, name):
        try:
            return self._ixn_objects[name]
        except KeyError:
            raise NameError(
                "snappi object named {0} not found in internal db".format(
                    name
                )
            )

    def get_working_dg(self, name):
        ixn_obj = self.get(name)
        return ixn_obj.working_dg

    def set(self, name, ixnobject):
        self._ixn_objects[name] = IxNetInfo(
            ixnobject, self._api.ngpf.working_dg
        )

    def set_scalable(self, ixnobject):
        names = ixnobject.get("name")
        set_names = []
        for index, name in enumerate(names):
            if name is None or name in set_names:
                continue
            if name not in self._ixn_objects:
                continue
            # Same name may present within different object structure
            old_keys = sorted(self._ixn_objects[name].ixnobject)
            keys = sorted(ixnobject)
            if old_keys != keys:
                continue
            set_names.append(name)
            self._ixn_objects[name] = IxNetInfo(
                ixnobject,
                self.get_working_dg(names[0]),
                index=index,
                multiplier=names.count(name),
                names=names
            )


class IxNetInfo(object):
    # index start with 0 and use multiplier for count
    def __init__(self, ixnobject, working_dg, index=0, multiplier=1, names=None):
        self.ixnobject = ixnobject
        self.working_dg = working_dg
        self.index = int(index)
        self.multiplier = int(multiplier)
        self.names = [] if names is None else names

    @property
    def xpath(self):
        return self.ixnobject.get("xpath")

    @property
    def href(self):
        return self.ixnobject.get("href")

