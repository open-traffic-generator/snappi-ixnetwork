from snappi_ixnetwork.logger import get_ixnet_logger


class IxNetObjects(object):
    def __init__(self, ixnetworkapi):
        self._ixnet_infos = {}
        self.logger = get_ixnet_logger(__name__)
        self._api = ixnetworkapi

    # get_ixn_href
    def get_href(self, name):
        """Returns an href given a unique configuration name"""
        obj = self.get(name)
        self.logger.debug("get_href %s : %s" % (name, obj.href))
        return obj.href

    def get_xpath(self, name):
        """Returns an xpath given a unique configuration name"""
        obj = self.get(name)
        self.logger.debug("get_xpath %s : %s" % (name, obj.xpath))
        return obj.xpath

    def get_object(self, name):
        """Returns an internal ixnobject given a unique configuration name"""
        obj = self.get(name)
        return obj.ixnobject

    @property
    def names(self):
        """Returns all names stored as keys"""
        return self._ixnet_infos.keys()

    def get(self, name):
        try:
            return self._ixnet_infos[name]
        except KeyError:
            self.logger.debug("These are existing names %s" % self.names)
            raise NameError(
                "snappi object named {0} not found in internal db".format(name)
            )

    def get_working_dg(self, name):
        ixn_obj = self.get(name)
        return ixn_obj.working_dg

    def set(self, name, ixnobject):
        self._ixnet_infos[name] = IxNetInfo(
            ixnobject, self._api.ngpf.working_dg
        )

    def set_scalable(self, ixnobject):
        names = ixnobject.get("name")
        self.logger.debug("set_scalable names : %s" % names)
        set_names = []
        for index, name in enumerate(names):
            if name is None or name in set_names:
                continue
            if name not in self._ixnet_infos:
                continue
            # Same name may present within different object structure
            old_keys = sorted(self._ixnet_infos[name].ixnobject)
            keys = sorted(ixnobject)
            if old_keys != keys:
                continue
            set_names.append(name)
            self._ixnet_infos[name] = IxNetInfo(
                ixnobject,
                self.get_working_dg(names[0]),
                index=index,
                multiplier=names.count(name),
                names=names,
            )


class IxNetInfo(object):
    # index start with 0 and use multiplier for count
    def __init__(
        self, ixnobject, working_dg, index=0, multiplier=1, names=None
    ):
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
