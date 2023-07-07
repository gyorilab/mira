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


def _expression_yielder(model_json, is_unit=False):
    # Recursively yield all (sympy, mathml) string pairs in the model json
    if isinstance(model_json, list):
        for item in model_json:
            yield from _expression_yielder(item)
    elif isinstance(model_json, dict):
        if "expression" in model_json and "expression_mathml" in model_json:
            yield (model_json["expression"],
                   model_json["expression_mathml"],
                   is_unit)

        # Otherwise, check if 'units' key is in the dict, indicating that
        # the expression is a unit
        is_units = "units" in model_json
        for value in model_json.values():
            # Otherwise, recursively yield from the value
            yield from _expression_yielder(value, is_units)
    # Otherwise, do nothing since we only care about the expression and
    # expression_mathml fields in a dict


def _remove_all_sympy(json_data, method="pop", inplace: bool = True):
    if method not in ("pop", "clear"):
        raise ValueError(f"Invalid method: {method}, must be 'pop' or 'clear'")
    # Recursively remove all sympy expressions
    if isinstance(json_data, list):
        for item in json_data:
            _remove_all_sympy(item)
    elif isinstance(json_data, dict):
        if "expression" in json_data:
            # Remove value
            if method == "pop":
                json_data.pop("expression")
            elif method == "clear":
                json_data["expression"] = ""
        else:
            # Recursive call
            for val in json_data.values():
                _remove_all_sympy(val)

    if not inplace:
        return json_data
