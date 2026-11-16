"""Define and load manually curated concept mappings in SSSOM format."""

from collections import defaultdict
from csv import DictReader
from enum import StrEnum
from importlib.resources import files
from importlib.resources.abc import Traversable
from itertools import dropwhile

from ga4gh.core.models import ConceptMapping, Extension, Relation
from pydantic import BaseModel

from disease.schemas import concept_id_to_coding

_MAPPINGS_DIR = files("disease_normalizer").joinpath("mappings", "data")

CATEGORY_MAPPINGS = _MAPPINGS_DIR.joinpath("category_mappings.sssom.tsv")
CONCEPT_MAPPINGS = _MAPPINGS_DIR.joinpath("cocnept_mappings.sssom.tsv")


class MappingJustification(StrEnum):
    """Supported justifications for asserting a mapping."""

    MANUAL_MAPPING_CURATION = "ManualMappingCuration"


class SssomMapping(BaseModel):
    """Represent a manually curated mapping between two concepts, using SSSOM."""

    subject_id: str
    subject_label: str
    predicate_id: Relation
    object_id: str
    object_label: str
    mapping_justification: MappingJustification
    author_id: str
    comment: str | None = None

    def to_concept_mapping(self) -> ConceptMapping:
        """Convert to GKM ConceptMapping instance

        :return: GKM ConceptMapping
        """
        extensions = [
            Extension(name="mapping_justification", value=self.mapping_justification),
            Extension(name="author_id", value=self.author_id),
        ]
        if self.comment:
            extensions.append(Extension(name="comment", value=self.comment))
        return ConceptMapping(
            coding=concept_id_to_coding(self.object_id),
            relation=self.predicate_id,
            extensions=extensions,
        )


def load_mappings(path: Traversable) -> defaultdict[str, list[SssomMapping]]:
    """Load mapping declarations from a TSV file, grouped by subject identifier.

    Column headers must correspond to the fields of ``SssomMapping``. Each row
    is validated when its mapping object is constructed.

    :param path: Path to the TSV file containing mapping declarations.
    :return: Mapping objects keyed by subject identifier, preserving file order within each subject's list.
    :raise OSError: If the file cannot be opened or read.
    :raise pydantic.ValidationError: If a row fails mapping validation.
    """
    mappings = defaultdict(list)
    with path.open(encoding="utf-8") as f:
        reader = DictReader(
            # skip metadata
            dropwhile(lambda line: line.startswith("#"), f),
            delimiter="\t",
        )
        for row in reader:
            mapping = SssomMapping(**row)
            row["comment"] = row["comment"] or None
            mappings[row["subject_id"]].append(mapping)
    return mappings


def get_etl_mappings() -> defaultdict[str, list[SssomMapping]]:
    """Load category and concept mappings for ETL, grouped by subject identifier.

    :return: dict with subject ID (case sensitive) as key and array of SSSOM mappings as value
    """
    mappings = load_mappings(CATEGORY_MAPPINGS)
    for subject_id, concept_mappings in load_mappings(CONCEPT_MAPPINGS).items():
        mappings[subject_id].extend(concept_mappings)
    return mappings
