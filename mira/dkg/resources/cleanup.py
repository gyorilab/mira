"""Clean up issues with the output"""

from pathlib import Path
import json

HERE = Path(__file__).parent.resolve()


def main():
    ncit_path = HERE.joinpath("ncit_slim.json")
    ncit = json.loads(ncit_path.read_text())
    rewrite = False
    for graph in ncit["graphs"]:
        if "id" not in graph:
            graph["id"] = "https://raw.githubusercontent.com/gyorilab/mira/main/mira/dkg/resources/ncit_slim.json"
            rewrite = True
    if rewrite:
        ncit_path.write_text(json.dumps(ncit, indent=2) + "\n")


if __name__ == '__main__':
    main()
