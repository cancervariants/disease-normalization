"""Construct test data for Mondo source."""

from collections import defaultdict
from pathlib import Path

import fastobo

from disease.database import create_db
from disease.etl import Mondo

mondo = Mondo(create_db())
mondo._extract_data()
infile = str(mondo._data_file.absolute())

scripts_dir = Path(__file__).resolve().parent
test_data_dir = scripts_dir.parent / "data" / "mondo"

reader = fastobo.iter(infile)
dag = defaultdict(list)
for frame in reader:
    item_id = str(frame.id)
    for clause in frame:
        if clause.raw_tag() == "is_a":
            dag[item_id].append(clause.raw_value())


def construct_inheritance_set(dag: defaultdict, child: str) -> set[str]:
    """Get IDs for concepts that a child concept inherits from

    :param dag: dictionary keying IDs to parent concepts
    :param child: concept to fetch parents of
    :return: set of parent concepts
    """
    parents = {child}
    for parent in dag[child]:
        parents |= construct_inheritance_set(dag, parent)
    return parents


relevant_terms = set()
for term in (
    "MONDO:0005072",
    "MONDO:0002083",
    "MONDO:0003587",
    "MONDO:0004099",
    "MONDO:0005233",
    "MONDO:0010648",
    "MONDO:0009539",
    "MONDO:0013108",
    "MONDO:0013082",
):
    relevant_terms |= construct_inheritance_set(dag, term)

outfile = test_data_dir / mondo._data_file.name
outfile.parent.mkdir(exist_ok=True)
with outfile.open("w") as f:
    doc = fastobo.load(infile)
    f.write(str(doc.header))
    f.write("\n")

    reader = fastobo.iter(infile)
    for frame in reader:
        if isinstance(frame, fastobo.term.TermFrame):
            if str(frame.id) in relevant_terms:
                f.write(str(frame))
                f.write("\n")
        else:
            f.write(str(frame))
            f.write("\n")
