-- some redundancy between here and create_tables.sql, drop_indexes.sql,
-- add_indexes.sql.
DROP INDEX IF EXISTS idx_dm_concept_id_low;
ALTER TABLE disease_concepts DROP CONSTRAINT IF EXISTS disease_concepts_merge_ref_fkey;
UPDATE disease_concepts SET merge_ref = NULL;
DROP TABLE disease_merged;
CREATE TABLE disease_merged (
    concept_id VARCHAR(127) PRIMARY KEY,
    label TEXT,
    aliases TEXT [],
    associated_with TEXT [],
    xrefs TEXT [],
    pediatric_disease BOOLEAN,
    oncologic_disease BOOLEAN
);
ALTER TABLE disease_concepts ADD CONSTRAINT disease_concepts_merge_ref_fkey
    FOREIGN KEY (merge_ref) REFERENCES disease_merged (concept_id);
CREATE INDEX idx_dm_concept_id_low ON disease_merged (lower(concept_id));
