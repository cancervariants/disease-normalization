"""Load disease categorizations (within OncoTree) for NCIt and MONDO terms."""

from collections import defaultdict, deque
from functools import cache
from dataclasses import dataclass, field
from pathlib import Path

import fastobo
from wags_tails import MondoData, OncoTreeData

from disease.database import AbstractDatabase
from disease.schemas import DiseaseCategorization, SourceName


class CategoryInputMismatchError(Exception):
    """Raise for conflict between version of a categorization input file and the existing stored disease data"""


# def _get_mondo_path(silent: bool) -> Path:
#     getter = MondoData(silent=silent)
#     path, _ = getter.get_latest()
#     return path
#
#
# @dataclass(frozen=True)
# class _OncoTreeCategoryTerm:
#     """Provide basic structure for oncotree-based categories"""
#
#     name: str
#     concept_id: str
#
#
# def _collect_ncit_oncotree_mappings_for_node(
#     node: dict, mappings: dict[str, _OncoTreeCategoryTerm]
# ) -> dict[str, _OncoTreeCategoryTerm]:
#     # need to skip oncotree:TISSUE because we don't import it as a disease
#     if node.get("externalReferences", {}).get("NCI") and node["level"] > 1:
#         key = f"{NamespacePrefix.NCIT.value}:{node['externalReferences']['NCI']}"
#         value = _OncoTreeCategoryTerm(
#             name=node["name"],
#             concept_id=f"{NamespacePrefix.ONCOTREE.value}:{node['code']}",
#         )
#         mappings[key] = value
#     for child in node["children"].values():
#         mappings = _collect_ncit_oncotree_mappings_for_node(child, mappings)
#     return mappings
#
#
# def _get_ncit_oncotree_mappings(
#     oncotree_path: Path,
# ) -> dict[str, _OncoTreeCategoryTerm]:
#     with oncotree_path.open() as fp:
#         data = json.load(fp)
#     return _collect_ncit_oncotree_mappings_for_node(data["TISSUE"], {})
#
#
# def load_ncit_categorizations(
#     storage: AbstractDatabase, data_path: Path | None, silent: bool
# ) -> None:
#     """Load OncoTree-based tumor categorizations for NCIt cancer terms
#
#     Requirements:
#     * Both OncoTree and NCIt terms must already be loaded into the DB
#     * The release versions for OncoTree and NCIt used for categorization must
#       match what's already in the database
#     """
#     # before anything else:
#     # 1) acquire input files
#     # 2) validate that they match stored versions
#     oncotree_getter = OncoTreeData(data_path, silent=silent)
#     oncotree_path, oncotree_version = oncotree_getter.get_latest()
#     stored_oncotree_metadata = storage.get_source_metadata(SourceName.ONCOTREE)
#     if (
#         not stored_oncotree_metadata
#         or oncotree_version != stored_oncotree_metadata.version
#     ):
#         raise CategoryInputMismatchError
#
#     ncit_etl = NCIt(storage, data_path, silent=silent)
#     ncit_etl._extract_data()  # noqa: SLF001
#     stored_ncit_metadata = storage.get_source_metadata(SourceName.NCIT)
#     if not stored_ncit_metadata or ncit_etl._version != stored_ncit_metadata.version:  # noqa: SLF001
#         raise CategoryInputMismatchError
#
#     # create ncit -> oncotree mappings
#     oncotree_mappings: dict = _get_ncit_oncotree_mappings(oncotree_path)
#
#     # get ncit disease terms of interest
#     ncit_disease_classes = ncit_etl.get_disease_classes()
#     for disease_class in ncit_disease_classes:
#         # create set of oncotree-mapped ncit parent terms
#         # for each disease class, walk up ancestry lineages until you find something w/ a mapping
#         # get the set of all categorizations, reduce as needed
#         pass


@dataclass
class _MondoTerm:
    concept_id: str
    name: str | None = None
    parents: set[str] = field(default_factory=set)
    oncotree_xrefs: set[str] = field(default_factory=set)


def normalize_oncotree_xref(xref: str) -> str | None:
    """Return the OncoTree code from an ONCOTREE-prefixed xref."""
    prefix, separator, code = xref.partition(":")
    if not separator or prefix.upper() != "ONCOTREE":
        return None
    return code


def closest_oncotree_mappings(
    term_id: str,
    terms: dict[str, _MondoTerm],
) -> dict[str, set[str]]:
    """Find the closest OncoTree mappings on every upward MONDO lineage.

    Returns:
        {
            "LUAD": {"MONDO:0008903"},
            "LUSC": {"MONDO:0012345"},
        }

    The values are the MONDO terms that directly assert the mapping.
    Traversal does not continue above a mapped ancestor, because mappings
    farther up that same lineage are less specific.
    """
    mappings: dict[str, set[str]] = defaultdict(set)
    visited: set[str] = set()
    queue: deque[str] = deque([term_id])

    while queue:
        current_id = queue.popleft()

        if current_id in visited:
            continue

        visited.add(current_id)
        current = terms.get(current_id)

        if current is None:
            continue

        if current.oncotree_xrefs:
            for xref in current.oncotree_xrefs:
                mappings[xref].add(current_id)

            # This is the closest mapped term on this lineage, so do not
            # continue to broader ancestors.
            continue

        queue.extend(current.parents)

    return dict(mappings)


def load_mondo_categorizations(
    storage: AbstractDatabase, data_path: Path | None, silent: bool
) -> None:
    """Load OncoTree-based tumor categorizations for mondo cancer terms"""
    # before anything else: acquire input files, validate that they match stored versions
    oncotree_getter = OncoTreeData(data_path, silent=silent)
    oncotree_path, oncotree_version = oncotree_getter.get_latest()
    stored_oncotree_metadata = storage.get_source_metadata(SourceName.ONCOTREE)
    if (
        not stored_oncotree_metadata
        or oncotree_version != stored_oncotree_metadata.version
    ):
        raise CategoryInputMismatchError

    mondo_getter = MondoData(data_path, silent=silent)
    mondo_path, mondo_version = mondo_getter.get_latest()
    stored_mondo_metadata = storage.get_source_metadata(SourceName.MONDO)
    if not stored_mondo_metadata or mondo_version != stored_mondo_metadata.version:
        raise CategoryInputMismatchError

    terms: dict[str, _MondoTerm] = {}
    mondo = fastobo.load(mondo_path)

    for frame in mondo:
        if not isinstance(frame, fastobo.term.TermFrame):
            continue

        term = _MondoTerm(concept_id=str(frame.id))

        for clause in frame:
            if isinstance(clause, fastobo.term.NameClause):
                term.name = str(clause.name)

            elif isinstance(clause, fastobo.term.IsAClause):
                term.parents.add(str(clause.term))

            elif isinstance(clause, fastobo.term.XrefClause):
                code = normalize_oncotree_xref(str(clause.xref.id))

                if code is not None:
                    term.oncotree_xrefs.add(code)

        terms[term.concept_id] = term

    storage.delete_disease_categorizations()

    for term in terms.values():
        mappings = closest_oncotree_mappings(term.concept_id, terms)

        if not mappings:
            continue

        for oncotree_code, asserting_terms in mappings.items():
            storage.load_disease_categorization(
                DiseaseCategorization(
                    category_schema_version=oncotree_version,
                    category_concept_id=oncotree_code,
                    category_name="todo",
                    concept_id=term.concept_id,
                )
            )
