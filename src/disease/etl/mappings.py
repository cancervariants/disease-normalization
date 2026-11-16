"""Load curated mappings separately from source-derived concepts (ADR-002)."""

from collections import defaultdict
from csv import DictReader
from enum import StrEnum
from importlib.resources import files
from importlib.resources.abc import Traversable
from itertools import dropwhile

from ga4gh.core.models import ConceptMapping, Extension, Relation
from pydantic import BaseModel, field_validator

from disease.schemas import concept_id_to_coding

_ETL_DIR = files("disease").joinpath("etl")
CATEGORY_MAPPINGS = _ETL_DIR.joinpath("category_mappings.sssom.tsv")
CONCEPT_MAPPINGS = _ETL_DIR.joinpath("concept_mappings.sssom.tsv")


class MappingJustification(StrEnum):
    """Supported justifications for asserting a mapping."""

    MANUAL_MAPPING_CURATION = "semapv:ManualMappingCuration"


class SssomMapping(BaseModel):
    """Represent a curated SSSOM row with explicit per-mapping provenance."""

    subject_id: str
    subject_label: str
    predicate_id: Relation
    object_id: str
    object_label: str
    mapping_justification: MappingJustification
    author_id: str
    comment: str | None = None

    @field_validator("predicate_id", mode="before")
    @classmethod
    def parse_predicate(cls, value: str) -> str:
        """Translate a SKOS CURIE into the relation used by GKM."""
        return value.removeprefix("skos:")

    def to_concept_mapping(self) -> ConceptMapping:
        """Convert the target and curation provenance to a GKM mapping."""
        coding = concept_id_to_coding(self.object_id)
        if coding is None:
            msg = f"Unsupported mapping target: {self.object_id}"
            raise ValueError(msg)
        coding.name = self.object_label
        extensions = [
            Extension(name="mapping_justification", value=self.mapping_justification),
            Extension(name="author_id", value=self.author_id),
        ]
        if self.comment:
            extensions.append(Extension(name="comment", value=self.comment))
        return ConceptMapping(
            coding=coding, relation=self.predicate_id, extensions=extensions
        )


def load_mappings(path: Traversable) -> defaultdict[str, list[SssomMapping]]:
    """Read the bundled SSSOM TSV profile, grouped by subject identifier.

    Provenance must be supplied on each row; mapping-set metadata is not inherited.
    Leading comment lines contain mapping-set metadata. Rows must have all declared
    columns, including an empty comment column when no comment is supplied.

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
        required = SssomMapping.model_fields.keys() - {"comment"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            msg = f"Missing required SSSOM columns in {path}"
            raise ValueError(msg)
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                msg = f"Incorrect number of SSSOM columns in {path}: {row}"
                raise ValueError(msg)
            row["comment"] = row.get("comment") or None
            mapping = SssomMapping(**row)
            mappings[mapping.subject_id].append(mapping)
    return mappings


def get_etl_mappings() -> defaultdict[str, list[ConceptMapping]]:
    """Return curated mappings for the database API, keyed by source concept ID.

    Category mappings must be broad matches to OncoTree; concept mappings must be
    exact matches. Callers must pass the results separately from source-derived
    ``Condition.mappings``, using the proposed ``curated_mappings`` argument.
    """
    mappings = defaultdict(list)
    for path, relation in (
        (CATEGORY_MAPPINGS, Relation.BROAD_MATCH),
        (CONCEPT_MAPPINGS, Relation.EXACT_MATCH),
    ):
        for subject_id, rows in load_mappings(path).items():
            for row in rows:
                if row.predicate_id != relation:
                    msg = f"Expected {relation.value} in {path}: {subject_id}"
                    raise ValueError(msg)
                if (
                    relation == Relation.BROAD_MATCH
                    and row.object_id.partition(":")[0].lower() != "oncotree"
                ):
                    msg = f"Expected an OncoTree category in {path}: {row.object_id}"
                    raise ValueError(msg)
                mappings[subject_id].append(row.to_concept_mapping())
    return mappings
