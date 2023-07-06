"""Tests for MIRA."""
import json

from mira.metamodel import SympyExprStr


def sorted_json_str(json_dict, ignore_key=None) -> str:
    if isinstance(json_dict, str):
        return json_dict
    elif isinstance(json_dict, (int, float, SympyExprStr)):
        return str(json_dict)
    elif isinstance(json_dict, (tuple, list, set)):
        return "[%s]" % (
            ",".join(sorted(sorted_json_str(s, ignore_key) for s in json_dict))
        )
    elif isinstance(json_dict, dict):
        if ignore_key is not None:
            dict_gen = (
                str(k) + sorted_json_str(v, ignore_key)
                for k, v in json_dict.items()
                if k != ignore_key
            )
        else:
            dict_gen = (
                str(k) + sorted_json_str(v, ignore_key) for k, v in json_dict.items()
            )
        return "{%s}" % (",".join(sorted(dict_gen)))
    elif json_dict is None:
        return json.dumps(json_dict)
    else:
        raise TypeError("Invalid type: %s" % type(json_dict))
