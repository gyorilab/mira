from pathlib import Path
import itertools as itt
import os

HERE = Path(__file__).parent.resolve()
NCIT_PATH = HERE.joinpath("ncit.obo")
NCIT_SLIM_PATH = HERE.joinpath("ncit_subset.obo")
NCIT_SLIM_JSON_PATH = HERE.joinpath("ncit_subset.json")
TERMS_PATH = HERE.joinpath("ncit_terms.txt")


def main():
    target_terms = {l.strip() for l in TERMS_PATH.read_text().splitlines()}
    new_lines = []
    with NCIT_PATH.open() as file:
        lines = iter(file)
        # handle first stanza
        while line := next(lines).strip():
            new_lines.append(line.strip())

        new_lines.append("")

        c = 0
        groups = itt.groupby(lines, lambda line: not line.strip())
        for is_blank, sublines in groups:
            if is_blank:
                continue

            first, second, *rest = (s.strip() for s in sublines)
            if first != "[Term]":
                continue
            if not second.removeprefix("id: ").startswith("NCIT:"):
                continue
            if second.removeprefix("id: NCIT:") not in target_terms:
                continue
            new_lines.extend((first, second, *rest))
            new_lines.append("")

    with NCIT_SLIM_PATH.open("w") as file:
        for line in new_lines:
            print(line, file=file)

    os.system(f"robot convert --input {NCIT_SLIM_PATH} --output {NCIT_SLIM_JSON_PATH}")
    os.system(f"rm {NCIT_SLIM_PATH}")


if __name__ == '__main__':
    main()
