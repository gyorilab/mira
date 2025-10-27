from pyobo import Obo
from pyobo.struct.obo.reader import from_obo_path
from pystow.utils import download
import bioregistry
from pathlib import Path

__all__ = [
    "get_cso_obo",
]

HERE = Path(__file__).parent.resolve()
PATH = HERE.joinpath("cso.obo")
URL = "https://raw.githubusercontent.com/cthoyt/Climate-System-Ontology-CSO/main/cso.obo"


def get_cso_obo() -> Obo:
    bioregistry.manager.synonyms["cso"] = "cso"
    bioregistry.manager.registry["cso"] = bioregistry.Resource(
        name="Climate Systems Ontology",
        prefix="cso",
        homepage="https://github.com/cthoyt/Climate-System-Ontology-CSO",
        description="An ontology for climate systems",
    )
    download(url=URL, path=PATH)
    # use https://github.com/pyobo/pyobo/pull/159
    return from_obo_path(PATH, prefix="cso", strict=False)


if __name__ == "__main__":
    for term in get_cso_obo():
        print(term)
