import json


class Validation(object):
    """Validate the configuration

    Ensures entire configuration has unique names

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    """
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
    
    def validate_config(self):
        self._unique_name_errors = []
        self.__check_config_objects(self._api.config)
        if len(self._unique_name_errors) > 0:
            raise NameError(', '.join(self._unique_name_errors))

    def __check_config_objects(self, config_item):
        if config_item is None:
            return
        for attr_name in dir(config_item):
            if attr_name.startswith('_'):
                continue
            attr_value = getattr(config_item, attr_name, None)
            if callable(attr_value) is True:
                continue
            if attr_name == 'name':
                if attr_value in self._api._config_objects:
                    self._unique_name_errors.append('%s.name: "%s" is not unique' % (config_item.__class__.__name__, attr_value))
                if attr_value is None:
                    self._unique_name_errors.append('%s.name: "None" is not allowed' % (config_item.__class__.__name__))
                else:
                    self._api._config_objects[attr_value] = config_item
            elif isinstance(attr_value, list):
                for item in attr_value:
                    self.__check_config_objects(item)
            elif '__module__' in dir(attr_value):
                if attr_value.__module__.startswith('abstract_open_traffic_generator'):
                    self.__check_config_objects(attr_value)

     