"""Load curated mappings separately from source-derived concepts (ADR-002)."""

from collections import defaultdict
from csv import DictReader
from importlib.resources import files
from importlib.resources.abc import Traversable
from itertools import dropwhile
from typing import NamedTuple

from ga4gh.core.models import ConceptMapping

from disease.schemas import SssomMapping

CURATED_MAPPINGS = files("disease.etl").joinpath("curated_mappings.sssom.tsv")


def load_mappings(path: Traversable) -> defaultdict[str, list[SssomMapping]]:
    """Read the bundled SSSOM TSV profile, grouped by subject identifier.

    Provenance must be supplied on each row; mapping-set metadata is not inherited.
    Leading comment lines contain mapping-set metadata. Rows must have all declared
    columns. Source version columns are required, but their cells may be empty.

    :param path: mapping file to read
    :raise ValueError: if a row has an incorrect number of columns
    :raise pydantic.ValidationError: if a row fails model validation
    """
    mappings = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        reader = DictReader(
            dropwhile(lambda line: line.startswith("#") or not line.strip(), f),
            delimiter="\t",
        )
        optional = {
            "comment",
            "subject_source",
            "object_source",
            "predicate_modifier",
        }
        required = SssomMapping.model_fields.keys() - optional
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            msg = f"Missing required SSSOM columns in {path}"
            raise ValueError(msg)
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                msg = f"Incorrect number of SSSOM columns in {path}: {row}"
                raise ValueError(msg)
            mapping = SssomMapping(
                **{field: value or None for field, value in row.items()}
            )
            mappings[mapping.subject_id].append(mapping)
    return mappings


class EtlMappings(NamedTuple):
    """Curated additions and rejections, indexed by subject ID."""

    curated_mappings: dict[str, list[ConceptMapping]]
    mapping_negations: dict[str, list[ConceptMapping]]


def get_etl_mappings() -> EtlMappings:
    """Return positive mappings and negations, each keyed by subject ID."""
    mappings = defaultdict(list)
    negations = defaultdict(list)
    for subject_id, rows in load_mappings(CURATED_MAPPINGS).items():
        for row in rows:
            if row.predicate_modifier is None:
                mappings[subject_id].append(row.to_concept_mapping())
            else:
                negations[subject_id].append(row.to_concept_mapping(allow_negated=True))
    return EtlMappings(mappings, negations)
