import re
from collections import namedtuple
from collections.abc import Mapping


def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


def convert_as_values(as_types, as_values):
    ConvertedAsValues = namedtuple_with_defaults(
        "ConvertedAsValues",
        ("as_num", "as4_num", "ip_addr", "assign_num", "common_num"),
        ([], [], [], [], []),
    )

    convert_values = ConvertedAsValues()
    for idx, as_type in enumerate(as_types):
        num, assign = as_values[idx].split(":")
        convert_values.as_num.append("65101")
        convert_values.as4_num.append("65101")
        convert_values.common_num.append("65101")
        convert_values.ip_addr.append("1.1.1.1")
        convert_values.assign_num.append(assign)
        if as_type == "as":
            convert_values.as_num[idx] = num
            convert_values.common_num[idx] = num
        elif as_type == "as4":
            convert_values.as4_num[idx] = num
            convert_values.common_num[idx] = num
        else:
            convert_values.ip_addr[idx] = num
    return convert_values


def hex_to_ipv4(hex_value):
    bytes = ["".join(x) for x in zip(*[iter(hex_value)] * 2)]
    bytes = [int(x, 16) for x in bytes]
    return ".".join(str(x) for x in reversed(bytes))
