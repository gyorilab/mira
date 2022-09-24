import os

HERE = os.path.dirname(os.path.abspath(__file__))


def get_resource_path(fname):
    """Return a full path to a given resource file name."""
    return os.path.join(HERE, fname)
