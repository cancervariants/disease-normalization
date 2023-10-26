ALTER TABLE disease_aliases ADD CONSTRAINT disease_aliases_concept_id_fkey
    FOREIGN KEY (concept_id) REFERENCES disease_concepts (concept_id);
ALTER TABLE disease_associations ADD CONSTRAINT disease_associations_concept_id_fkey
    FOREIGN KEY (concept_id) REFERENCES disease_concepts (concept_id);
ALTER TABLE disease_labels ADD CONSTRAINT disease_labels_concept_id_fkey
    FOREIGN KEY (concept_id) REFERENCES disease_concepts (concept_id);
ALTER TABLE disease_xrefs ADD CONSTRAINT disease_xrefs_concept_id_fkey
    FOREIGN KEY (concept_id) REFERENCES disease_concepts (concept_id);
