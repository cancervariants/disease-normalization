"""Build OncoTree test data.

It's actually just the real data, because it's not too big.
"""
import shutil
from pathlib import Path

from disease.database import Database
from disease.etl import OncoTree

oncotree = OncoTree(Database())
oncotree._extract_data()
TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "oncotree"
outfile_path = TEST_DATA_DIR / oncotree._data_file.name
outfile_path.parent.mkdir(exist_ok=True)

shutil.copyfile(oncotree._data_file, outfile_path)
