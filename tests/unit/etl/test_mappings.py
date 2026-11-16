"""Tests for curated mapping loading and conversion."""

import pytest
from ga4gh.core.models import ConceptMapping, Relation

from disease.etl import mappings

HEADER = (
    "subject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\t"
    "mapping_justification\tauthor_id\tcomment\n"
)


def write_tsv(path, *rows):
    path.write_text(
        "# license: https://example.org/license\n\n" + HEADER + "".join(rows)
    )
    return path


def row(predicate="skos:exactMatch", target="ncit:C4207", comment=""):
    return (
        f"DOID:6032\tSubject\t{predicate}\t{target}\tTarget\t"
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
        (HEADER + row().rstrip("\t\n") + "\n", "Incorrect number"),
        (HEADER + row().rstrip("\n") + "\textra\n", "Incorrect number"),
        (HEADER + row(predicate="skos:unknown"), "predicate_id"),
    ],
)
def test_malformed_input(tmp_path, content, message):
    path = tmp_path / "invalid.tsv"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        mappings.load_mappings(path)


@pytest.mark.parametrize("with_category", [False, True])
def test_combined_mappings(tmp_path, monkeypatch, with_category):
    category_rows = [row("skos:broadMatch", "oncotree:OVT")] if with_category else []
    monkeypatch.setattr(
        mappings,
        "CATEGORY_MAPPINGS",
        write_tsv(tmp_path / "category.tsv", *category_rows),
    )
    monkeypatch.setattr(
        mappings, "CONCEPT_MAPPINGS", write_tsv(tmp_path / "concept.tsv", row())
    )
    loaded = mappings.get_etl_mappings()
    assert list(loaded) == ["DOID:6032"]
    result = loaded["DOID:6032"]
    assert all(isinstance(mapping, ConceptMapping) for mapping in result)
    expected = [Relation.BROAD_MATCH] if with_category else []
    assert [mapping.relation for mapping in result] == [*expected, Relation.EXACT_MATCH]


@pytest.mark.parametrize(
    ("category", "predicate", "target", "message"),
    [
        (True, "skos:exactMatch", "oncotree:OVT", "Expected broadMatch"),
        (False, "skos:broadMatch", "ncit:C4207", "Expected exactMatch"),
        (True, "skos:broadMatch", "ncit:C4207", "Expected an OncoTree category"),
        (False, "skos:exactMatch", "unknown:1", "Unsupported mapping target"),
    ],
)
def test_invalid_semantics(tmp_path, monkeypatch, category, predicate, target, message):
    category_path = write_tsv(
        tmp_path / "category.tsv", *([row(predicate, target)] if category else [])
    )
    concept_path = write_tsv(
        tmp_path / "concept.tsv", *([] if category else [row(predicate, target)])
    )
    monkeypatch.setattr(mappings, "CATEGORY_MAPPINGS", category_path)
    monkeypatch.setattr(mappings, "CONCEPT_MAPPINGS", concept_path)
    with pytest.raises(ValueError, match=message):
        mappings.get_etl_mappings()
