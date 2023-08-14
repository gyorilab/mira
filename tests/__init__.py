"""Tests for MIRA."""
import json

from mira.metamodel import SympyExprStr


def sorted_json_str(json_dict, ignore_key=None, skip_empty: bool = False) -> str:
    """Create a sorted json string from a json compliant object

    Parameters
    ----------
    json_dict :
        A json compliant object
    ignore_key :
        Key to ignore in dictionaries
    skip_empty :
        Skip values that evaluates to False, except for 0, 0.0, and False

    Returns
    -------
    :
        A sorted string representation of the json_dict object
    """
    if isinstance(json_dict, str):
        if skip_empty and not json_dict:
            return ""
        return json_dict
    elif isinstance(json_dict, (int, float, SympyExprStr)):
        if skip_empty and not json_dict and json_dict != 0 and json_dict != 0.0:
            return ""
        return str(json_dict)
    elif isinstance(json_dict, (tuple, list, set)):
        if skip_empty and not json_dict:
            return ""
        out_str = "[%s]" % (
            ",".join(sorted(sorted_json_str(s, ignore_key, skip_empty) for s in
                            json_dict))
        )
        if skip_empty and out_str == "[]":
            return ""
        return out_str
    elif isinstance(json_dict, dict):
        if skip_empty and not json_dict:
            return ""

        # Here skip the key value pair if skip_empty is True and the value
        # is empty
        def _k_v_gen(d):
            for k, v in d.items():
                if ignore_key is not None and k == ignore_key:
                    continue
                if skip_empty and not v and v != 0 and v != 0.0 and v is not False:
                    continue
                yield k, v

        dict_gen = (
            str(k) + sorted_json_str(v, ignore_key, skip_empty)
            for k, v in _k_v_gen(json_dict)
        )
        out_str = "{%s}" % (",".join(sorted(dict_gen)))
        if skip_empty and out_str == "{}":
            return ""
        return out_str
    elif json_dict is None:
        return json.dumps(json_dict)
    else:
        raise TypeError("Invalid type: %s" % type(json_dict))


def expression_yielder(model_json, is_unit=False):
    """Recursively yield all (sympy, mathml) string pairs in the model json

    Parameters
    ----------
    model_json :
        The model json to yield from
    is_unit :
        Whether the current expression is a unit

    Yields
    ------
    :
        A (sympy, mathml) string pair
    """
    if isinstance(model_json, list):
        for item in model_json:
            yield from expression_yielder(item)
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
            yield from expression_yielder(value, is_units)
    # Otherwise, do nothing since we only care about the expression and
    # expression_mathml fields in a dict


def remove_all_sympy(json_data, method="pop"):
    """Remove all sympy expressions from the model json by either popping or
    clearing the expression field.

    Parameters
    ----------
    json_data :
        The data to check completion for
    method :
        The method to use to remove the sympy expression. Either "pop" or
        "clear" (default: "pop"). If "pop", the expression is removed from
        the dict. If "clear", the expression is set to an empty string.
    """
    if method not in ("pop", "clear"):
        raise ValueError(f"Invalid method: {method}, must be 'pop', 'clear' "
                         f"or 'null'")
    # Recursively remove all sympy expressions
    if isinstance(json_data, list):
        for item in json_data:
            remove_all_sympy(item)
    elif isinstance(json_data, dict):
        if "expression" in json_data:
            # Remove value
            if method == "pop":
                json_data.pop("expression")
            elif method == "clear":
                json_data["expression"] = ""
            elif method == "null":
                json_data["expression"] = None
        else:
            # Recursive call
            for val in json_data.values():
                remove_all_sympy(val)
