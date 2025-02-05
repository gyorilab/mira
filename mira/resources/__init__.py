import os
from pathlib import Path
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
AMR_SCHEMA_PATH = Path(HERE + "/amr_schemas")

URL_SCHEMA_MAPPING = {
    "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/petrinet_v0.6/petrinet/petrinet_schema.json": "petrinet_v0.6.json",
    "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/regnet_v0.2/regnet/regnet_schema.json": "regnet_v0.2.json",
    "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/stockflow_v0.1/stockflow/stockflow_schema.json": "stockflow_v0.1.json"
}


def get_resource_file(fname):
    """Return the path to a resource file.

    Parameters
    ----------
    fname : str
        The name of the file.

    Returns
    -------
    str
        The path to the file.
    """
    return os.path.join(HERE, fname)
