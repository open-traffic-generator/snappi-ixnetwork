# import yaml
# import json
#
#
# class SerDesObj(object):
#     """Comment removed"""
#
#     def __init__(self, data):
#         for name, value in data.items():
#             setattr(self, name, self._wrap(value))
#
#     def _wrap(self, value):
#         if isinstance(value, (tuple, list, set, frozenset)):
#             return type(value)([self._wrap(v) for v in value])
#         else:
#             return SerDesObj(value) if isinstance(value, dict) else value
#
#
# class SerDes(object):
#     def __init__(self):
#         pass
#
#     @staticmethod
#     def to_object(contents):
#         """Given a yaml or json string returns a python object
#         If contents is anything else it will just be returned.
#         """
#         if isinstance(contents, (bytes, str)):
#             return SerDes.to_object(yaml.safe_load(contents))
#         elif isinstance(contents, dict):
#             return SerDesObj(contents)
#         else:
#             return contents
#
#     @staticmethod
#     def to_json(obj):
#         """Given a python object returns a json string"""
#         return json.dumps(obj, indent=2, default=lambda x: x.__dict__)
#
#     @staticmethod
#     def to_yaml(obj):
#         """Given a python object returns a yaml string"""
#         return yaml.dump(obj)
#
#
# if __name__ == "__main__":
#     # start with yaml
#     y = """
# config:
#   description: |
#     A literal description.
#     Type-4bits
#      - {some brace}
#      - [some bracket]
#   ports:
#     - name: port 1
#       location: 1.1.1.1/1
#     - name: port 2
#       location: 1.1.1.1/2
#   flows: []
#   layer1: []
#   captures: []
#     """
#     # get object from yaml
#     o = SerDes.to_object(y)
#     # get json from object
#     j = SerDes.to_json(o)
#     print(j)
#     # get object from json
#     o = SerDes.to_object(j)
#     # get yaml from object
#     y = SerDes.to_yaml(o)
#     print(y)
