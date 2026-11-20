# ADR-002 - Use SSSOM files to augment source concepts with curated mappings

## Status

**Proposed**

## Context

The current `rules` module can add or alter field values on individual records when we need to supplement or override source data. This mechanism has seen limited use and has several limitations:

* **Provenance**: curated additions are not stored separately from source-provided data. As a result, `GET /search` cannot reliably distinguish our curation from the source data it is intended to represent faithfully.
* **Documentation**: the current format provides little information about authorship, scope, or the rationale for a mapping.
* **Reuse**: mappings are tied to this application's rules format, making them harder to share with other projects.

We need a portable format for curated mappings and a way to apply them while preserving the source representation. This complements the use of `Condition` objects proposed in [ADR-001](001-mappableconcept-domain-model.md).

Additionally, in applications like MetaKB, we are adding computed broadMatches from some MONDO and NCIt terms out to OncoTree categories, for things like a filter UI. We would like to move that logic into this library so that it can be reused.

## Decision

* Bundle one `curated_mappings.sssom.tsv` file with the source code in Simple Standard for Sharing Ontological Mappings (SSSOM) format. Include human-curated mapping additions and corrections, including OncoTree categories.
* To reject a source assertion, add a row with the same subject, predicate, and object and set `predicate_modifier` to `Not`. Record the curator, the rationale, and the source release when known.
* To change a mapping's scope, negate the original assertion and add a positive row with the corrected predicate. For example, negate `X skos:exactMatch Y` and add `X skos:broadMatch Y` when Y is broader than X.
* Load curated mappings and corrections during ETL.
* Also during ETL, attempt to compute a single best OncoTree `broadMatch` for eligible MONDO and NCIt concepts. A concept may have no inferred category.
* Store curated and inferred mappings separately from the source-derived `Condition` JSONB, preserving the provenance of each mapping. Retrieval supports two views:
  * The **source view** contains the source record and its source-provided mappings.
  * The **augmented view** applies curated corrections to the targeted source assertions and includes applicable positive curated and inferred mappings.
* Retrieval by mapping should use the source view for `GET /search` and the augmented view for `GET /normalize`.

## Consequences

* Consolidate the curated concept and category rows in one SSSOM file. Produce inferred mappings as a separate generated output.
* For NCIt category inference, load the OncoTree release file once per inference run and index its NCIt cross-references by NCIt concept ID. Regenerate NCIt inferences when either the NCIt or OncoTree release changes.
* Record the input releases in generated SSSOM mappings. Use `subject_source_version` for the MONDO or NCIt release and `object_source_version` for the OncoTree release.
* Update ETL, storage, and retrieval to preserve the distinction between source-derived records and curated mappings.
  * Extend the database API to accept supplemental mappings separately: `add_record(self, disease: Condition, src_name: SourceName, *, supplemental_mappings: list[ConceptMapping] | None = None) -> None`. The `disease` argument must contain only source-derived data, including source-provided mappings. Treat an omitted value or `None` as no supplemental mappings for that record. Similarly, add a param to record retrieval methods on the DB for whether supplemental mappings should be included using `include_supplemental_mappings` in the result.
  * Persist positive supplemental mappings and curated negations separately from the source record. ETL must interpret `predicate_modifier` before converting positive mappings to `ConceptMapping` and retain negations with their provenance.
  * Make retrieval explicitly select the source or augmented view, independently of whether it retrieves an individual or merged record. Build the augmented view without mutating the source record, and deduplicate mappings while preserving curation provenance.
  * Apply corrections to augmented reference lookups and merge edges. A rejected exact match must be excluded from both exact-match lookup and merging for the targeted source assertion. The source view retains the original assertion and its lookup reference.
* Use a separate mechanism for augmenting aliases and other metadata; this decision covers mappings only -- but the manner in which we handle mappings should inform our eventual workflow for handling aliases.
