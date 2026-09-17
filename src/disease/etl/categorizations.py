"""Load disease categorizations (within OncoTree) for NCIt and MONDO terms.

Current plan:
    * Generate SSSOM mapping artifact for MONDO->OncoTree using skos:broadMatch
    * load each mapping into DB

MONDO mapping algorithm
* Given a mondo term, construct ancestral set of all oncotree mappings by walking up
  inheritance tree and stopping when an oncotree xref is found
* If set consists of multiple distinct oncotree mappings: (TODO)
    * if one is a more specific form of the other, choose the more specific term
    * if both have a common parent, take the parent term
"""

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import fastobo
from wags_tails import MondoData, OncoTreeData

from disease.database.database import AbstractDatabase
from disease.schemas import SourceName

_logger = logging.getLogger(__name__)


class CategorizationError(Exception):
    """Encompass category generation errors"""


class MissingMondoTermError(CategorizationError):
    """Raise for inability to recover referenced MONDO term

    Possibly indicates mismatch in MONDO versions/systems
    """


class CategoryInputMismatchError(CategorizationError):
    """Raise for conflict between version of a categorization input file and the existing stored disease data"""


def _get_frame_for_term(
    mondo: fastobo.doc.OboDoc, term_id: str
) -> fastobo.term.TermFrame:
    try:
        term_frame = next(t for t in mondo if str(t.id) == term_id.upper())
    except StopIteration as e:
        msg = f"Unable to retrieve {term_id} from local MONDO ontology"
        raise MissingMondoTermError(msg) from e
    return term_frame


def _get_parents_from_frame(frame: fastobo.term.TermFrame) -> set[str]:
    """Get term parents from a fastobo `frame`

    Exclude overly-broad or non-MONDO terms
    """
    parent_term_ids = set()
    for clause in frame:
        if clause.raw_tag() == "is_a":
            if clause.term.prefix != "MONDO" or clause.raw_value() == "MONDO:0005070":
                continue
            parent_term_ids.add(clause.raw_value())
    return parent_term_ids


def _get_oncotree_xref_from_frame(term_frame: fastobo.term.TermFrame) -> str | None:
    for clause in term_frame:
        if (
            isinstance(clause, fastobo.term.XrefClause)
            and clause.xref.id.prefix == "ONCOTREE"
            and clause.xref.id.local not in {"MT", "OTHER"}
        ):
            return str(clause.xref.id)
    return None


def _get_parent_oncotree_xrefs(
    mondo: fastobo.doc.OboDoc,
    term_frame: fastobo.term.TermFrame,
) -> list[tuple[str, str]]:
    if oncotree_xref := _get_oncotree_xref_from_frame(term_frame):
        return [(oncotree_xref, str(term_frame.id))]

    xrefs = []
    for parent_id in _get_parents_from_frame(term_frame):
        parent_term_frame = _get_frame_for_term(mondo, parent_id)
        xrefs += _get_parent_oncotree_xrefs(mondo, parent_term_frame)

    return xrefs


def _get_best_oncotree_mapping(
    mondo: fastobo.doc.OboDoc, term_frame: fastobo.term.TermFrame
) -> tuple[str, str] | None:
    """Recursive function for fetching parental oncotree mappings + filtering to the best one"""
    parent_xref_mappings = list(set(_get_parent_oncotree_xrefs(mondo, term_frame)))

    if len(parent_xref_mappings) != 1:
        # temporary -- insert conflict resolution later
        return None
    return parent_xref_mappings[0]


class MappingPredicate(StrEnum):
    """Constrain supported types of mapping predicates"""

    BROAD_MATCH = "skos:broadMatch"


class MappingJustification(StrEnum):
    """Constrain supported types of mapping justifications"""

    MAPPING_CHAINING = "semapv:MappingChaining"


@dataclass(frozen=True)
class SssomCategorizationMapping:
    """Individual SSSOM-based mapping from query terms (subject) to categorization terms (object)"""

    subject_id: str
    subject_label: str
    subject_source_version: str
    object_id: str
    object_label: str
    object_source_version: str
    comment: str
    predicate_id: str = MappingPredicate.BROAD_MATCH
    mapping_justification: str = MappingJustification.MAPPING_CHAINING


def generate_mondo_category_sssom(
    term_id: str,
    mondo: fastobo.doc.OboDoc,
    oncotree_flatmap: dict,
    mondo_version: str,
    oncotree_version: str,
) -> SssomCategorizationMapping | None:
    """Create SSSOM categorization SSSOM mapping"""
    term_frame = _get_frame_for_term(mondo, term_id)

    try:
        mapping_result = _get_best_oncotree_mapping(mondo, term_frame)
    except MissingMondoTermError:
        _logger.exception(
            "Encountered missing MONDO term while looking up categorization of %s, mondo version %s",
            term_id,
            mondo_version,
        )
        return None
    if not mapping_result:
        return None
    oncotree_mapping, mondo_derived_via = mapping_result
    try:
        oncotree_entry = oncotree_flatmap[oncotree_mapping]
        oncotree_label = oncotree_entry["name"]
    except KeyError:
        return None

    return SssomCategorizationMapping(
        subject_id=str(term_frame.id),
        subject_label=next(c.raw_value() for c in term_frame if c.raw_tag() == "name"),
        object_id=oncotree_mapping,
        object_label=oncotree_label,
        subject_source_version=mondo_version,
        object_source_version=oncotree_version,
        comment=f"Derived via xref from {mondo_derived_via}",
    )


def _recursively_build_oncotree_flatmap(node: dict, flatmap: dict) -> dict:
    for child_key, child_node in node.get("children", {}).items():
        if child_key in flatmap:
            continue
        flatmap = _recursively_build_oncotree_flatmap(child_node, flatmap)

    node["children"] = list(node["children"].keys())

    flatmap[f"ONCOTREE:{node['code']}"] = node
    return flatmap


def _build_oncotree_flatmap(oncotree_file_path: Path) -> dict:
    with oncotree_file_path.open() as fp:
        data = json.load(fp)

    return _recursively_build_oncotree_flatmap(data["TISSUE"], {})


def load_mondo_categories(
    storage: AbstractDatabase, data_dir: Path | None = None
) -> None:
    oncotree_getter = OncoTreeData(data_dir=data_dir)
    oncotree_file_path, oncotree_version = oncotree_getter.get_latest()
    oncotree = _build_oncotree_flatmap(oncotree_file_path)
    mondo_getter = MondoData(data_dir=data_dir)
    mondo_file_path, mondo_version = mondo_getter.get_latest()
    mondo = fastobo.load(mondo_file_path)

    sssom_mappings: list[SssomCategorizationMapping] = []
    for term in storage.get_all_concept_ids(SourceName.MONDO):
        if mapping := generate_mondo_category_sssom(
            term, mondo, oncotree, mondo_version, oncotree_version
        ):
            print(mapping)
            sssom_mappings.append(mapping)
        else:
            print(f"ope: {term}")

    # for mapping in sssom_mappings:
    #     storage.load_disease_categorization(
    #         DiseaseCategorization(
    #             category_schema_version=mapping.object_source_version,
    #             category_concept_id=mapping.object_id,
    #             category_name=mapping.object_label,
    #             concept_id=mapping.subject_id,
    #         )
    #     )
