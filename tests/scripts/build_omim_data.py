"""Build OMIM test data."""

import csv
from pathlib import Path

from disease.database import create_db
from disease.etl import OMIM

TEST_IDS = [
    "309200",
    "613065",
    "247640",
]

omim = OMIM(create_db())
omim._extract_data()
TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "omim"
outfile_path = TEST_DATA_DIR / omim._data_file.name
outfile_path.parent.mkdir(exist_ok=True)

with omim._data_file.open() as f:
    rows = list(csv.reader(f, delimiter="\t"))

write_rows = []

# get headers
write_rows.append(rows.pop(0))
write_rows.append(rows.pop(0))
write_rows.append(rows.pop(0))

write_rows.extend(row for row in rows if row[0].startswith("#") or row[1] in TEST_IDS)

with outfile_path.open("w") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerows(write_rows)
