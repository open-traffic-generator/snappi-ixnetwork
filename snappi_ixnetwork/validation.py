class Validation(object):
    """Validate the configuration

    Ensures entire configuration has unique names

    Args
    ----
    - ixnetworkapi (Api): instance of the ixnetworkapi class
    """

    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi

    def validate_config(self):
        self._unique_name_errors = []
        self.__check_config_objects(self._api.snappi_config)
        if len(self._unique_name_errors) > 0:
            raise NameError(", ".join(self._unique_name_errors))

    def __check_config_objects(self, config_item):
        if config_item is None:
            return
        config_item.validate()

        if (
            hasattr(config_item, "choice") is True
            and getattr(config_item, "choice") is None
        ):
            return

        for attr_name in config_item._properties:
            if attr_name.startswith("_") or attr_name == "parent":
                continue
            attr_value = config_item.get(attr_name)
            if callable(attr_value) is True:
                continue

            if attr_name == "name":
                if attr_value in self._api._config_objects:
                    self._unique_name_errors.append(
                        '%s.name: "%s" is not unique'
                        % (config_item.__class__.__name__, attr_value)
                    )
                # todo: we will enable after finalyze model
                if attr_value is None:
                    continue
                    # self._unique_name_errors.append('%s.name: "None" is not allowed' % (config_item.__class__.__name__))
                else:
                    self._api._config_objects[attr_value] = config_item
            elif "__module__" in dir(attr_value):
                if attr_value.__module__.startswith("snappi"):
                    if "__next__" in dir(attr_value):
                        for item in attr_value:
                            if getattr(item, "parent", None) is not None:
                                self.__check_config_objects(item.parent)
                            else:
                                self.__check_config_objects(item)
                    else:
                        self.__check_config_objects(attr_value)
