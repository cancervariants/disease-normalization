# ADR-002 - Use SSSOM files to augment source concepts with curated mappings

## Status

**Proposed**

## Context

The current `rules` module can add or alter field values on individual records when we need to supplement or override source data. This mechanism has seen limited use and has several limitations:

* **Provenance**: curated additions are not stored separately from source-provided data. As a result, `GET /search` cannot reliably distinguish our curation from the source data it is intended to represent faithfully.
* **Documentation**: the current format provides little information about authorship, scope, or the rationale for a mapping.
* **Reuse**: mappings are tied to this application's rules format, making them harder to share with other projects.

We need a portable format for curated mappings and a way to apply them while preserving the source representation. This complements the use of `Condition` objects proposed in [ADR-001](001-mappableconcept-domain-model.md).

## Decision

* Bundle two mapping files in Simple Standard for Sharing Ontological Mappings (SSSOM) format with the source code:
  * **Disease category mappings**: `broadMatch` mappings from disease concepts to broader OncoTree categories.
  * **Curated exact mappings**: manually curated concept-to-concept `exactMatch` mappings.
* Add to ETL module to apply these mappings when concepts are generated from source files.
* Store curated mappings separately from the source-derived `Condition` JSONB in the database so retrieval can return either a **source view** or an **augmented view** of a concept:
  * The source view contains the source-derived record, without our curated additions.
  * The augmented view combines the source-derived record with applicable curated mappings.
* Retrieval by mapping should be able to opt into usage of the curated mappings; IE, the existing `GET /search` behavior should be able to query the database just by the record as the source gives it to us, but `GET /normalize` should use the curated mappings.

## Consequences

* Convert the existing single-entry mapping file to SSSOM format.
* Update ETL, storage, and retrieval to preserve the distinction between source-derived records and curated mappings.
  * Extend the database API to accept curated mappings separately: `add_record(self, disease: Condition, src_name: SourceName, *, curated_mappings: list[ConceptMapping] | None = None) -> None`. The `disease` argument must contain only source-derived data, including source-provided mappings. Treat an omitted value or `None` as no curated mappings for that record. Similarly, add a param to record retrieval methods on the DB for whether curated mappings should be included in the result.
  * Update both database implementations to persist curated mappings separately from the source record. ETL must pass these mappings through the new argument instead of appending them to `disease.mappings`.
  * Make retrieval explicitly select the source or augmented view, independently of whether it retrieves an individual or merged record. Build the augmented view without mutating the source record, and deduplicate mappings while preserving curation provenance.
  * Define how curated mappings participate in lookup indexes and concept merging. Both database implementations currently derive lookup references from the supplied record; separate storage alone will not make curated mappings available to normalization.
* Maintain two mapping files, with enough metadata to document their authorship and scope and support reuse outside this project.
* Use a separate mechanism for augmenting aliases and other metadata; this decision covers mappings only.
