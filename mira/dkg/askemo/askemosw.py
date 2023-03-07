import os

import pandas as pd

header_row = 1
row_count = 59
columns = list(range(8))
google_sheet_csv_export_url = os.environ["SPACE_ONTOLOGY_URL"]

df = pd.read_csv(
    google_sheet_csv_export_url,
    header=header_row,
    nrows=row_count,
    usecols=columns,
)

print(df.head())
print(df.tail())
