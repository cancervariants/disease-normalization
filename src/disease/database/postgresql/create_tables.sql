CREATE TABLE disease_sources (
    name VARCHAR(127) PRIMARY KEY,
    data JSONB
);
-- see also: delete_normalized_concepts.sql
CREATE TABLE disease_merged (
    concept_id VARCHAR(127) PRIMARY KEY,
    label TEXT,
    aliases TEXT [],
    associated_with TEXT [],
    xrefs TEXT [],
    pediatric_disease BOOLEAN,
    oncologic_disease BOOLEAN
);
CREATE TABLE disease_concepts (
    concept_id VARCHAR(127) PRIMARY KEY,
    source VARCHAR(127) NOT NULL REFERENCES disease_sources (name),
    pediatric_disease BOOLEAN,
    oncologic_disease BOOLEAN,
    merge_ref VARCHAR(127) REFERENCES disease_merged (concept_id)
);
CREATE TABLE disease_labels (
    id SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    concept_id VARCHAR(127) REFERENCES disease_concepts (concept_id)
);
CREATE TABLE disease_aliases (
    id SERIAL PRIMARY KEY,
    alias TEXT NOT NULL,
    concept_id VARCHAR(127) NOT NULL REFERENCES disease_concepts (concept_id)
);
CREATE TABLE disease_xrefs (
    id SERIAL PRIMARY KEY,
    xref TEXT NOT NULL,
    concept_id VARCHAR(127) NOT NULL REFERENCES disease_concepts (concept_id)
);
CREATE TABLE disease_associations (
    id SERIAL PRIMARY KEY,
    associated_with TEXT NOT NULL,
    concept_ID VARCHAR(127) NOT NULL REFERENCES disease_concepts (concept_id)
);
