"""Tests for curated mapping loading and conversion."""

import pytest
from ga4gh.core.models import Relation

from disease.etl import mappings
from disease.schemas import PredicateModifier

HEADER = (
    "subject_id\tsubject_label\tsubject_source\tsubject_source_version\t"
    "predicate_id\tpredicate_modifier\tobject_id\tobject_label\tobject_source\tobject_source_version\t"
    "mapping_justification\tauthor_id\tcomment\n"
)


def write_tsv(path, *rows):
    path.write_text(
        "# license: https://example.org/license\n\n" + HEADER + "".join(rows)
    )
    return path


def row(predicate="skos:exactMatch", target="ncit:C4207", comment="", modifier=""):
    return (
        f"DOID:6032\tSubject\tdoid\t2025-06-27\t{predicate}\t{modifier}\t{target}\tTarget\t"
        f"{target.partition(':')[0]}\t\t"
        f"semapv:ManualMappingCuration\torcid:test\t{comment}\n"
    )


@pytest.mark.parametrize("comment", ["", "Reviewed manually"])
def test_load_and_convert(tmp_path, comment):
    path = write_tsv(
        tmp_path / "mappings.tsv", row(comment=comment), row(target="ncit:C1")
    )
    loaded = mappings.load_mappings(path)
    assert list(loaded) == ["DOID:6032"]
    rows = loaded["DOID:6032"]
    assert [r.object_id for r in rows] == ["ncit:C4207", "ncit:C1"]
    assert rows[0].comment == (comment or None)
    assert rows[0].subject_source == "doid"
    assert rows[0].subject_source_version == "2025-06-27"
    assert rows[0].object_source == "ncit"
    assert rows[0].object_source_version is None
    converted = rows[0].to_concept_mapping()
    assert converted.relation == Relation.EXACT_MATCH
    assert converted.coding.code.root == "C4207"
    assert converted.coding.name == "Target"
    expected = {
        "author_id": "orcid:test",
        "mapping_justification": "semapv:ManualMappingCuration",
    }
    if comment:
        expected["comment"] = comment
    assert {e.name: e.value for e in converted.extensions} == expected


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("subject_id\n", "Missing required SSSOM columns"),
        (
            HEADER.replace("object_source_version\t", ""),
            "Missing required SSSOM columns",
        ),
        (HEADER + row().rstrip("\t\n") + "\n", "Incorrect number"),
        (HEADER + row().rstrip("\n") + "\textra\n", "Incorrect number"),
        (HEADER + row(predicate="skos:unknown"), "predicate_id"),
        (HEADER + row(modifier="unknown"), "predicate_modifier"),
    ],
)
def test_malformed_input(tmp_path, content, message):
    path = tmp_path / "invalid.tsv"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        mappings.load_mappings(path)


def test_positive_and_negated_mappings(tmp_path, monkeypatch):
    path = write_tsv(
        tmp_path / "curated.tsv",
        row(modifier="Not", comment="Review found a broader match"),
        row(predicate="skos:broadMatch"),
        row(predicate="skos:broadMatch", target="oncotree:OVT"),
        row(target="ncit:C1"),
    )
    monkeypatch.setattr(mappings, "CURATED_MAPPINGS", path)

    negation = mappings.load_mappings(path)["DOID:6032"][0]
    assert negation.predicate_modifier == PredicateModifier.NOT
    assert negation.predicate_id == Relation.EXACT_MATCH
    assert negation.comment == "Review found a broader match"
    assert negation.author_id == "orcid:test"
    with pytest.raises(ValueError, match="negated assertion"):
        negation.to_concept_mapping()

    positive, negative = mappings.get_etl_mappings()
    assert negative["DOID:6032"][0].object_id == "ncit:C4207"
    assert negative["DOID:6032"][0].comment == negation.comment
    result = positive["DOID:6032"]
    assert [(mapping.coding.id, mapping.relation) for mapping in result] == [
        ("ncit:C4207", Relation.BROAD_MATCH),
        ("oncotree:OVT", Relation.BROAD_MATCH),
        ("ncit:C1", Relation.EXACT_MATCH),
    ]


def test_unsupported_target(tmp_path, monkeypatch):
    path = write_tsv(tmp_path / "curated.tsv", row(target="unknown:1"))
    monkeypatch.setattr(mappings, "CURATED_MAPPINGS", path)
    with pytest.raises(ValueError, match="Unsupported mapping target"):
        mappings.get_etl_mappings()
