CREATE INDEX idx_d_concept_id_low ON disease_concepts (lower(concept_id));
-- see also: delete_normalized_concepts.sql
CREATE INDEX idx_dm_concept_id_low ON disease_merged (lower(concept_id));
CREATE INDEX idx_dl_label_low ON disease_labels (lower(label));
CREATE INDEX idx_da_alias_low ON disease_aliases (lower(alias));
CREATE INDEX idx_dx_xref_low ON disease_xrefs (lower(xref));
CREATE INDEX idx_d_as_association_low ON disease_associations (lower(associated_with));
CREATE INDEX idx_rlv_concept_id_low ON record_lookup_view (lower(concept_id));
