import os
import csv

HERE = os.path.dirname(os.path.abspath(__file__))


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


def make_sbml_units():
    import libsbml
    module_contents = dir(libsbml)
    unit_kinds = {var: var.split('_')[-1].lower()
                  for var in module_contents
                  if var.startswith("UNIT_KIND")
                  and var != "UNIT_KIND_INVALID"}
    unit_kinds = {getattr(libsbml, var): unit_name
                  for var, unit_name in unit_kinds.items()}
    with open(get_resource_file('sbml_units.csv'), 'w') as fh:
        csv.writer(fh).writerows(sorted(unit_kinds.items()))