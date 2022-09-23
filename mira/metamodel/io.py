import json
from .templates import


def model_from_json_file(fname):
    with open(fname, 'r') as fh:
