import csv
import sys
from pathlib import Path
from bs4 import BeautifulSoup


def save_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def extract_file(html_file, output_dir):
    pmid = html_file.stem
    paper_dir = output_dir / pmid
    paper_dir.mkdir(parents=True, exist_ok=True)

    soup = BeautifulSoup(html_file.read_text(encoding="utf-8", errors="ignore"), "html.parser")

    results = []
    for i, table in enumerate(soup.find_all("table"), 1):
        rows = [
            [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            for tr in table.find_all("tr")
        ]
        rows = [r for r in rows if r]

        caption = table.find("caption")
        caption_text = caption.get_text(" ", strip=True) if caption else ""

        html_path = paper_dir / f"table_{i}.html"
        csv_path = paper_dir / f"table_{i}.csv"
        html_path.write_text(str(table), encoding="utf-8")
        save_csv(rows, csv_path)

        n_cols = max((len(r) for r in rows), default=0)

        header_text = " ".join(rows[0]).lower() if rows else ""
        is_param_table = "parameter" in (caption_text + " " + header_text).lower()

        results.append([
            pmid, i, caption_text, len(rows), n_cols,
            is_param_table, str(html_path), str(csv_path),
        ])

    return results


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: marker_table_extraction.py INPUT_DIR OUTPUT_DIR SUMMARY_CSV")

    input_dir, output_dir, summary_path = (Path(p) for p in sys.argv[1:4])
    output_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_dir.glob("*.html"))
    if not html_files:
        sys.exit(f"no HTML files found in {input_dir}")

    summary = []
    for html_file in html_files:
        tables = extract_file(html_file, output_dir)
        summary.extend(tables)
        print(f"{html_file.name}: {len(tables)} tables")

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pmid", "table_number", "caption", "rows", "columns",
                          "parameter_table", "html_file", "csv_file"])
        writer.writerows(summary)

    print(f"\n{len(html_files)} papers, {len(summary)} tables -> {summary_path}")


if __name__ == "__main__":
    main()
