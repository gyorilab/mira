import os


HERE = os.path.dirname(os.path.abspath(__file__))
AMR_SCHEMA_PATH = os.path.join(HERE, "amr_schemas")

AMR_SCHEMA_BASE_URL = ("https://raw.githubusercontent.com/DARPA-ASKEM/"
                       "Model-Representations")
URL_SCHEMA_MAPPING = {
    f"{AMR_SCHEMA_BASE_URL}/petrinet_v0.6/petrinet/petrinet_schema.json":
        "petrinet_v0.6.json",
    f"{AMR_SCHEMA_BASE_URL}/regnet_v0.2/regnet/regnet_schema.json":
        "regnet_v0.2.json",
    f"{AMR_SCHEMA_BASE_URL}s/stockflow_v0.1/stockflow/stockflow_schema.json":
        "stockflow_v0.1.json"
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
