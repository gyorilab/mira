from typing import Any, List, Mapping

import requests
from dkg.client import Entity

__all__ = [
    "search_wikidata",
]

#: See documentation for query action at
#: https://www.wikidata.org/w/api.php?action=help&modules=query
WIKIDATA_API = "https://www.wikidata.org/w/api.php"


def search_wikidata(text: str) -> List[Entity]:
    """Search Wikidata with the given text string."""
    payload = {
        "action": "wbsearchentities",
        "search": text,
        "language": "en",
        "format": "json",
        "limit": 50,
    }
    res = requests.get(WIKIDATA_API, params=payload)
    res.raise_for_status()
    res_json = res.json()
    results = [_process_result(r) for r in res_json["search"]]
    # TODO if "search-continue" is available, then there are more results to paginate through.
    return results


def _process_result(record: Mapping[str, Any]) -> Entity:
    return Entity(
        id=f"wikidata:{record['id']}",
        name=record["label"],
        description=record.get("description", ""),
        type="class",
        labels=["wikidata"],
        obsolete=False,
    )


if __name__ == "__main__":
    print(*search_wikidata("plant"), sep="\n")
    # print(json.dumps(search_wikidata("plant"), indent=2))
