import re
from collections import namedtuple, Mapping

def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T


def asdot2plain(asdot):
    """This returns an ASPLAIN formated ASN given an ASDOT+ format"""
    if re.findall(r'\.|\:', asdot):
        left, right = re.split(r'\.|\:', asdot)
        ret = int(left) * 65536 + int(right)
        return ret
    else:
        return int(asdot)


def convert_as_values(as_types, as_values):
    ConvertedAsValues = namedtuple_with_defaults("ConvertedAsValues",
                                                 ("as_num", "as4_num", "assign_num"),
                                                 ([], [], []))

    convert_values = ConvertedAsValues()
    for idx, as_type in enumerate(as_types):
        num, assign = as_values[idx].split(":")
        convert_values.as_num.append("65101")
        convert_values.as4_num.append("65101")
        convert_values.assign_num.append(assign)
        if as_type == "as":
            convert_values.as_num[idx] = num
        elif as_type == "as4":
            convert_values.as4_num[idx] = num

    return convert_values