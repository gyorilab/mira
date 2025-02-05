import os
from pathlib import Path
import csv

HERE = os.path.dirname(os.path.abspath(__file__))
AMR_SCHEMA_PATH = Path(HERE + "/amr_schemas")

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
